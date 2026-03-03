"""API routes."""
from flask import Blueprint, request, jsonify, Response, stream_with_context
import json
import os
import uuid
from datetime import datetime
from werkzeug.utils import secure_filename
from app.services.ai_service import get_ai_service, init_ai_service
from app.services.asr_service import get_asr_service, init_asr_service
from app.db import database
from app.models.schemas import (
    CreateInterviewRequest, InterviewResponse, InterviewDetailResponse,
    MessageResponse, ChatMessage, InterviewStatus, MessageType, SkillDomain
)
from app.services.prompt_service import prompt_service
from app.models.prompt_config import InterviewPromptConfig, DEFAULT_PROMPT_CONFIG
import logging

logger = logging.getLogger(__name__)

# 鍒涘缓API钃濆浘
api_bp = Blueprint('api', __name__)

# 绠€鍘嗕笂浼犻厤缃?
UPLOAD_FOLDER = 'uploads/resumes'
ALLOWED_EXTENSIONS = {'pdf'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

# 纭繚涓婁紶鐩綍瀛樺湪
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def init_api(settings):
    """API endpoint."""
    init_ai_service(settings)
    init_asr_service(settings)


def _infer_candidate_name_from_resume(resume_text: str) -> str:
    """Try to infer candidate name from resume text with simple heuristics."""
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
    domain = (domain_raw or "").strip().lower()
    allowed = {d.value for d in SkillDomain}
    return domain if domain in allowed else SkillDomain.FULLSTACK.value


def _serialize_timestamp(value):
    if hasattr(value, "isoformat"):
        return value.isoformat(timespec='seconds')
    return value


def _build_history_export(interview_id: int, current_message_id: int) -> dict:
    """Export only the current message path history."""
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


# ==================== 闈㈣瘯鐩稿叧鎺ュ彛 ====================

@api_bp.route('/interviews', methods=['POST'])
def create_interview():
    """API endpoint."""
    try:
        data = request.get_json() or {}
        interview_req = CreateInterviewRequest(**data)

        position_plugin = database.get_profile_plugin(interview_req.position_profile_id)
        interviewer_plugin = database.get_profile_plugin(interview_req.interviewer_profile_id)
        if not position_plugin:
            return jsonify({'error': '岗位画像不存在'}), 400
        if not interviewer_plugin:
            return jsonify({'error': '面试官画像不存在'}), 400

        position_cfg = position_plugin.get('config') or {}
        interviewer_cfg = interviewer_plugin.get('config') or {}
        skill_req = position_cfg.get('skill_requirements') or {}

        derived_skills = skill_req.get('core_skills') or ['综合能力']
        derived_domain = _normalize_skill_domain(position_cfg.get('skill_domain'))
        derived_candidate_name = _infer_candidate_name_from_resume(interview_req.resume_text or "")
        derived_position = position_plugin.get('name') or '技术岗位'
        derived_experience = (
            position_cfg.get('experience_level')
            or interviewer_cfg.get('preferred_level')
            or '中级'
        )

        # 创建面试记录（核心输入为画像与简历，其余字段自动推导）
        interview_id = database.create_interview({
            'candidate_name': derived_candidate_name,
            'position': derived_position,
            'skill_domain': derived_domain,
            'skills': derived_skills,
            'experience_level': derived_experience,
            'duration_minutes': interview_req.duration_minutes,
            'additional_requirements': interview_req.additional_requirements,
            'resume_file_id': interview_req.resume_file_id,
            'resume_text': interview_req.resume_text
        })

        # 应用画像到面试
        try:
            database.apply_interview_profile(
                interview_id,
                interview_req.position_profile_id,
                interview_req.interviewer_profile_id,
                {}
            )
            logger.info(
                "应用画像到面试成功: interview_id=%s, position=%s, interviewer=%s",
                interview_id,
                interview_req.position_profile_id,
                interview_req.interviewer_profile_id,
            )
        except Exception as e:
            logger.error(f"应用画像失败: {e}")
            database.delete_interview(interview_id)
            return jsonify({'error': '画像绑定失败，面试创建已回滚'}), 500

        # 鑾峰彇闈㈣瘯璇︽儏
        interview = database.get_interview(interview_id)

        logger.info(f"鍒涘缓闈㈣瘯鎴愬姛: {interview_id}")
        return jsonify(InterviewResponse(**interview).model_dump()), 201

    except Exception as e:
        logger.error(f"鍒涘缓闈㈣瘯澶辫触: {e}")
        return jsonify({'error': str(e)}), 400


@api_bp.route('/interviews', methods=['GET'])
def list_interviews():
    """API endpoint."""
    try:
        status = request.args.get('status')
        limit = int(request.args.get('limit', 50))
        offset = int(request.args.get('offset', 0))

        interviews = database.list_interviews(limit=limit, offset=offset, status=status)

        return jsonify([InterviewResponse(**i).model_dump() for i in interviews]), 200

    except Exception as e:
        logger.error(f"鍒楀嚭闈㈣瘯澶辫触: {e}")
        return jsonify({'error': str(e)}), 400


@api_bp.route('/interviews/<int:interview_id>', methods=['GET'])
def get_interview(interview_id: int):
    """API endpoint."""
    try:
        interview = database.get_interview(interview_id)
        if not interview:
            return jsonify({'error': 'Interview not found'}), 404

        # 鑾峰彇娑堟伅鍘嗗彶
        messages = database.get_messages(interview_id)

        # 鑾峰彇褰撳墠闃舵鍜岃繘搴︿俊鎭?
        current_stage = interview.get('current_stage')
        stage_progress = None
        
        if current_stage and interview['status'] == InterviewStatus.IN_PROGRESS:
            ai_service = get_ai_service()
            try:
                stage_progress = ai_service.get_interview_progress(
                    messages,
                    current_stage,
                    interview.get('duration_minutes', 30),
                    interview_config=interview,
                )
            except:
                pass  # 濡傛灉鑾峰彇杩涘害澶辫触锛屽拷鐣?

        # 浠?interview 涓Щ闄?current_stage锛岄伩鍏嶉噸澶嶄紶閫?
        interview_without_stage = {k: v for k, v in interview.items() if k not in ['current_stage', 'current_message_id']}

        # 鏋勫缓璇︽儏鍝嶅簲
        interview_detail = InterviewDetailResponse(
            **interview_without_stage,
            messages=[MessageResponse(**m).model_dump() for m in messages],
            current_stage=current_stage,
            stage_progress=stage_progress,
            current_message_id=interview.get('current_message_id')  # 娣诲姞褰撳墠娑堟伅ID
        )

        return jsonify(interview_detail.model_dump()), 200

    except Exception as e:
        logger.error(f"鑾峰彇闈㈣瘯璇︽儏澶辫触: {e}")
        return jsonify({'error': str(e)}), 400


@api_bp.route('/interviews/<int:interview_id>', methods=['DELETE'])
def delete_interview(interview_id: int):
    """API endpoint."""
    try:
        success = database.delete_interview(interview_id)
        if not success:
            return jsonify({'error': 'Interview not found'}), 404

        logger.info(f"鍒犻櫎闈㈣瘯鎴愬姛: {interview_id}")
        return jsonify({'message': '删除成功'}), 200

    except Exception as e:
        logger.error(f"鍒犻櫎闈㈣瘯澶辫触: {e}")
        return jsonify({'error': str(e)}), 400


@api_bp.route('/interviews/<int:interview_id>/start', methods=['POST'])
def start_interview(interview_id: int):
    """API endpoint."""
    try:
        from app.services.tts_service import get_tts_service

        interview = database.get_interview(interview_id)
        if not interview:
            return jsonify({'error': 'Interview not found'}), 404

        # 鍏佽 CREATED 鎴?IN_PROGRESS 鐘舵€侊紙鏀寔閲嶈瘯锛?
        if interview['status'] not in [InterviewStatus.CREATED, InterviewStatus.IN_PROGRESS]:
            return jsonify({'error': 'Invalid interview status'}), 400

        # 妫€鏌ユ槸鍚﹀凡鏈夋秷鎭紙濡傛灉鏈夛紝璇存槑宸茬粡寮€濮嬩簡锛?
        messages = database.get_messages(interview_id)
        is_retry = len(messages) > 0 and interview['status'] == InterviewStatus.IN_PROGRESS

        if is_retry:
            logger.info(f"Interview {interview_id} restarting")
        else:
            # 鏇存柊鐘舵€佷负杩涜涓紝骞惰缃垵濮嬮樁娈?
            database.update_interview_status(interview_id, InterviewStatus.IN_PROGRESS)
            database.update_interview_stage(interview_id, prompt_service.get_first_stage())

        # 鑾峰彇AI鏈嶅姟
        ai_service = get_ai_service()

        # 鐢熸垚寮€鍦烘秷鎭?
        welcome_message = ai_service.start_interview(interview)

        # 淇濆瓨AI娑堟伅
        message_id = database.create_message(interview_id, MessageType.ASSISTANT, welcome_message)

        # 鏇存柊褰撳墠娑堟伅鑺傜偣
        database.update_interview_current_message(interview_id, message_id)

        # 鐢熸垚TTS闊抽
        welcome_audio = None
        try:
            tts_service = get_tts_service()
            welcome_audio = tts_service.text_to_speech(welcome_message)
            logger.info(f"TTS闊抽鐢熸垚鎴愬姛,闀垮害: {len(welcome_audio) if welcome_audio else 0}")
        except Exception as e:
            logger.error(f"TTS鐢熸垚澶辫触: {e}")

        first_stage = prompt_service.get_first_stage()
        logger.info(f"寮€濮嬮潰璇? {interview_id}, 闃舵: {first_stage}")
        return jsonify({
            'message': 'Interview started',
            'welcome_message': welcome_message,
            'welcome_audio': welcome_audio,
            'message_id': message_id,
            'current_stage': first_stage
        }), 200

    except Exception as e:
        logger.error(f"寮€濮嬮潰璇曞け璐? {e}")
        return jsonify({'error': str(e)}), 500


@api_bp.route('/interviews/<int:interview_id>/complete', methods=['POST'])
def complete_interview(interview_id: int):
    """API endpoint."""
    try:
        interview = database.get_interview(interview_id)
        if not interview:
            return jsonify({'error': 'Interview not found'}), 404

        if interview['status'] != InterviewStatus.IN_PROGRESS:
            return jsonify({'error': '面试状态不正确'}), 400

        # 仅导出当前消息路径，不允许回退到全量消息
        current_message_id = interview.get('current_message_id')
        if not current_message_id:
            return jsonify({'error': '当前消息路径不存在，无法导出历史对话'}), 400

        export_payload = _build_history_export(interview_id, current_message_id)

        # 保存桩评估（本项目不负责真实评估）
        evaluation = {
            'overall_score': 0,
            'dimension_scores': {},
            'strengths': [],
            'weaknesses': [],
            'recommendation': '评估已打桩：仅导出当前消息路径历史对话',
            'feedback': json.dumps(export_payload, ensure_ascii=False)
        }
        database.create_evaluation({
            'interview_id': interview_id,
            'overall_score': evaluation['overall_score'],
            'dimension_scores': evaluation['dimension_scores'],
            'strengths': evaluation['strengths'],
            'weaknesses': evaluation['weaknesses'],
            'recommendation': evaluation['recommendation'],
            'feedback': evaluation['feedback']
        })

        # 鏇存柊鐘舵€佷负瀹屾垚
        database.update_interview_status(interview_id, InterviewStatus.COMPLETED)

        logger.info(f"面试完成（评估桩）: {interview_id}, 导出消息数: {export_payload['message_count']}")
        return jsonify({
            'message': '面试已完成',
            'evaluation': evaluation,
            'history_export': export_payload
        }), 200

    except Exception as e:
        logger.error(f"瀹屾垚闈㈣瘯澶辫触: {e}")
        return jsonify({'error': str(e)}), 500


@api_bp.route('/interviews/<int:interview_id>/history-export', methods=['GET'])
def export_interview_history(interview_id: int):
    """API endpoint."""
    try:
        interview = database.get_interview(interview_id)
        if not interview:
            return jsonify({'error': 'Interview not found'}), 404

        current_message_id = interview.get('current_message_id')
        if not current_message_id:
            return jsonify({'error': '当前消息路径不存在，无法导出历史对话'}), 400

        export_payload = _build_history_export(interview_id, current_message_id)
        return jsonify(export_payload), 200

    except Exception as e:
        logger.error(f"导出历史对话失败: {e}")
        return jsonify({'error': str(e)}), 500


@api_bp.route('/interviews/<int:interview_id>/chat', methods=['POST'])
def chat(interview_id: int):
    """API endpoint."""
    try:
        data = request.get_json()
        user_message = data.get('content')
        parent_id = data.get('parent_id')  # 鍙€夛細鐖舵秷鎭疘D
        branch_id = data.get('branch_id', 'main')  # 鍙€夛細鍒嗘敮ID锛岄粯璁や负 'main'

        if not user_message:
            return jsonify({'error': '消息内容不能为空'}), 400

        interview = database.get_interview(interview_id)
        if not interview:
            return jsonify({'error': 'Interview not found'}), 404

        if interview['status'] != InterviewStatus.IN_PROGRESS:
            return jsonify({'error': '面试未进行中'}), 400

        # 淇濆瓨鐢ㄦ埛娑堟伅锛堟敮鎸佹爲褰㈢粨鏋勶級
        user_message_id = database.create_message(
            interview_id,
            MessageType.USER,
            user_message,
            parent_id=parent_id,
            branch_id=branch_id
        )

        # 鑾峰彇瀵硅瘽鍘嗗彶
        messages = database.get_message_path(interview_id, user_message_id)

        # 鑾峰彇AI鏈嶅姟
        ai_service = get_ai_service()
        
        # 纭畾搴旇澶勪簬鐨勯樁娈?
        new_stage = ai_service.determine_current_stage(interview, messages, interview.get('duration_minutes', 30))
        current_stage = interview.get('current_stage', prompt_service.get_first_stage())
        
        # 濡傛灉闃舵鍙戠敓鍙樺寲锛屾洿鏂版暟鎹簱
        if new_stage != current_stage:
            database.update_interview_stage(interview_id, new_stage)
            logger.info(f"闈㈣瘯 {interview_id} 闃舵鍒囨崲: {current_stage} -> {new_stage}")
        
        # 鐢熸垚AI鍥炲锛堜紶鍏ュ綋鍓嶉樁娈碉級
        ai_response = ai_service.continue_interview(interview, messages, current_stage=new_stage)

        # 淇濆瓨AI鍥炲
        ai_message_id = database.create_message(
            interview_id,
            MessageType.ASSISTANT,
            ai_response,
            parent_id=user_message_id,
            branch_id=branch_id
        )
        database.update_interview_current_message(interview_id, ai_message_id)

        # 鑾峰彇杩涘害淇℃伅
        progress_info = ai_service.get_interview_progress(
            messages, 
            new_stage,
            interview.get('duration_minutes', 30),
            interview_config=interview,
        )

        logger.info(f"闈㈣瘯 {interview_id} 瀵硅瘽娑堟伅宸蹭繚瀛橈紝褰撳墠闃舵: {new_stage}")
        return jsonify({
            'role': MessageType.ASSISTANT,
            'content': ai_response,
            'current_stage': new_stage,
            'progress': progress_info
        }), 200

    except Exception as e:
        logger.error(f"瀵硅瘽澶辫触: {e}")
        return jsonify({'error': str(e)}), 500


@api_bp.route('/interviews/<int:interview_id>/chat/stream', methods=['POST'])
def chat_stream(interview_id: int):
    """API endpoint."""
    try:
        from flask import Response, stream_with_context
        from app.services.tts_service import get_tts_service

        data = request.get_json()
        user_message = data.get('content')
        parent_id = data.get('parent_id')  # 鍙€夛細鐖舵秷鎭疘D
        branch_id = data.get('branch_id', 'main')  # 鍙€夛細鍒嗘敮ID锛岄粯璁や负 'main'
        enable_tts = data.get('enable_tts', True)  # 鏄惁鍚敤 TTS锛岄粯璁ゅ惎鐢?

        if not user_message:
            return jsonify({'error': '消息内容不能为空'}), 400

        interview = database.get_interview(interview_id)
        if not interview:
            return jsonify({'error': 'Interview not found'}), 404

        if interview['status'] != InterviewStatus.IN_PROGRESS:
            return jsonify({'error': '面试未进行中'}), 400

        # 淇濆瓨鐢ㄦ埛娑堟伅锛堟敮鎸佹爲褰㈢粨鏋勶級
        user_message_id = database.create_message(
            interview_id,
            MessageType.USER,
            user_message,
            parent_id=parent_id,
            branch_id=branch_id
        )

        # 鑾峰彇瀵硅瘽鍘嗗彶
        messages = database.get_message_path(interview_id, user_message_id)

        # 鑾峰彇AI鏈嶅姟
        ai_service = get_ai_service()

        # 纭畾搴旇澶勪簬鐨勯樁娈?
        new_stage = ai_service.determine_current_stage(interview, messages, interview.get('duration_minutes', 30))
        current_stage = interview.get('current_stage', prompt_service.get_first_stage())

        # 濡傛灉闃舵鍙戠敓鍙樺寲锛屾洿鏂版暟鎹簱
        if new_stage != current_stage:
            database.update_interview_stage(interview_id, new_stage)
            logger.info(f"闈㈣瘯 {interview_id} 闃舵鍒囨崲: {current_stage} -> {new_stage}")

        def generate():
            """API endpoint."""
            full_response = ""
            sentence_buffer = ""  # 鐢ㄤ簬缂撳瓨鍙ュ瓙

            try:
                # 娴佸紡鐢熸垚AI鍥炲
                for chunk in ai_service.continue_interview_stream(interview, messages, current_stage=new_stage):
                    full_response += chunk
                    sentence_buffer += chunk

                    # 妫€鏌ユ槸鍚︽湁瀹屾暣鍙ュ瓙
                    if any(sep in sentence_buffer for sep in ['。', '！', '？', '.', '!', '?', '\n']):
                        # 鍒嗗壊鍙ュ瓙
                        sentences = []
                        remaining = ""

                        for char in sentence_buffer:
                            remaining += char
                            if char in ['。', '！', '？', '.', '!', '?', '\n']:
                                sentences.append(remaining.strip())
                                remaining = ""

                        sentence_buffer = remaining  # 淇濆瓨鏈畬鎴愮殑閮ㄥ垎

                        # 涓烘瘡涓畬鏁村彞瀛愮敓鎴?TTS
                        for sentence in sentences:
                            if sentence and enable_tts:
                                try:
                                    tts_service = get_tts_service()
                                    audio_base64 = tts_service.text_to_speech(sentence)

                                    # 鍙戦€佸寘鍚煶棰戠殑 SSE 鏁版嵁
                                    yield f"data: {json.dumps({'content': sentence, 'audio': audio_base64, 'sentence_end': True, 'done': False}, ensure_ascii=False)}\n\n"
                                except Exception as e:
                                    logger.error(f"TTS 鐢熸垚澶辫触: {e}")
                                    # TTS 澶辫触鏃跺彧鍙戦€佹枃鏈?
                                    yield f"data: {json.dumps({'content': sentence, 'audio': None, 'sentence_end': True, 'done': False}, ensure_ascii=False)}\n\n"
                            else:
                                # 涓嶅惎鐢?TTS 鏃跺彧鍙戦€佹枃鏈?
                                yield f"data: {json.dumps({'content': sentence, 'audio': None, 'sentence_end': True, 'done': False}, ensure_ascii=False)}\n\n"
                    else:
                        # 鍙戦€佷笉鍖呭惈闊抽鐨勬祦寮忔暟鎹紙瀹炴椂鏄剧ず锛?
                        yield f"data: {json.dumps({'content': chunk, 'audio': None, 'sentence_end': False, 'done': False}, ensure_ascii=False)}\n\n"

                # 澶勭悊鍓╀綑鐨勬枃鏈?
                if sentence_buffer.strip() and enable_tts:
                    try:
                        tts_service = get_tts_service()
                        audio_base64 = tts_service.text_to_speech(sentence_buffer.strip())
                        yield f"data: {json.dumps({'content': sentence_buffer.strip(), 'audio': audio_base64, 'sentence_end': True, 'done': False}, ensure_ascii=False)}\n\n"
                    except Exception as e:
                        logger.error(f"TTS 鐢熸垚澶辫触: {e}")
                        yield f"data: {json.dumps({'content': sentence_buffer.strip(), 'audio': None, 'sentence_end': True, 'done': False}, ensure_ascii=False)}\n\n"

                # 淇濆瓨瀹屾暣鐨凙I鍥炲锛屽苟鏇存柊褰撳墠娑堟伅鑺傜偣
                message_id = database.create_message(
                    interview_id,
                    MessageType.ASSISTANT,
                    full_response,
                    parent_id=user_message_id,
                    branch_id=branch_id
                )
                # 鏇存柊闈㈣瘯鐨勫綋鍓嶆秷鎭妭鐐?
                database.update_interview_current_message(interview_id, message_id)

                # 鑾峰彇杩涘害淇℃伅
                progress_info = ai_service.get_interview_progress(
                    messages,
                    new_stage,
                    interview.get('duration_minutes', 30),
                    interview_config=interview,
                )

                # 鍙戦€佸畬鎴愭秷鎭紝鍖呭惈瀹屾暣淇℃伅
                yield f"data: {json.dumps({'done': True, 'current_stage': new_stage, 'progress': progress_info}, ensure_ascii=False)}\n\n"

            except Exception as e:
                logger.error(f"娴佸紡瀵硅瘽澶辫触: {e}")
                yield f"data: {json.dumps({'error': str(e), 'done': True}, ensure_ascii=False)}\n\n"

        logger.info(f"闈㈣瘯 {interview_id} 寮€濮嬫祦寮忓璇? TTS鍚敤: {enable_tts}")
        return Response(
            stream_with_context(generate()),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'X-Accel-Buffering': 'no'
            }
        )

    except Exception as e:
        logger.error(f"瀵硅瘽澶辫触: {e}")
        return jsonify({'error': str(e)}), 500


