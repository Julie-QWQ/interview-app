"""FastAPI routes for interview lifecycle management."""

from __future__ import annotations

import logging
from typing import Dict, Any, List

from fastapi import APIRouter, Body
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from app.api.utils import (
    _build_history_export,
    _infer_candidate_name_from_resume,
    _normalize_skill_domain,
    finalize_expression_analysis,
)
from app.db import database
from app.models.schemas import (
    CreateInterviewRequest,
    InterviewDetailResponse,
    InterviewResponse,
    InterviewStatus,
    MessageResponse,
    MessageType,
)
from app.services.ai_service import get_ai_service
from app.services.interview_orchestrator import get_interview_orchestrator
from app.services.prompt_service import prompt_service
from app.services.evaluation_service_client import get_evaluation_client
from app.services.event_publisher import get_event_publisher
import json

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")


def _error(message: str, status_code: int = 500) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"error": message})


def _convert_position_to_evaluation_format(position: str) -> str:
    """将岗位名称转换为评估服务期望的格式"""
    position_lower = position.lower()
    if "java" in position_lower or "后端" in position:
        return "java_backend"
    elif "前端" in position_lower or "web" in position_lower or "vue" in position_lower or "react" in position_lower:
        return "web_frontend"
    elif "算法" in position_lower or "algorithm" in position_lower:
        return "algorithm"
    else:
        return "java_backend"  # 默认


