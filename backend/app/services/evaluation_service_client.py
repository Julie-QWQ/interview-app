"""评估服务客户端 - 对接 evaluation-service (端口8002)"""

import logging
import requests
from typing import Any, Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class EvaluationServiceClient:
    """评估服务客户端类"""

    def __init__(self, base_url: str = "http://10.179.224.2:8002"):
        self.base_url = base_url.rstrip("/")
        self.timeout = 10  # 减少超时时间到10秒, 避免阻塞面试流程
        self.max_retries = 1  # 最多重试1次

    def _build_url(self, path: str) -> str:
        """构建完整URL"""
        return f"{self.base_url}/api/evaluation{path}"

    def trigger_evaluation(
        self,
        interview_id: str,
        user_id: int,
        position: str,
        qa_list: List[Dict[str, Any]],
    ) -> bool:
        """
        触发完整评估接口 (面试结束时调用)

        Args:
            interview_id: 面试唯一ID
            user_id: 用户ID
            position: 岗位 (如 java_backend / web_frontend / algorithm)
            qa_list: 完整问答列表, 每个元素包含:
                - questionIndex: 题目序号
                - questionId: 题目ID
                - questionText: 题目内容
                - answerText: 候选人回答
                - questionType: 题目类型 (technical/open)
                - keyPoints: 技术要点 (可选)
                - followUpCount: 追问次数 (可选)
                - answerDuration: 回答时长 (可选)

        Returns:
            是否成功触发
        """
        url = self._build_url("/trigger")

        payload = {
            "interviewId": interview_id,
            "userId": user_id,
            "position": position,
            "qaList": qa_list,
        }

        try:
            response = requests.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=self.timeout,
            )
            response.raise_for_status()
            result = response.json()

            if result.get("code") == 200:
                logger.info(
                    f"触发完整评估成功 - interviewId: {interview_id}, "
                    f"qaCount: {len(qa_list)}"
                )
                return True
            else:
                logger.error(
                    f"触发完整评估失败 - interviewId: {interview_id}, "
                    f"error: {result.get('message')}"
                )
                return False

        except requests.Timeout:
            logger.warning(
                f"触发完整评估超时 - interviewId: {interview_id}, "
                f"timeout: {self.timeout}s"
            )
            return False
        except requests.ConnectionError as e:
            logger.warning(
                f"触发完整评估连接失败 - interviewId: {interview_id}, "
                f"error: {e}"
            )
            return False
        except requests.HTTPError as e:
            logger.error(
                f"触发完整评估HTTP错误 - interviewId: {interview_id}, "
                f"status: {e.response.status_code if e.response else 'unknown'}"
            )
            return False
        except requests.RequestException as e:
            logger.error(
                f"触发完整评估请求异常 - interviewId: {interview_id}, "
                f"error: {e}"
            )
            return False
        except Exception as e:
            logger.error(
                f"触发完整评估未知异常 - interviewId: {interview_id}, "
                f"error: {e}"
            )
            return False

    def realtime_evaluation(
        self,
        interview_id: str,
        user_id: int,
        position: str,
        question_index: int,
        question_type: str,
        question_text: str,
        answer_text: str,
        key_points: Optional[List[str]] = None,
        speech_rate: Optional[int] = None,
        pause_count: Optional[int] = None,
        filler_count: Optional[int] = None,
        follow_up_count: Optional[int] = None,
        answer_duration: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        实时单题评估接口

        Args:
            interview_id: 面试唯一ID
            user_id: 用户ID
            position: 岗位 (如 java_backend / web_frontend / algorithm)
            question_index: 题目序号 (从1开始)
            question_type: 题目类型 (technical技术题 / open开放性题目)
            question_text: 题目内容
            answer_text: 候选人回答文本
            key_points: 标准答案要点 (技术题必填, 开放题可不传)
            speech_rate: 语速 (字/分钟)
            pause_count: 停顿次数
            filler_count: 口头禅次数
            follow_up_count: 本题追问次数
            answer_duration: 回答时长 (秒)

        Returns:
            评估结果字典, 包含:
            - technicalScore: 技术正确性得分 (1-10)
            - logicScore: 逻辑严谨性得分 (1-10)
            - primaryEmotion: 主要情绪
            - confidence: 自信度 (0-1)
            - nervousness: 紧张度 (0-1)
            - highlights: 回答亮点列表
            - weaknesses: 回答不足列表
            - missedPoints: 遗漏要点
            - quickAdvice: 即时建议
        """
        url = self._build_url("/realtime")

        payload = {
            "interviewId": interview_id,
            "userId": user_id,
            "position": position,
            "questionIndex": question_index,
            "questionType": question_type,
            "questionText": question_text,
            "answerText": answer_text,
        }

        # 添加可选字段
        if key_points:
            payload["keyPoints"] = key_points
        if speech_rate is not None:
            payload["speechRate"] = speech_rate
        if pause_count is not None:
            payload["pauseCount"] = pause_count
        if filler_count is not None:
            payload["fillerCount"] = filler_count
        if follow_up_count is not None:
            payload["followUpCount"] = follow_up_count
        if answer_duration is not None:
            payload["answerDuration"] = answer_duration

        try:
            response = requests.post(
                url,
                json=payload,
                timeout=self.timeout,
            )
            response.raise_for_status()
            result = response.json()

            if result.get("code") == 200:
                logger.info(
                    f"实时评估成功 - interviewId: {interview_id}, "
                    f"questionIndex: {question_index}"
                )
                return result.get("data")
            else:
                logger.error(
                    f"实时评估失败 - interviewId: {interview_id}, "
                    f"questionIndex: {question_index}, error: {result.get('message')}"
                )
                return None

        except requests.Timeout:
            logger.warning(
                f"实时评估超时 - interviewId: {interview_id}, "
                f"questionIndex: {question_index}, timeout: {self.timeout}s"
            )
            return None
        except requests.ConnectionError as e:
            logger.warning(
                f"实时评估连接失败 - interviewId: {interview_id}, "
                f"questionIndex: {question_index}, error: {e}"
            )
            return None
        except requests.HTTPError as e:
            logger.error(
                f"实时评估HTTP错误 - interviewId: {interview_id}, "
                f"questionIndex: {question_index}, status: {e.response.status_code if e.response else 'unknown'}"
            )
            return None
        except requests.RequestException as e:
            logger.error(
                f"实时评估请求异常 - interviewId: {interview_id}, "
                f"questionIndex: {question_index}, error: {e}"
            )
            return None
        except Exception as e:
            logger.error(
                f"实时评估未知异常 - interviewId: {interview_id}, "
                f"questionIndex: {question_index}, error: {e}"
            )
            return None

    def get_evaluation_status(self, interview_id: str) -> Optional[Dict[str, Any]]:
        """
        查询批量评估状态

        Args:
            interview_id: 面试ID

        Returns:
            状态信息字典, 包含:
            - status: 0评估中 / 1已完成 / 2失败
            - interviewId: 面试ID
        """
        url = self._build_url(f"/status/{interview_id}")

        try:
            response = requests.get(url, timeout=self.timeout)
            response.raise_for_status()
            result = response.json()

            if result.get("code") == 200:
                return result.get("data")
            else:
                logger.error(
                    f"查询评估状态失败 - interviewId: {interview_id}, "
                    f"error: {result.get('message')}"
                )
                return None

        except requests.RequestException as e:
            logger.error(f"查询评估状态接口调用失败: {e}")
            return None

    def get_evaluation_report(self, interview_id: str) -> Optional[Dict[str, Any]]:
        """
        获取完整评估报告

        Args:
            interview_id: 面试ID

        Returns:
            完整评估报告, 包含总分、评级、各维度得分、改进建议等
        """
        url = self._build_url(f"/report/{interview_id}")

        try:
            response = requests.get(url, timeout=self.timeout)
            response.raise_for_status()
            result = response.json()

            if result.get("code") == 200:
                logger.info(f"获取评估报告成功 - interviewId: {interview_id}")
                return result.get("data")
            else:
                logger.error(
                    f"获取评估报告失败 - interviewId: {interview_id}, "
                    f"error: {result.get('message')}"
                )
                return None

        except requests.RequestException as e:
            logger.error(f"获取评估报告接口调用失败: {e}")
            return None

    def get_user_history(self, user_id: int) -> Optional[List[Dict[str, Any]]]:
        """
        获取用户历史评估列表

        Args:
            user_id: 用户ID

        Returns:
            历史评估记录列表, 按时间降序
        """
        url = self._build_url(f"/history/{user_id}")

        try:
            response = requests.get(url, timeout=self.timeout)
            response.raise_for_status()
            result = response.json()

            if result.get("code") == 200:
                return result.get("data", [])
            else:
                logger.error(
                    f"获取用户历史失败 - userId: {user_id}, "
                    f"error: {result.get('message')}"
                )
                return None

        except requests.RequestException as e:
            logger.error(f"获取用户历史接口调用失败: {e}")
            return None


# 全局单例
_evaluation_client: Optional[EvaluationServiceClient] = None


def get_evaluation_client() -> EvaluationServiceClient:
    """获取评估服务客户端单例"""
    global _evaluation_client
    if _evaluation_client is None:
        _evaluation_client = EvaluationServiceClient()
    return _evaluation_client