@api_bp.route('/interviews/<int:interview_id>/evaluation', methods=['GET'])
def get_evaluation(interview_id: int):
    """API endpoint."""
    try:
        evaluation = database.get_evaluation(interview_id)
        if not evaluation:
            return jsonify({'error': 'Evaluation not found'}), 404

        return jsonify(evaluation), 200

    except Exception as e:
        logger.error(f"鑾峰彇璇勪及澶辫触: {e}")
        return jsonify({'error': str(e)}), 400


# ==================== 鍋ュ悍妫€鏌?====================

@api_bp.route('/health', methods=['GET'])
def health():
    """API endpoint."""
    return jsonify({'status': 'healthy', 'service': 'interview-service-api'})


# ==================== Prompt閰嶇疆鐩稿叧鎺ュ彛 ====================

@api_bp.route('/prompts/config', methods=['GET'])
def get_prompt_config():
    """API endpoint."""
    try:
        # 浠庢暟鎹簱鑾峰彇閰嶇疆锛屽鏋滄病鏈夊垯浣跨敤榛樿閰嶇疆
        config_data = database.get_prompt_config('default')
        
        if config_data:
            config = InterviewPromptConfig(**config_data)
        else:
            # 棣栨浣跨敤锛屼繚瀛橀粯璁ら厤缃?
            config_dict = DEFAULT_PROMPT_CONFIG.model_dump()
            database.save_prompt_config(config_dict, 'default')
            config = DEFAULT_PROMPT_CONFIG
        
        return jsonify(config.model_dump()), 200
        
    except Exception as e:
        logger.error(f"鑾峰彇Prompt閰嶇疆澶辫触: {e}")
        return jsonify({'error': str(e)}), 500