def _build_qa_list_for_evaluation(messages: List[Dict[str, Any]], interview: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    从面试消息构建评估服务需要的QA列表

    Args:
        messages: 面试消息列表
        interview: 面试信息

    Returns:
        QA列表，每项包含 questionIndex, questionText, answerText 等字段
    """
    from datetime import datetime
    import re

    qa_list = []
    question_index = 0

    i = 0
    while i < len(messages):
        msg = messages[i]

        # 寻找面试官的问题
        if msg.get("role") == "assistant":
            question_index += 1
            question_text = msg.get("content", "")
            question_timestamp = msg.get("timestamp")

            # 寻找候选人的回答
            answer_text = ""
            answer_timestamp = None
            answer_msg = None

            if i + 1 < len(messages) and messages[i + 1].get("role") == "user":
                answer_msg = messages[i + 1]
                answer_text = answer_msg.get("content", "")
                answer_timestamp = answer_msg.get("timestamp")

            # 判断题目类型（简化判断：开放性问题包含"项目"、"经历"等关键词）
            question_type = "open" if any(keyword in question_text for keyword in ["项目", "经历", "介绍", "说说", "为什么", "自我介绍", "介绍下"]) else "technical"

            # 计算回答时长（秒）
            answer_duration = 60  # 默认值
            if question_timestamp and answer_timestamp:
                try:
                    # 解析时间戳
                    q_time = datetime.fromisoformat(str(question_timestamp).replace('Z', '+00:00')) if isinstance(question_timestamp, str) else question_timestamp
                    a_time = datetime.fromisoformat(str(answer_timestamp).replace('Z', '+00:00')) if isinstance(answer_timestamp, str) else answer_timestamp
                    time_diff = (a_time - q_time).total_seconds()
                    if time_diff > 0:
                        answer_duration = int(time_diff)
                except Exception as e:
                    logger.warning(f"计算回答时长失败: {e}")

            # 估算语速（字符/分钟）
            speech_rate = 200  # 默认值
            if answer_text and answer_duration > 0:
                char_count = len(answer_text)
                speech_rate = int((char_count / answer_duration) * 60) if answer_duration > 0 else 200

            # 估算停顿次数（基于标点符号）
            pause_count = 0
            if answer_text:
                # 统计句号、问号、感叹号的数量作为停顿的近似
                pause_count = answer_text.count('。') + answer_text.count('？') + answer_text.count('！') + answer_text.count('.') + answer_text.count('?') + answer_text.count('!')

            # 估算填充词数量（嗯、啊、呃等）
            filler_count = 0
            if answer_text:
                filler_count = len(re.findall(r'[嗯啊呃额那个就是说然后然后呢]', answer_text))

            # 估算追问次数（检查后续是否有相关追问）
            follow_up_count = 0
            if i + 2 < len(messages):
                # 检查接下来的2-3条消息是否是追问
                for j in range(i + 2, min(i + 5, len(messages))):
                    next_msg = messages[j]
                    if next_msg.get("role") == "assistant":
                        next_content = next_msg.get("content", "")
                        # 如果包含追问关键词，计数
                        if any(keyword in next_content for keyword in ["具体", "展开", "详细", "再说说", "还有", "比如", "例子"]):
                            follow_up_count += 1
                        else:
                            break  # 遇到非追问就停止
                    else:
                        break

            # 提取关键点（技术题需要）
            key_points = []
            if question_type == "technical" and question_text:
                # 从问题中提取技术关键词
                # 常见技术关键词模式
                tech_keywords = re.findall(r'(?:Redis|MySQL|Spring|Vue|React|Java|Python|算法|数据结构|线程|进程|缓存|数据库|网络|HTTP|API|分布式|微服务|设计模式|JVM|GC|集合|框架|架构|性能|安全|测试)', question_text)
                key_points = list(set(tech_keywords))  # 去重

            qa_item = {
                "questionIndex": question_index,
                "questionId": str(question_index),  # 纯数字字符串，如 "1", "25"
                "questionText": question_text,
                "answerText": answer_text,
                "questionType": question_type,
                "keyPoints": key_points if key_points else [],
                "speechRate": speech_rate,
                "pauseCount": pause_count,
                "fillerCount": filler_count,
                "followUpCount": follow_up_count,
                "answerDuration": answer_duration,
            }
            qa_list.append(qa_item)

        i += 1

    return qa_list


def _trigger_evaluation_and_publish_event(interview: Dict[str, Any], export_payload: Dict[str, Any]):
    """
    触发评估服务并发布面试完成事件

    注意：此函数的所有异常都会被捕获，不会影响面试完成的正常流程

    Args:
        interview: 面试信息
        export_payload: 导出的历史记录
    """
    try:
        interview_id = interview.get("id")
        interview_id_str = str(interview_id)

        logger.info(f"开始触发评估服务和发布事件 - interviewId: {interview_id_str}")

        # 构建评估服务需要的QA列表
        messages = export_payload.get("messages", [])
        qa_list = _build_qa_list_for_evaluation(messages, interview)

        if not qa_list:
            logger.warning(f"没有找到问答数据，跳过评估 - interviewId: {interview_id_str}")
            return

        # 构建简历信息
        skills = interview.get("skills", [])
        resume_info = {
            "skills": skills if isinstance(skills, list) else [skills],
        }

        # 获取用户ID（简化处理，使用1作为默认值）
        user_id = 1  # TODO: 从认证信息或请求中获取实际用户ID

        # 获取岗位和模式
        position = _convert_position_to_evaluation_format(interview.get("position", ""))
        mode = interview.get("mode", "standard")

        # 调用实时评估接口（为每个问题调用一次）
        evaluation_client = get_evaluation_client()
        success_count = 0
        failed_count = 0

        for qa_item in qa_list:
            try:
                # 🖨️ 打印关键ID到控制台
                print(f"📤 发送到评估服务 - interviewId: {interview_id_str}, questionId: {qa_item['questionId']}")

                # 调用评估接口，设置较短的超时时间
                result = evaluation_client.realtime_evaluation(
                    interview_id=interview_id_str,
                    user_id=user_id,
                    position=position,
                    question_index=qa_item["questionIndex"],
                    question_type=qa_item["questionType"],
                    question_text=qa_item["questionText"],
                    answer_text=qa_item["answerText"],
                    key_points=qa_item.get("keyPoints"),
                    speech_rate=qa_item.get("speechRate"),
                    pause_count=qa_item.get("pauseCount"),
                    filler_count=qa_item.get("fillerCount"),
                    follow_up_count=qa_item.get("followUpCount"),
                    answer_duration=qa_item.get("answerDuration"),
                )

                if result:
                    success_count += 1
                    logger.debug(f"实时评估成功 - questionIndex: {qa_item['questionIndex']}")
                else:
                    failed_count += 1
                    logger.warning(f"实时评估返回空结果 - questionIndex: {qa_item['questionIndex']}")

            except Exception as e:
                failed_count += 1
                logger.error(f"实时评估异常 - questionIndex: {qa_item['questionIndex']}, error: {e}")
                # 继续处理下一个问题，不中断整个流程

        # 发布面试完成事件
        try:
            event_publisher = get_event_publisher()
            event_publisher.publish_interview_completed_event(
                interview_id=interview_id_str,
                user_id=user_id,
                position=position,
                mode=mode,
                resume_info=resume_info,
                qa_list=qa_list,
            )
            logger.info(f"事件发布成功 - interviewId: {interview_id_str}")
        except Exception as e:
            logger.error(f"事件发布失败 - interviewId: {interview_id_str}, error: {e}")
            # 事件发布失败不影响主流程

        logger.info(
            f"评估服务调用完成 - interviewId: {interview_id_str}, "
            f"成功: {success_count}, 失败: {failed_count}, 总数: {len(qa_list)}"
        )

        # 调用触发完整评估接口
        try:
            trigger_success = evaluation_client.trigger_evaluation(
                interview_id=interview_id_str,
                user_id=user_id,
                position=position,
                qa_list=qa_list,
            )
            if trigger_success:
                logger.info(f"触发完整评估成功 - interviewId: {interview_id_str}")
            else:
                logger.warning(f"触发完整评估失败 - interviewId: {interview_id_str}")
        except Exception as e:
            logger.error(f"触发完整评估异常 - interviewId: {interview_id_str}, error: {e}")
            # 触发失败不影响主流程

    except Exception as e:
        logger.error(f"触发评估和发布事件整体失败: {e}", exc_info=True)
        # 不影响主流程，只记录错误


@router.post("/interviews")
def create_interview(payload: dict = Body(default_factory=dict)):
    try:
        interview_req = CreateInterviewRequest(**payload)

        position_plugin = database.get_profile_plugin(interview_req.position_profile_id)
        interviewer_plugin = database.get_profile_plugin(interview_req.interviewer_profile_id)
        if not position_plugin:
            return _error("岗位画像不存在", status_code=400)
        if not interviewer_plugin:
            return _error("面试官画像不存在", status_code=400)

        position_cfg = position_plugin.get("config") or {}
        interviewer_cfg = interviewer_plugin.get("config") or {}
        skill_req = position_cfg.get("skill_requirements") or {}

        interview_id = database.create_interview(
            {
                "candidate_name": _infer_candidate_name_from_resume(interview_req.resume_text or ""),
                "position": position_plugin.get("name") or "技术岗位",
                "skill_domain": _normalize_skill_domain(position_cfg.get("skill_domain")),
                "skills": skill_req.get("core_skills") or ["综合能力"],
                "experience_level": position_cfg.get("experience_level")
                or interviewer_cfg.get("preferred_level")
                or "中级",
                "duration_minutes": interview_req.duration_minutes,
                "additional_requirements": interview_req.additional_requirements,
                "resume_file_id": interview_req.resume_file_id,
                "resume_text": interview_req.resume_text,
            }
        )

        try:
            database.apply_interview_profile(
                interview_id,
                interview_req.position_profile_id,
                interview_req.interviewer_profile_id,
                {},
            )
        except Exception:
            database.delete_interview(interview_id)
            return _error("Profile binding failed and interview creation was rolled back")

        interview = database.get_interview(interview_id)
        return JSONResponse(status_code=201, content=InterviewResponse(**interview).model_dump(mode="json"))
    except ValidationError as exc:
        return _error(str(exc), status_code=400)
    except Exception as exc:
        logger.error("Failed to create interview: %s", exc)
        return _error("Internal server error")


@router.get("/interviews")
def list_interviews(status: str | None = None, limit: int = 50, offset: int = 0):
    try:
        interviews = database.list_interviews(limit=limit, offset=offset, status=status)
        return [InterviewResponse(**item).model_dump(mode="json") for item in interviews]
    except Exception as exc:
        logger.error("Failed to list interviews: %s", exc)
        return _error("Internal server error")


@router.get("/interviews/{interview_id}")
def get_interview(interview_id: int):
    try:
        interview = database.get_interview(interview_id)
        if not interview:
            return _error("Interview not found", status_code=404)

        messages = database.get_messages(interview_id)
        current_stage = interview.get("current_stage")
        stage_progress = None
        if current_stage and interview["status"] == InterviewStatus.IN_PROGRESS:
            try:
                stage_progress = get_ai_service().get_interview_progress(
                    messages,
                    current_stage,
                    interview.get("duration_minutes", 30),
                    interview_config=interview,
                )
            except Exception:
                logger.warning("Failed to compute stage progress", exc_info=True)

        interview_without_stage = {
            key: value
            for key, value in interview.items()
            if key not in {"current_stage", "current_message_id"}
        }
        detail = InterviewDetailResponse(
            **interview_without_stage,
            messages=[MessageResponse(**message).model_dump(mode="json") for message in messages],
            current_stage=current_stage,
            stage_progress=stage_progress,
            current_message_id=interview.get("current_message_id"),
        )
        return detail.model_dump(mode="json")
    except Exception as exc:
        logger.error("Failed to get interview: %s", exc)
        return _error("Internal server error")


@router.delete("/interviews/{interview_id}")
def delete_interview(interview_id: int):
    try:
        if not database.delete_interview(interview_id):
            return _error("Interview not found", status_code=404)
        return {"message": "删除成功"}
    except Exception as exc:
        logger.error("Failed to delete interview: %s", exc)
        return _error("Internal server error")


@router.post("/interviews/{interview_id}/start")
def start_interview(interview_id: int):
    try:
        interview = database.get_interview(interview_id)
        if not interview:
            return _error("Interview not found", status_code=404)
        if interview["status"] not in [InterviewStatus.CREATED, InterviewStatus.IN_PROGRESS]:
            return _error("Invalid interview status", status_code=400)

        messages = database.get_messages(interview_id)
        is_retry = len(messages) > 0 and interview["status"] == InterviewStatus.IN_PROGRESS
        if not is_retry:
            database.update_interview_status(interview_id, InterviewStatus.IN_PROGRESS)
            database.update_interview_stage(interview_id, prompt_service.get_first_stage())

        trace_id = get_interview_orchestrator().new_trace_id()
        welcome_message = get_ai_service().start_interview(interview, trace_id=trace_id)
        message_id = database.create_message(interview_id, MessageType.ASSISTANT, welcome_message)
        database.update_interview_current_message(interview_id, message_id)
        first_stage = prompt_service.get_first_stage()
        return {
            "message": "Interview started",
            "trace_id": trace_id,
            "welcome_message": welcome_message,
            "welcome_audio": None,
            "message_id": message_id,
            "current_stage": first_stage,
        }
    except Exception as exc:
        logger.error("Failed to start interview: %s", exc)
        return _error("Internal server error")


@router.post("/interviews/{interview_id}/complete")
def complete_interview(interview_id: int):
    try:
        interview = database.get_interview(interview_id)
        if not interview:
            return _error("Interview not found", status_code=404)
        if interview["status"] != InterviewStatus.IN_PROGRESS:
            return _error("面试未进行中", status_code=400)

        current_message_id = interview.get("current_message_id")
        if not current_message_id:
            return _error("当前消息路径不存在，无法导出历史对话", status_code=400)

        export_payload = _build_history_export(interview_id, current_message_id)
        report_payload = finalize_expression_analysis(interview_id)
        database.update_interview_status(interview_id, InterviewStatus.COMPLETED)

        # 异步调用评估服务并发布事件（不阻塞响应）
        import threading
        threading.Thread(
            target=_trigger_evaluation_and_publish_event,
            args=(interview, export_payload),
            daemon=True
        ).start()

        return {
            "message": "面试已完成",
            "history_export": export_payload,
            "expression_report": report_payload,
        }
    except Exception as exc:
        logger.error("Failed to complete interview: %s", exc)
        return _error("Internal server error")


@router.get("/interviews/{interview_id}/history-export")
def export_interview_history(interview_id: int):
    try:
        interview = database.get_interview(interview_id)
        if not interview:
            return _error("Interview not found", status_code=404)
        current_message_id = interview.get("current_message_id")
        if not current_message_id:
            return _error("当前消息路径不存在，无法导出历史对话", status_code=400)
        return _build_history_export(interview_id, current_message_id)
    except Exception as exc:
        logger.error("Failed to export history: %s", exc)
        return _error("Internal server error")


@router.get("/interviews/{interview_id}/progress")
def get_interview_progress(interview_id: int):
    try:
        interview = database.get_interview(interview_id)
        if not interview:
            return _error("Interview not found", status_code=404)
        current_message_id = interview.get("current_message_id")
        messages = (
            database.get_message_path(interview_id, current_message_id)
            if current_message_id
            else database.get_messages(interview_id)
        )
        current_stage = interview.get("current_stage", prompt_service.get_first_stage())
        return get_ai_service().get_interview_progress(
            messages,
            current_stage,
            interview.get("duration_minutes", 30),
            interview_config=interview,
        )
    except Exception as exc:
        logger.error("Failed to get interview progress: %s", exc)
        return _error("Internal server error")


@router.put("/interviews/{interview_id}/current-message")
def update_current_message(interview_id: int, payload: dict = Body(default_factory=dict)):
    try:
        message_id = payload.get("message_id")
        if not message_id:
            return _error("message_id is required", status_code=400)
        messages = database.get_messages(interview_id)
        if not any(message["id"] == message_id for message in messages):
            return _error("Message not found", status_code=404)
        if not database.update_interview_current_message(interview_id, message_id):
            return _error("更新失败")
        return {"message": "更新成功"}
    except Exception as exc:
        logger.error("Failed to update current message: %s", exc)
        return _error("Internal server error")
