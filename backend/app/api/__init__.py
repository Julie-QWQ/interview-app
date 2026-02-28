"""
API路由模块
"""
from flask import Blueprint, request, jsonify
from app.services.ai_service import get_ai_service, init_ai_service
from app.db import database
from app.models.schemas import (
    CreateInterviewRequest, InterviewResponse, InterviewDetailResponse,
    MessageResponse, ChatMessage, InterviewStatus, MessageType
)
from app.models.interview_stage import InterviewStage
import logging

logger = logging.getLogger(__name__)

# 创建API蓝图
api_bp = Blueprint('api', __name__)


def init_api(settings):
    """初始化API"""
    init_ai_service(settings)


# ==================== 面试相关接口 ====================

@api_bp.route('/interviews', methods=['POST'])
def create_interview():
    """创建面试"""
    try:
        data = request.get_json()
        interview_req = CreateInterviewRequest(**data)

        # 创建面试记录
        interview_id = database.create_interview({
            'candidate_name': interview_req.candidate_name,
            'position': interview_req.position,
            'skill_domain': interview_req.skill_domain.value,
            'skills': interview_req.skills,
            'experience_level': interview_req.experience_level,
            'duration_minutes': interview_req.duration_minutes,
            'additional_requirements': interview_req.additional_requirements
        })

        # 获取面试详情
        interview = database.get_interview(interview_id)

        logger.info(f"创建面试成功: {interview_id}")
        return jsonify(InterviewResponse(**interview).model_dump()), 201

    except Exception as e:
        logger.error(f"创建面试失败: {e}")
        return jsonify({'error': str(e)}), 400


@api_bp.route('/interviews', methods=['GET'])
def list_interviews():
    """列出面试"""
    try:
        status = request.args.get('status')
        limit = int(request.args.get('limit', 50))
        offset = int(request.args.get('offset', 0))

        interviews = database.list_interviews(limit=limit, offset=offset, status=status)

        return jsonify([InterviewResponse(**i).model_dump() for i in interviews]), 200

    except Exception as e:
        logger.error(f"列出面试失败: {e}")
        return jsonify({'error': str(e)}), 400


@api_bp.route('/interviews/<int:interview_id>', methods=['GET'])
def get_interview(interview_id: int):
    """获取面试详情"""
    try:
        interview = database.get_interview(interview_id)
        if not interview:
            return jsonify({'error': '面试不存在'}), 404

        # 获取消息历史
        messages = database.get_messages(interview_id)

        # 获取当前阶段和进度信息
        current_stage = interview.get('current_stage')
        stage_progress = None
        
        if current_stage and interview['status'] == InterviewStatus.IN_PROGRESS:
            ai_service = get_ai_service()
            try:
                stage_progress = ai_service.get_interview_progress(
                    messages,
                    current_stage,
                    interview.get('duration_minutes', 30)
                )
            except:
                pass  # 如果获取进度失败，忽略

        # 构建详情响应
        interview_detail = InterviewDetailResponse(
            **interview,
            messages=[MessageResponse(**m).model_dump() for m in messages],
            current_stage=current_stage,
            stage_progress=stage_progress
        )

        return jsonify(interview_detail.model_dump()), 200

    except Exception as e:
        logger.error(f"获取面试详情失败: {e}")
        return jsonify({'error': str(e)}), 400


@api_bp.route('/interviews/<int:interview_id>', methods=['DELETE'])
def delete_interview(interview_id: int):
    """删除面试"""
    try:
        success = database.delete_interview(interview_id)
        if not success:
            return jsonify({'error': '面试不存在'}), 404

        logger.info(f"删除面试成功: {interview_id}")
        return jsonify({'message': '删除成功'}), 200

    except Exception as e:
        logger.error(f"删除面试失败: {e}")
        return jsonify({'error': str(e)}), 400


@api_bp.route('/interviews/<int:interview_id>/start', methods=['POST'])
def start_interview(interview_id: int):
    """开始面试"""
    try:
        interview = database.get_interview(interview_id)
        if not interview:
            return jsonify({'error': '面试不存在'}), 404

        if interview['status'] != InterviewStatus.CREATED:
            return jsonify({'error': '面试状态不正确'}), 400

        # 更新状态为进行中，并设置初始阶段
        database.update_interview_status(interview_id, InterviewStatus.IN_PROGRESS)
        database.update_interview_stage(interview_id, InterviewStage.WELCOME.value)

        # 获取AI服务
        ai_service = get_ai_service()

        # 生成开场消息
        welcome_message = ai_service.start_interview(interview)

        # 保存AI消息
        database.create_message(interview_id, MessageType.ASSISTANT, welcome_message)

        logger.info(f"开始面试: {interview_id}, 阶段: {InterviewStage.WELCOME.value}")
        return jsonify({
            'message': '面试开始成功',
            'welcome_message': welcome_message,
            'current_stage': InterviewStage.WELCOME.value
        }), 200

    except Exception as e:
        logger.error(f"开始面试失败: {e}")
        return jsonify({'error': str(e)}), 500