@api_bp.route('/prompts/config', methods=['POST'])
def update_prompt_config():
    """API endpoint."""
    try:
        data = request.get_json()
        
        # 楠岃瘉閰嶇疆
        config = InterviewPromptConfig(**data)
        
        # 淇濆瓨鍒版暟鎹簱
        database.save_prompt_config(config.model_dump(), 'default')
        
        logger.info("Prompt config updated")
        return jsonify({'message': '配置保存成功'}), 200
        
    except Exception as e:
        logger.error(f"鏇存柊Prompt閰嶇疆澶辫触: {e}")
        return jsonify({'error': str(e)}), 500


@api_bp.route('/prompts/reset', methods=['POST'])
def reset_prompt_config():
    """API endpoint."""
    try:
        config_dict = DEFAULT_PROMPT_CONFIG.model_dump()
        database.save_prompt_config(config_dict, 'default')
        
        logger.info("Prompt config reset")
        return jsonify({'message': 'Config reset to default', 'config': config_dict}), 200
        
    except Exception as e:
        logger.error(f"閲嶇疆Prompt閰嶇疆澶辫触: {e}")
        return jsonify({'error': str(e)}), 500


@api_bp.route('/interviews/<int:interview_id>/progress', methods=['GET'])
def get_interview_progress(interview_id: int):
    """API endpoint."""
    try:
        interview = database.get_interview(interview_id)
        if not interview:
            return jsonify({'error': 'Interview not found'}), 404

        # 鑾峰彇瀵硅瘽鍘嗗彶
        current_message_id = interview.get('current_message_id')
        if current_message_id:
            messages = database.get_message_path(interview_id, current_message_id)
        else:
            messages = database.get_messages(interview_id)

        # 鑾峰彇AI鏈嶅姟鏉ヨ绠楄繘搴?
        ai_service = get_ai_service()
        
        current_stage = interview.get('current_stage', prompt_service.get_first_stage())
        progress_info = ai_service.get_interview_progress(
            messages,
            current_stage,
            interview.get('duration_minutes', 30),
            interview_config=interview,
        )

        return jsonify(progress_info), 200

    except Exception as e:
        logger.error(f"鑾峰彇杩涘害澶辫触: {e}")
        return jsonify({'error': str(e)}), 400


