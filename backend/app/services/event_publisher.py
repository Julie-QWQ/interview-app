"""Redis事件发布器 - 用于发布面试完成事件到评估服务"""

import json
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class EventPublisher:
    """Redis事件发布器"""

    def __init__(self):
        # TODO: 实际Redis连接需要从配置读取
        # 这里使用HTTP接口发布事件，由后端API层处理Redis发布
        self.enabled = True

    def publish_interview_completed_event(
        self,
        interview_id: str,
        user_id: int,
        position: str,
        mode: str,
        resume_info: Dict[str, Any],
        qa_list: List[Dict[str, Any]],
    ) -> bool:
        """
        发布面试完成事件到 evaluation:completed 频道

        Args:
            interview_id: 面试ID
            user_id: 用户ID
            position: 岗位
            mode: 面试模式
            resume_info: 简历信息，包含skills等
            qa_list: 问答历史列表，每项包含：
                - questionIndex: 题目序号
                - questionId: 题目ID
                - questionText: 题目内容
                - answerText: 回答文本
                - questionType: 题目类型（technical/open）
                - keyPoints: 标准答案要点
                - speechRate: 语速
                - pauseCount: 停顿次数
                - fillerCount: 口头禅次数
                - followUpCount: 追问次数
                - answerDuration: 回答时长

        Returns:
            是否发布成功
        """
        event_payload = {
            "interviewId": interview_id,
            "userId": user_id,
            "position": position,
            "mode": mode,
            "resumeInfo": resume_info,
            "qaList": qa_list,
        }

        try:
            # 这里只是记录日志，实际发布由API层通过Redis完成
            logger.info(
                f"准备发布面试完成事件 - interviewId: {interview_id}, "
                f"userId: {user_id}, position: {position}, "
                f"qaCount: {len(qa_list)}"
            )
            logger.debug(f"事件负载: {json.dumps(event_payload, ensure_ascii=False)}")
            return True

        except Exception as e:
            logger.error(f"发布面试完成事件失败: {e}")
            return False


# 全局单例
_event_publisher: Optional[EventPublisher] = None


def get_event_publisher() -> EventPublisher:
    """获取事件发布器单例"""
    global _event_publisher
    if _event_publisher is None:
        _event_publisher = EventPublisher()
    return _event_publisher