@api_bp.route('/interviews/<int:interview_id>/complete', methods=['POST'])
def complete_interview(interview_id: int):
    """完成面试并生成评估"""
    try:
        interview = database.get_interview(interview_id)
        if not interview:
            return jsonify({'error': '面试不存在'}), 404

        if interview['status'] != InterviewStatus.IN_PROGRESS:
            return jsonify({'error': '面试状态不正确'}), 400

        # 获取对话历史
        messages = database.get_messages(interview_id)

        # 获取AI服务并生成评估
        ai_service = get_ai_service()
        evaluation = ai_service.evaluate_interview(interview, messages)

        # 保存评估
        database.create_evaluation({
            'interview_id': interview_id,
            'overall_score': evaluation['overall_score'],
            'dimension_scores': evaluation['dimension_scores'],
            'strengths': evaluation['strengths'],
            'weaknesses': evaluation['weaknesses'],
            'recommendation': evaluation['recommendation'],
            'feedback': evaluation['feedback']
        })

        # 更新状态为完成
        database.update_interview_status(interview_id, InterviewStatus.COMPLETED)

        logger.info(f"完成面试: {interview_id}, 评估分数: {evaluation['overall_score']}")
        return jsonify({
            'message': '面试完成',
            'evaluation': evaluation
        }), 200

    except Exception as e:
        logger.error(f"完成面试失败: {e}")
        return jsonify({'error': str(e)}), 500


@api_bp.route('/interviews/<int:interview_id>/chat', methods=['POST'])
def chat(interview_id: int):
    """发送消息并获取AI回复"""
    try:
        data = request.get_json()
        user_message = data.get('content')

        if not user_message:
            return jsonify({'error': '消息内容不能为空'}), 400

        interview = database.get_interview(interview_id)
        if not interview:
            return jsonify({'error': '面试不存在'}), 404

        if interview['status'] != InterviewStatus.IN_PROGRESS:
            return jsonify({'error': '面试未进行中'}), 400

        # 保存用户消息
        database.create_message(interview_id, MessageType.USER, user_message)

        # 获取对话历史
        messages = database.get_messages(interview_id)

        # 获取AI服务
        ai_service = get_ai_service()
        
        # 确定应该处于的阶段
        new_stage = ai_service.determine_current_stage(messages, interview.get('duration_minutes', 30))
        current_stage = interview.get('current_stage', InterviewStage.WELCOME.value)
        
        # 如果阶段发生变化，更新数据库
        if new_stage.value != current_stage:
            database.update_interview_stage(interview_id, new_stage.value)
            logger.info(f"面试 {interview_id} 阶段切换: {current_stage} -> {new_stage.value}")
        
        # 生成AI回复（传入当前阶段）
        ai_response = ai_service.continue_interview(interview, messages, current_stage=new_stage.value)

        # 保存AI回复
        database.create_message(interview_id, MessageType.ASSISTANT, ai_response)

        # 获取进度信息
        progress_info = ai_service.get_interview_progress(
            messages, 
            new_stage.value, 
            interview.get('duration_minutes', 30)
        )

        logger.info(f"面试 {interview_id} 对话消息已保存，当前阶段: {new_stage.value}")
        return jsonify({
            'role': MessageType.ASSISTANT,
            'content': ai_response,
            'current_stage': new_stage.value,
            'progress': progress_info
        }), 200

    except Exception as e:
        logger.error(f"对话失败: {e}")
        return jsonify({'error': str(e)}), 500


@api_bp.route('/interviews/<int:interview_id>/evaluation', methods=['GET'])
def get_evaluation(interview_id: int):
    """获取面试评估"""
    try:
        evaluation = database.get_evaluation(interview_id)
        if not evaluation:
            return jsonify({'error': '评估不存在'}), 404

        return jsonify(evaluation), 200

    except Exception as e:
        logger.error(f"获取评估失败: {e}")
        return jsonify({'error': str(e)}), 400


# ==================== 健康检查 ====================

@api_bp.route('/health', methods=['GET'])
def health():
    """健康检查"""
    return jsonify({'status': 'healthy', 'service': 'interview-service-api'})


@api_bp.route('/interviews/<int:interview_id>/progress', methods=['GET'])
def get_interview_progress(interview_id: int):
    """获取面试进度"""
    try:
        interview = database.get_interview(interview_id)
        if not interview:
            return jsonify({'error': '面试不存在'}), 404

        # 获取对话历史
        messages = database.get_messages(interview_id)

        # 获取AI服务来计算进度
        ai_service = get_ai_service()
        
        current_stage = interview.get('current_stage', InterviewStage.WELCOME.value)
        progress_info = ai_service.get_interview_progress(
            messages,
            current_stage,
            interview.get('duration_minutes', 30)
        )

        return jsonify(progress_info), 200

    except Exception as e:
        logger.error(f"获取进度失败: {e}")
        return jsonify({'error': str(e)}), 400
