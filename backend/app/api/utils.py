"""API工具函数模块."""
from datetime import datetime
from typing import Any, Dict
from copy import deepcopy

from config.settings import DEFAULT_VOICE_CONFIG

SEGMENT_HARD_SEPARATORS = {"。", "！", "？", ".", "!", "?", "\n"}
SEGMENT_SOFT_SEPARATORS = {"，", ",", "；", ";", "：", ":"}
SEGMENT_SOFT_LIMIT = 70
SEGMENT_HARD_LIMIT = 120


def _infer_candidate_name_from_resume(resume_text: str) -> str:
    """从简历文本中推断候选人姓名."""
    if not resume_text:
        return "候选人"

    lines = [line.strip() for line in resume_text.splitlines() if line.strip()]
    if not lines:
        return "候选人"

    for line in lines[:20]:
        normalized = line.replace("：", ":")
        if normalized.startswith("姓名:"):
            name = normalized.split(":", 1)[1].strip()
            if name:
                return name
    return "候选人"


def _normalize_skill_domain(domain_raw: str) -> str:
    """标准化技能领域."""
    from app.models.schemas import SkillDomain

    domain = (domain_raw or "").strip().lower()
    allowed = {d.value for d in SkillDomain}
    return domain if domain in allowed else SkillDomain.FULLSTACK.value


def _serialize_timestamp(value: Any) -> Any:
    """序列化时间戳."""
    if hasattr(value, "isoformat"):
        return value.isoformat(timespec='seconds')
    return value


def _serialize_record(record: Dict[str, Any]) -> Dict[str, Any]:
    """序列化数据库记录."""
    serialized = {}
    for key, value in (record or {}).items():
        serialized[key] = _serialize_timestamp(value)
    return serialized


def _build_history_export(interview_id: int, current_message_id: int) -> Dict[str, Any]:
    """导出当前消息路径的历史记录."""
    from app.db import database

    messages = database.get_message_path(interview_id, current_message_id)
    exported_history = [
        {
            'id': msg.get('id'),
            'role': msg.get('role'),
            'content': msg.get('content'),
            'timestamp': _serialize_timestamp(msg.get('timestamp'))
        }
        for msg in messages
    ]
    return {
        'interview_id': interview_id,
        'current_message_id': current_message_id,
        'exported_at': datetime.now().isoformat(timespec='seconds'),
        'message_count': len(exported_history),
        'messages': exported_history
    }


def _normalize_voice_config_payload(payload: Dict[str, Any] | None) -> Dict[str, Any]:
    """标准化语音配置."""
    raw = payload or {}
    normalized = deepcopy(DEFAULT_VOICE_CONFIG)
    normalized.update(raw)

    int_fields = [
        'noise_floor_sample_ms',
        'min_speech_ms',
        'end_silence_ms',
        'max_segment_ms',
        'pre_roll_ms',
        'barge_in_ms',
        'chunk_retention_ms',
        'timeslice_ms',
        'auto_send_min_chars',
        'typing_grace_ms',
    ]
    float_fields = ['speech_start_threshold', 'min_threshold']
    bool_fields = ['enabled', 'always_on_enabled']
    truthy_values = {'1', 'true', 'yes', 'on'}

    for field in int_fields:
        normalized[field] = int(normalized[field])
    for field in float_fields:
        normalized[field] = float(normalized[field])
    for field in bool_fields:
        value = normalized[field]
        if isinstance(value, str):
            normalized[field] = value.strip().lower() in truthy_values
        else:
            normalized[field] = bool(value)

    words = normalized.get('short_noise_words', [])
    if isinstance(words, str):
        words = [item.strip() for item in words.splitlines()]
    normalized['short_noise_words'] = [str(word).strip() for word in words if str(word).strip()]
    return normalized


def _pop_ready_segments(buffer: str) -> tuple[list[str], str]:
    """Split buffered model output into ready-to-render segments."""
    ready_segments = []
    current = ""

    for char in buffer:
        current += char
        if char in SEGMENT_HARD_SEPARATORS:
            if current.strip():
                ready_segments.append(current.strip())
            current = ""
            continue

        if len(current) >= SEGMENT_SOFT_LIMIT and char in SEGMENT_SOFT_SEPARATORS:
            ready_segments.append(current.strip())
            current = ""
            continue

        if len(current) >= SEGMENT_HARD_LIMIT:
            ready_segments.append(current.strip())
            current = ""

    return ready_segments, current


def _parse_optional_timestamp(value: Any) -> datetime | None:
    """解析可选时间戳."""
    raw = str(value or '').strip()
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace('Z', '+00:00'))
    except ValueError:
        return None


def _serialize_expression_report(record: Dict[str, Any] | None) -> Dict[str, Any] | None:
    """序列化表情分析报告."""
    if not record:
        return None

    serialized = {}
    for key, value in record.items():
        if key == 'report_data' and isinstance(value, dict):
            # 递归序列化报告数据
            serialized[key] = {k: _serialize_timestamp(v) for k, v in value.items()}
        else:
            serialized[key] = _serialize_timestamp(value)
    return serialized


def finalize_expression_analysis(interview_id: int) -> Dict[str, Any] | None:
    """完成表情分析并生成报告."""
    from app.db import database
    from app.services.expression_analyzer_service import get_expression_analyzer_service

    try:
        analyzer = get_expression_analyzer_service()
        report = analyzer.generate_report(interview_id)

        if report:
            report_id = database.create_expression_report({
                "interview_id": interview_id,
                "report_data": report
            })
            return {"report_id": report_id, **report}
    except Exception as e:
        import logging
        logging.error(f"Failed to finalize expression analysis for interview {interview_id}: {e}")
    return None


def _resolve_interviewer_avatar_runtime_config(interview_id: int) -> Dict[str, str]:
    """解析面试官头像运行时配置."""
    from app.db import database
    from app.services.prompt_service import prompt_service

    interview = database.get_interview(interview_id)
    if not interview:
        return {}

    # 获取提示词配置
    prompt_config = prompt_service.get_prompt_config_data()
    avatar_config = prompt_config.get("interviewer_avatar", {})

    # 根据面试阶段返回不同配置
    stage = interview.get("current_stage", "welcome")
    stage_avatar_config = avatar_config.get(f"{stage}_avatar", {})

    return {
        "gender": stage_avatar_config.get("gender", "Female"),
        "style": stage_avatar_config.get("style", "professional"),
        "background": stage_avatar_config.get("background", "office"),
    }
