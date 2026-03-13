"""
阿里云 Avatar Dialog 数字人服务
使用 WebSocket 连接阿里云 Avatar Dialog API 实现实时数字人对话

官方文档: https://help.aliyun.com/zh/model-studio/avatar-dialog-api
"""
import asyncio
import base64
import hashlib
import json
import logging
import os
import time
import uuid
from typing import Optional, Dict, Any, AsyncIterator
import websockets

logger = logging.getLogger(__name__)


class AvatarDialogService:
    """阿里云 Avatar Dialog 数字人服务类"""

    def __init__(self):
        # DashScope API 配置
        self.api_endpoint = os.getenv('DASHSCOPE_API_ENDPOINT', 'wss://dashscope.aliyuncs.com/api-ws/v1/inference')
        self.api_key = os.getenv('DASHSCOPE_API_KEY', '')

        # RTC 配置
        self.rtc_app_id = os.getenv('ALIYUN_RTC_APP_ID', '')
        self.rtc_app_key = os.getenv('ALIYUN_RTC_APP_KEY', '')

        # 默认数字人配置
        self.default_avatar_id = os.getenv('ALIYUN_AVATAR_DEFAULT_ID', 'taoji')
        self.sample_rate = int(os.getenv('ALIYUN_AVATAR_SAMPLE_RATE', '16000'))

        # WebSocket 连接
        self.ws_connection: Optional[websockets.WebSocketClientProtocol] = None
        self.task_id: Optional[str] = None
        self.session_initialized = False

        # 是否启用
        self.enabled = bool(self.api_key and self.rtc_app_id and self.rtc_app_key)

        if not self.enabled:
            logger.warning("阿里云 Avatar Dialog 配置不完整，服务将被禁用")

    def _get_auth_headers(self) -> Dict[str, str]:
        """获取鉴权请求头"""
        return {
            "Authorization": f"Bearer {self.api_key}"
        }

    def _generate_rtc_token(self, user_id: str, channel_id: str) -> Dict[str, Any]:
        """
        生成 RTC Token

        Args:
            user_id: 用户 ID
            channel_id: 频道 ID

        Returns:
            RTC 参数字典
        """
        current_time = int(time.time())
        timestamp = current_time + 24 * 60 * 60  # Token 有效期 24 小时

        # 调试日志
        logger.info(f"当前时间戳: {current_time} ({time.ctime(current_time)})")
        logger.info(f"Token 时间戳: {timestamp} ({time.ctime(timestamp)})")

        # 生成 Token: SHA256(app_id + app_key + channel_id + user_id + timestamp)
        data = f"{self.rtc_app_id}{self.rtc_app_key}{channel_id}{user_id}{timestamp}"
        logger.debug(f"Token 数据: {data[:50]}...")  # 只显示前50个字符
        sha256_hash = hashlib.sha256()
        sha256_hash.update(data.encode())
        token = sha256_hash.hexdigest()

        return {
            "app_id": self.rtc_app_id,
            "channel_id": channel_id,
            "user_id": user_id,
            "nonce": "",
            "timestamp": timestamp,
            "token": token,
            "gslb": ["https://gw.rtn.aliyuncs.com"]
        }

    async def initialize_session(
        self,
        avatar_id: Optional[str] = None,
        interview_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        初始化数字人会话

        Args:
            avatar_id: 数字人 ID，不指定则使用默认
            interview_id: 面试 ID

        Returns:
            {
                'success': bool,
                'rtc_params': dict,  # RTC 连接参数
                'avatar_id': str,
                'task_id': str,
                'error': str (如果失败)
            }
        """
        if not self.enabled:
            return {
                'success': False,
                'error': '阿里云 Avatar Dialog 服务未启用或配置不完整'
            }

        try:
            # 生成任务 ID
            self.task_id = str(uuid.uuid4())

            # 生成 RTC 参数
            user_id = f"interview_{interview_id or 'default'}"
            channel_id = f"channel_{interview_id or 'default'}_{int(time.time())}"
            rtc_params = self._generate_rtc_token(user_id, channel_id)

            # 构建 InitializeVideoSession 消息
            avatar_id = avatar_id or self.default_avatar_id
            init_message = {
                "header": {
                    "task_id": self.task_id,
                    "streaming": "duplex",
                    "action": "run-task"
                },
                "payload": {
                    "task_group": "aigc",
                    "task": "video-generation",
                    "function": "stream-generation",
                    "model": "avatar-dialog",
                    "input": {
                        "header": {
                            "name": "InitializeVideoSession",
                            "request_id": str(uuid.uuid4())
                        },
                        "payload": {
                            "avatar_id": avatar_id,
                            "format": "PCM",
                            "sample_rate": self.sample_rate,
                            "session_config": {
                                "enable_motion_data": False,
                                "motion_data_compression": "zip",
                                "motion_data_audio_encoder": "opus"
                            },
                            "h5_mode_enable": True,
                            "user_agent": {
                                "client": "BAILIAN",
                                "platform": "Dalvik/2.1.0 (Linux; U; Android 12; NOH-AL00 Build/HUAWEINOH-AL00)",
                                "version": "3.18.0",
                                "app_type": "Dev"
                            },
                            "rtc_param": rtc_params
                        }
                    },
                    "parameter": {}
                }
            }

            # 建立 WebSocket 连接
            logger.info(f"正在连接 Avatar Dialog API: {self.api_endpoint}")
            self.ws_connection = await websockets.connect(
                self.api_endpoint,
                additional_headers=self._get_auth_headers(),
                ping_interval=300,
                ping_timeout=300
            )

            # 发送初始化消息
            message_json = json.dumps(init_message, ensure_ascii=True)
            logger.info(f"发送 InitializeVideoSession 消息: task_id={self.task_id}, avatar_id={avatar_id}")
            logger.info(f"完整消息内容: {message_json}")
            await self.ws_connection.send(message_json)

            # 等待会话初始化完成 (监听 VideoSessionInitialized 事件)
            session_initialized = await self._wait_for_session_init()

            if not session_initialized:
                await self.ws_connection.close()
                return {
                    'success': False,
                    'error': '会话初始化超时或失败'
                }

            self.session_initialized = True
            logger.info(f"Avatar Dialog 会话初始化成功: task_id={self.task_id}")

            return {
                'success': True,
                'rtc_params': rtc_params,
                'avatar_id': avatar_id,
                'task_id': self.task_id
            }

        except Exception as e:
            error_msg = f"初始化 Avatar Dialog 会话失败: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }

    async def _wait_for_session_init(self, timeout: int = 30) -> bool:
        """
        等待会话初始化完成

        Args:
            timeout: 超时时间（秒）

        Returns:
            True 如果初始化成功，否则 False
        """
        if not self.ws_connection:
            return False

        start_time = time.time()

        try:
            while time.time() - start_time < timeout:
                try:
                    message = await asyncio.wait_for(
                        self.ws_connection.recv(),
                        timeout=5.0
                    )
                    event = json.loads(message)
                    logger.info(f"收到事件: {json.dumps(event, ensure_ascii=False)}")

                    # 检查是否为 task-failed 事件
                    if event.get('header', {}).get('event') == 'task-failed':
                        error_code = event.get('header', {}).get('error_code', 'Unknown')
                        error_message = event.get('payload', {}).get('output', {}).get('payload', {}).get('message', 'Unknown error')
                        logger.error(f"任务失败: {error_code} - {error_message}")
                        logger.error(f"完整错误信息: {json.dumps(event, ensure_ascii=False, indent=2)}")
                        return False

                    # 检查是否为 VideoSessionInitialized 事件
                    if event.get('header', {}).get('event') == 'result-generated':
                        output = event.get('payload', {}).get('output', {})
                        header = output.get('header', {})

                        if header.get('name') == 'VideoSessionInitialized':
                            logger.info("收到 VideoSessionInitialized 事件")
                            # 继续等待 VideoSessionStarted
                            continue

                        if header.get('name') == 'VideoSessionStarted':
                            logger.info("收到 VideoSessionStarted 事件，会话初始化完成")
                            return True

                except asyncio.TimeoutError:
                    continue

            logger.error(f"等待会话初始化超时 ({timeout}秒)")
            return False

        except Exception as e:
            logger.error(f"等待会话初始化异常: {e}")
            return False

    async def stream_audio(
        self,
        audio_data: bytes,
        speech_id: str,
        sentence_id: str,
        end_of_speech: bool = False
    ) -> Dict[str, Any]:
        """
        发送音频数据到 Avatar Dialog

        Args:
            audio_data: PCM 音频数据（bytes）
            speech_id: 语音 ID
            sentence_id: 句子 ID
            end_of_speech: 是否为语音结束

        Returns:
            {
                'success': bool,
                'error': str (如果失败)
            }
        """
        if not self.enabled or not self.session_initialized:
            return {
                'success': False,
                'error': 'Avatar Dialog 会话未初始化'
            }

        try:
            # 将音频数据转换为 Base64
            audio_base64 = base64.b64encode(audio_data).decode('utf-8')

            # 构建 GenerateVideo 消息
            message = {
                "header": {
                    "task_id": self.task_id,
                    "streaming": "duplex",
                    "action": "continue-task"
                },
                "payload": {
                    "input": {
                        "header": {
                            "name": "GenerateVideo",
                            "request_id": str(uuid.uuid4())
                        },
                        "payload": {
                            "speech_id": speech_id,
                            "sentence_id": sentence_id,
                            "audio_data": audio_base64,
                            "end_of_speech": end_of_speech
                        }
                    }
                }
            }

            # 发送消息
            await self.ws_connection.send(json.dumps(message))
            logger.debug(f"发送音频数据: speech_id={speech_id}, sentence_id={sentence_id}, size={len(audio_data)}")

            return {
                'success': True
            }

        except Exception as e:
            error_msg = f"发送音频数据失败: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }

    async def interrupt_speech(self) -> Dict[str, Any]:
        """
        打断当前播报

        Returns:
            {
                'success': bool,
                'error': str (如果失败)
            }
        """
        if not self.enabled or not self.session_initialized:
            return {
                'success': False,
                'error': 'Avatar Dialog 会话未初始化'
            }

        try:
            # 构建 ChangeAvatarStatus 消息
            message = {
                "header": {
                    "task_id": self.task_id,
                    "streaming": "duplex",
                    "action": "continue-task"
                },
                "payload": {
                    "input": {
                        "header": {
                            "name": "ChangeAvatarStatus",
                            "request_id": str(uuid.uuid4())
                        },
                        "payload": {
                            "target_status": "LISTENING"
                        }
                    }
                }
            }

            # 发送消息
            await self.ws_connection.send(json.dumps(message))
            logger.info("发送打断命令")

            return {
                'success': True
            }

        except Exception as e:
            error_msg = f"打断播报失败: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }

    async def destroy_session(self) -> Dict[str, Any]:
        """
        销毁数字人会话

        Returns:
            {
                'success': bool,
                'error': str (如果失败)
            }
        """
        if not self.ws_connection:
            return {
                'success': False,
                'error': 'WebSocket 连接不存在'
            }

        try:
            # 构建 DestroyVideoSession 消息
            message = {
                "header": {
                    "task_id": self.task_id,
                    "streaming": "duplex",
                    "action": "finish-task"
                },
                "payload": {
                    "input": {
                        "header": {
                            "name": "DestroyVideoSession",
                            "request_id": str(uuid.uuid4())
                        },
                        "payload": {}
                    }
                }
            }

            # 发送销毁消息
            await self.ws_connection.send(json.dumps(message))
            logger.info("发送 DestroyVideoSession 消息")

            # 等待 VideoSessionDestroyed 事件
            try:
                await asyncio.wait_for(self._wait_for_session_destroy(), timeout=10.0)
            except asyncio.TimeoutError:
                logger.warning("等待会话销毁超时")

            # 关闭 WebSocket 连接
            await self.ws_connection.close()

            # 重置状态
            self.ws_connection = None
            self.task_id = None
            self.session_initialized = False

            logger.info("Avatar Dialog 会话已销毁")
            return {
                'success': True
            }

        except Exception as e:
            error_msg = f"销毁会话失败: {str(e)}"
            logger.error(error_msg)

            # 尝试强制关闭连接
            if self.ws_connection:
                try:
                    await self.ws_connection.close()
                except Exception:
                    logger.warning("Failed to close websocket during session destroy cleanup", exc_info=True)

            return {
                'success': False,
                'error': error_msg
            }

    async def _wait_for_session_destroy(self, timeout: int = 10) -> bool:
        """
        等待会话销毁完成

        Args:
            timeout: 超时时间（秒）

        Returns:
            True 如果销毁成功，否则 False
        """
        if not self.ws_connection:
            return False

        start_time = time.time()

        try:
            while time.time() - start_time < timeout:
                try:
                    message = await asyncio.wait_for(
                        self.ws_connection.recv(),
                        timeout=5.0
                    )
                    event = json.loads(message)

                    # 检查是否为 VideoSessionDestroyed 事件
                    if event.get('header', {}).get('event') == 'task-finished':
                        output = event.get('payload', {}).get('output', {})
                        header = output.get('header', {})

                        if header.get('name') == 'VideoSessionDestroyed':
                            logger.info("收到 VideoSessionDestroyed 事件")
                            return True

                except asyncio.TimeoutError:
                    continue

            return False

        except Exception as e:
            logger.error(f"等待会话销毁异常: {e}")
            return False

    async def trigger_heartbeat(self) -> Dict[str, Any]:
        """
        触发心跳，保持连接活跃

        Returns:
            {
                'success': bool,
                'error': str (如果失败)
            }
        """
        if not self.enabled or not self.session_initialized:
            return {
                'success': False,
                'error': 'Avatar Dialog 会话未初始化'
            }

        try:
            # 构建 TriggerHeartbeat 消息
            message = {
                "header": {
                    "task_id": self.task_id,
                    "streaming": "duplex",
                    "action": "continue-task"
                },
                "payload": {
                    "input": {
                        "header": {
                            "name": "TriggerHeartbeat",
                            "request_id": str(uuid.uuid4())
                        },
                        "payload": {}
                    }
                }
            }

            # 发送心跳消息
            await self.ws_connection.send(json.dumps(message))
            logger.debug("发送心跳消息")

            return {
                'success': True
            }

        except Exception as e:
            error_msg = f"发送心跳失败: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }

    def get_rtc_token(self, user_id: str, channel_id: Optional[str] = None) -> Dict[str, Any]:
        """
        获取 RTC Token（用于前端连接）

        Args:
            user_id: 用户 ID
            channel_id: 频道 ID，不指定则自动生成

        Returns:
            RTC 参数字典
        """
        if channel_id is None:
            channel_id = f"channel_{int(time.time())}"

        return self._generate_rtc_token(user_id, channel_id)

    def health_check(self) -> bool:
        """
        检查服务可用性

        Returns:
            True 如果服务可用，否则 False
        """
        return self.enabled and bool(self.api_key and self.rtc_app_id and self.rtc_app_key)


# 全局单例
_avatar_dialog_service = None


def get_avatar_dialog_service() -> AvatarDialogService:
    """获取数字人服务实例"""
    global _avatar_dialog_service
    if _avatar_dialog_service is None:
        _avatar_dialog_service = AvatarDialogService()
    return _avatar_dialog_service


def init_avatar_dialog_service(settings):
    """初始化数字人服务"""
    global _avatar_dialog_service
    _avatar_dialog_service = AvatarDialogService()
    logger.info("阿里云 Avatar Dialog 数字人服务已初始化")