@api_bp.route('/interviews/<int:interview_id>/current-message', methods=['PUT'])
def update_current_message(interview_id: int):
    """API endpoint."""
    try:
        data = request.get_json()
        message_id = data.get('message_id')

        if not message_id:
            return jsonify({'error': 'message_id is required'}), 400

        # 楠岃瘉娑堟伅鏄惁瀛樺湪
        messages = database.get_messages(interview_id)
        message_exists = any(msg['id'] == message_id for msg in messages)

        if not message_exists:
            return jsonify({'error': 'Message not found'}), 404

        # 鏇存柊褰撳墠娑堟伅鑺傜偣
        success = database.update_interview_current_message(interview_id, message_id)

        if success:
            logger.info(f"鏇存柊闈㈣瘯 {interview_id} 鐨勫綋鍓嶆秷鎭妭鐐逛负 {message_id}")
            return jsonify({'message': '更新成功'}), 200
        else:
            return jsonify({'error': '更新失败'}), 500

    except Exception as e:
        logger.error(f"鏇存柊褰撳墠娑堟伅鑺傜偣澶辫触: {e}")
        return jsonify({'error': str(e)}), 500


# ==================== 绠€鍘嗕笂浼犵浉鍏虫帴鍙?====================

def allowed_file(filename):
    """API endpoint."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@api_bp.route('/interviews/upload-resume', methods=['POST'])
def upload_resume():
    """API endpoint."""
    try:
        # 妫€鏌ユ槸鍚︽湁鏂囦欢
        if 'file' not in request.files:
            return jsonify({'error': '没有上传文件'}), 400

        file = request.files['file']

        # 妫€鏌ユ枃浠跺悕
        if file.filename == '':
            return jsonify({'error': 'Filename is empty'}), 400

        # 妫€鏌ユ枃浠剁被鍨?
        if not allowed_file(file.filename):
            return jsonify({'error': 'Only PDF files are supported'}), 400

        # 妫€鏌ユ枃浠跺ぇ灏?
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)

        if file_size > MAX_FILE_SIZE:
            return jsonify({'error': f'文件大小不能超过 {MAX_FILE_SIZE // (1024*1024)}MB'}), 400

        # 鐢熸垚鍞竴鏂囦欢鍚?
        original_filename = secure_filename(file.filename)
        file_id = str(uuid.uuid4())
        file_extension = original_filename.rsplit('.', 1)[1].lower()
        filename = f"{file_id}.{file_extension}"
        filepath = os.path.join(UPLOAD_FOLDER, filename)

        # 淇濆瓨鏂囦欢
        file.save(filepath)
        logger.info(f"绠€鍘嗘枃浠跺凡淇濆瓨: {filepath}")

        # 瑙ｆ瀽PDF鍐呭
        try:
            resume_text = extract_text_from_pdf(filepath)
            logger.info(f"绠€鍘嗚В鏋愭垚鍔燂紝鍐呭闀垮害: {len(resume_text)}")
        except Exception as e:
            logger.error(f"绠€鍘嗚В鏋愬け璐? {e}")
            resume_text = None

        return jsonify({
            'message': 'Resume uploaded successfully',
            'file_id': file_id,
            'original_filename': original_filename,
            'file_path': filepath,
            'resume_text': resume_text
        }), 200

    except Exception as e:
        logger.error(f"绠€鍘嗕笂浼犲け璐? {e}")
        return jsonify({'error': str(e)}), 500


def extract_text_from_pdf(pdf_path):
    """API endpoint."""
    try:
        import PyPDF2

        text_content = []
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            num_pages = len(pdf_reader.pages)

            for page_num in range(num_pages):
                page = pdf_reader.pages[page_num]
                text = page.extract_text()
                if text.strip():
                    text_content.append(text)

        return '\n\n'.join(text_content)

    except ImportError:
        logger.warning("PyPDF2 鏈畨瑁咃紝灏濊瘯浣跨敤 pdfplumber")
        try:
            import pdfplumber

            text_content = []
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text and text.strip():
                        text_content.append(text)

            return '\n\n'.join(text_content)

        except ImportError:
            logger.error("鏃㈡病鏈夊畨瑁?PyPDF2 涔熸病鏈夊畨瑁?pdfplumber锛屾棤娉曡В鏋怭DF")
            return None
    except Exception as e:
        logger.error(f"PDF 瑙ｆ瀽澶辫触: {e}")
        return None


@api_bp.route('/stages/config', methods=['GET'])
def get_stages_config():
    """API endpoint."""
    try:
        stage_models = prompt_service.get_stage_configs()
        stages_config = [
            {
                'stage': s.stage,
                'name': s.name,
                'description': s.description,
                'max_turns': s.max_turns,
                'min_turns': s.min_turns,
                'time_allocation': s.time_allocation,
                'system_instruction': s.system_instruction,
                'enabled': s.enabled,
                'order': getattr(s, 'order', 0),
            }
            for s in stage_models
        ]

        return jsonify({
            'stages': stages_config,
            'total_duration': sum(s['time_allocation'] for s in stages_config),
            'total_max_turns': sum(s['max_turns'] for s in stages_config)
        }), 200

    except Exception as e:
        logger.error(f"鑾峰彇闃舵閰嶇疆澶辫触: {e}")
        return jsonify({'error': str(e)}), 400


# ==================== 闈㈣瘯蹇収鐩稿叧鎺ュ彛 ====================

@api_bp.route('/interviews/<int:interview_id>/snapshots', methods=['POST'])
def create_snapshot(interview_id: int):
    """API endpoint."""
    try:
        data = request.get_json()
        name = data.get('name')
        description = data.get('description', '')

        if not name:
            return jsonify({'error': '快照名称不能为空'}), 400

        # 鑾峰彇褰撳墠闈㈣瘯鐘舵€?
        interview = database.get_interview(interview_id)
        if not interview:
            return jsonify({'error': 'Interview not found'}), 404

        messages = database.get_messages(interview_id)

        # 杈呭姪鍑芥暟:灏?datetime 瀵硅薄杞崲涓哄瓧绗︿覆
        def serialize_datetime(obj):
            """API endpoint."""
            if isinstance(obj, dict):
                return {k: serialize_datetime(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [serialize_datetime(item) for item in obj]
            elif hasattr(obj, 'isoformat'):  # datetime 瀵硅薄
                return obj.isoformat()
            else:
                return obj

        # 搴忓垪鍖栨暟鎹?澶勭悊 datetime 瀵硅薄
        serialized_interview = serialize_datetime(dict(interview))
        serialized_messages = serialize_datetime(messages)

        # 鏋勫缓蹇収鏁版嵁鍐呭
        snapshot_content = {
            'interview': serialized_interview,
            'messages': serialized_messages,
            'current_stage': interview.get('current_stage'),
            'created_at': interview.get('created_at').isoformat() if interview.get('created_at') else None
        }

        # 鏋勫缓浼犻€掔粰鏁版嵁搴撶殑鍙傛暟
        snapshot_params = {
            'interview_id': interview_id,
            'name': name,
            'description': description,
            'snapshot_data': snapshot_content
        }

        snapshot_id = database.create_snapshot(snapshot_params)

        logger.info(f"????: snapshot_id={snapshot_id}")
        return jsonify({
            'message': '??????',
            'snapshot_id': snapshot_id
        }), 201

    except Exception as e:
        logger.error(f"鍒涘缓蹇収澶辫触: {e}")
        return jsonify({'error': str(e)}), 500


@api_bp.route('/interviews/<int:interview_id>/snapshots', methods=['GET'])
def list_snapshots(interview_id: int):
    """API endpoint."""
    try:
        snapshots = database.get_snapshots(interview_id)

        # 杞崲涓哄搷搴旀牸寮忥紙涓嶅寘鍚畬鏁寸殑 snapshot_data锛?
        result = []
        for snapshot in snapshots:
            # snapshot_data 鏄?JSONB,浼氳 psycopg2 鑷姩杞崲涓哄瓧鍏?
            snapshot_data = snapshot.get('snapshot_data', {})

            # 濡傛灉浠嶇劧鏄瓧绗︿覆(鏌愪簺鎯呭喌涓?,鍒欒В鏋?
            if isinstance(snapshot_data, str):
                import json
                snapshot_data = json.loads(snapshot_data)

            result.append({
                'id': snapshot['id'],
                'name': snapshot['name'],
                'description': snapshot['description'],
                'created_at': snapshot['created_at'],
                'message_count': len(snapshot_data.get('messages', []))
            })

        return jsonify(result), 200

    except Exception as e:
        logger.error(f"鑾峰彇蹇収鍒楄〃澶辫触: {e}")
        return jsonify({'error': str(e)}), 500


@api_bp.route('/snapshots/<int:snapshot_id>', methods=['GET'])
def get_snapshot(snapshot_id: int):
    """API endpoint."""
    try:
        snapshot = database.get_snapshot(snapshot_id)
        if not snapshot:
            return jsonify({'error': 'Snapshot not found'}), 404

        # snapshot_data 鏄?JSONB,浼氳 psycopg2 鑷姩杞崲涓哄瓧鍏?
        snapshot_data = snapshot.get('snapshot_data', {})

        # 濡傛灉浠嶇劧鏄瓧绗︿覆(鏌愪簺鎯呭喌涓?,鍒欒В鏋?
        if isinstance(snapshot_data, str):
            import json
            snapshot_data = json.loads(snapshot_data)

        return jsonify({
            'id': snapshot['id'],
            'name': snapshot['name'],
            'description': snapshot['description'],
            'created_at': snapshot['created_at'],
            'data': snapshot_data
        }), 200

    except Exception as e:
        logger.error(f"鑾峰彇蹇収璇︽儏澶辫触: {e}")
        return jsonify({'error': str(e)}), 500


@api_bp.route('/snapshots/<int:snapshot_id>/load', methods=['POST'])
def load_snapshot(snapshot_id: int):
    """API endpoint."""
    try:
        snapshot = database.get_snapshot(snapshot_id)
        if not snapshot:
            return jsonify({'error': 'Snapshot not found'}), 404

        # snapshot_data 鏄?JSONB,浼氳 psycopg2 鑷姩杞崲涓哄瓧鍏?
        snapshot_data = snapshot.get('snapshot_data', {})

        # 濡傛灉浠嶇劧鏄瓧绗︿覆(鏌愪簺鎯呭喌涓?,鍒欒В鏋?
        if isinstance(snapshot_data, str):
            import json
            snapshot_data = json.loads(snapshot_data)

        # 鑾峰彇鍘熼潰璇旾D
        original_interview_id = snapshot_data['interview']['id']

        # 鎭㈠娑堟伅鍜岄樁娈靛埌鏁版嵁搴?
        # 娉ㄦ剰锛氳繖閲屾垜浠彧鏄繑鍥炲揩鐓ф暟鎹紝瀹為檯鐨?鎭㈠"鐢卞墠绔喅瀹氬浣曞鐞?
        # 鍙互閫夋嫨鍒涘缓鏂伴潰璇曟垨瑕嗙洊鐜版湁闈㈣瘯

        logger.info(f"????: snapshot_id={snapshot_id}")
        return jsonify({
            'message': '??????',
            'snapshot_id': snapshot_id,
            'original_interview_id': original_interview_id,
            'data': snapshot_data
        }), 200

    except Exception as e:
        logger.error(f"鍔犺浇蹇収澶辫触: {e}")
        return jsonify({'error': str(e)}), 500


@api_bp.route('/snapshots/<int:snapshot_id>', methods=['DELETE'])
def delete_snapshot(snapshot_id: int):
    """API endpoint."""
    try:
        success = database.delete_snapshot(snapshot_id)
        if not success:
            return jsonify({'error': 'Snapshot not found'}), 404

        logger.info(f"????: snapshot_id={snapshot_id}")
        return jsonify({'message': '快照删除成功'}), 200

    except Exception as e:
        logger.error(f"鍒犻櫎蹇収澶辫触: {e}")
        return jsonify({'error': str(e)}), 500


# ==================== ASR 璇煶璇嗗埆鎺ュ彛 ====================

@api_bp.route('/asr/transcribe', methods=['POST'])
def transcribe_audio():
    """API endpoint."""
    try:
        # 妫€鏌?ASR 鏈嶅姟鏄惁鍙敤
        asr_service = get_asr_service()
        if not asr_service:
            return jsonify({'error': 'ASR service unavailable'}), 503

        # 妫€鏌ユ槸鍚︽湁鏂囦欢涓婁紶
        if 'audio' not in request.files:
            return jsonify({'error': 'Audio file not found'}), 400

        audio_file = request.files['audio']
        if audio_file.filename == '':
            return jsonify({'error': '未选择文件'}), 400

        # 璇诲彇闊抽鏁版嵁
        audio_data = audio_file.read()

        if len(audio_data) == 0:
            return jsonify({'error': '音频文件为空'}), 400

        # 闄愬埗闊抽澶у皬 (鏈€澶?25MB)
        MAX_AUDIO_SIZE = 25 * 1024 * 1024
        if len(audio_data) > MAX_AUDIO_SIZE:
            return jsonify({'error': f'音频文件不能超过 {MAX_AUDIO_SIZE // (1024*1024)}MB'}), 400

        logger.info(f"鏀跺埌闊抽鏂囦欢, 澶у皬: {len(audio_data)} bytes")

        # 璋冪敤 ASR 鏈嶅姟杩涜璇嗗埆
        text = asr_service.transcribe(audio_data)

        logger.info(f"ASR 璇嗗埆鎴愬姛, 鏂囨湰: {text[:100]}...")

        return jsonify({
            'text': text,
            'text_length': len(text)
        }), 200

    except Exception as e:
        logger.error(f"璇煶璇嗗埆澶辫触: {e}")
        return jsonify({'error': f'语音识别失败: {str(e)}'}), 500


@api_bp.route('/asr/status', methods=['GET'])
def get_asr_status():
    """API endpoint."""
    try:
        asr_service = get_asr_service()

        if asr_service:
            return jsonify({
                'available': True,
                'provider': type(asr_service).__name__,
                'message': 'ASR 鏈嶅姟鍙敤'
            }), 200
        else:
            return jsonify({
                'available': False,
                'provider': None,
                'message': 'ASR ????????? OPENAI_API_KEY ????'
            }), 503

    except Exception as e:
        logger.error(f"鑾峰彇 ASR 鐘舵€佸け璐? {e}")
        return jsonify({'error': str(e)}), 500


