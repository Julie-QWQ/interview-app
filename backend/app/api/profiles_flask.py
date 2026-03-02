"""
画像插件API接口 (Flask版本)
"""
from flask import request, jsonify
import logging

from app.db import database

logger = logging.getLogger(__name__)


def register_profile_routes(api_bp):
    """注册画像相关路由"""

    @api_bp.route('/profiles/plugins', methods=['GET'])
    def list_plugins():
        """获取画像插件列表"""
        try:
            plugin_type = request.args.get('type')  # position | interviewer
            is_system = request.args.get('is_system')

            # 转换 is_system 参数
            is_system_bool = None
            if is_system is not None:
                is_system_bool = is_system.lower() == 'true'

            plugins = database.list_profile_plugins(
                plugin_type=plugin_type,
                is_system=is_system_bool
            )

            return jsonify({
                'success': True,
                'data': plugins
            }), 200

        except Exception as e:
            logger.error(f"获取插件列表失败: {e}")
            return jsonify({'error': '获取插件列表失败'}), 500

    @api_bp.route('/profiles/plugins', methods=['POST'])
    def create_plugin():
        """创建自定义画像插件"""
        try:
            data = request.get_json()
            plugin_id = data.get('plugin_id')

            # 检查是否已存在
            existing = database.get_profile_plugin(plugin_id)
            if existing:
                return jsonify({'error': '插件ID已存在'}), 400

            # 创建插件
            new_plugin_id = database.create_profile_plugin(data)

            return jsonify({
                'success': True,
                'message': '创建成功',
                'data': {'plugin_id': plugin_id}
            }), 201

        except Exception as e:
            logger.error(f"创建插件失败: {e}")
            return jsonify({'error': '创建插件失败'}), 500

    @api_bp.route('/profiles/plugins/<plugin_id>', methods=['GET'])
    def get_plugin(plugin_id):
        """获取插件详情"""
        try:
            plugin = database.get_profile_plugin(plugin_id)
            if not plugin:
                return jsonify({'error': '插件不存在'}), 404

            return jsonify({
                'success': True,
                'data': plugin
            }), 200

        except Exception as e:
            logger.error(f"获取插件详情失败: {e}")
            return jsonify({'error': '获取插件详情失败'}), 500

    @api_bp.route('/profiles/plugins/<plugin_id>', methods=['PUT'])
    def update_plugin(plugin_id):
        """更新插件配置"""
        try:
            data = request.get_json()

            # 检查插件是否存在
            existing = database.get_profile_plugin(plugin_id)
            if not existing:
                return jsonify({'error': '插件不存在'}), 404

            # 系统预设插件不允许修改
            if existing['is_system']:
                return jsonify({'error': '系统预设插件不允许修改'}), 403

            success = database.update_profile_plugin(plugin_id, data)
            if not success:
                return jsonify({'error': '更新失败'}), 500

            return jsonify({
                'success': True,
                'message': '更新成功'
            }), 200

        except Exception as e:
            logger.error(f"更新插件失败: {e}")
            return jsonify({'error': '更新插件失败'}), 500

    @api_bp.route('/profiles/plugins/<plugin_id>', methods=['DELETE'])
    def delete_plugin(plugin_id):
        """删除自定义插件"""
        try:
            # 检查插件是否存在
            existing = database.get_profile_plugin(plugin_id)
            if not existing:
                return jsonify({'error': '插件不存在'}), 404

            # 系统预设插件不允许删除
            if existing['is_system']:
                return jsonify({'error': '系统预设插件不允许删除'}), 403

            success = database.delete_profile_plugin(plugin_id)
            if not success:
                return jsonify({'error': '删除失败'}), 500

            return jsonify({
                'success': True,
                'message': '删除成功'
            }), 200

        except Exception as e:
            logger.error(f"删除插件失败: {e}")
            return jsonify({'error': '删除插件失败'}), 500

    @api_bp.route('/profiles/interviews/<int:interview_id>/apply', methods=['POST'])
    def apply_profiles(interview_id):
        """应用画像到面试"""
        try:
            data = request.get_json()
            position_plugin_id = data.get('position_plugin_id')
            interviewer_plugin_id = data.get('interviewer_plugin_id')
            custom_config = data.get('custom_config')

            # 检查插件是否存在
            position_plugin = database.get_profile_plugin(position_plugin_id)
            if not position_plugin:
                return jsonify({'error': f'岗位插件 {position_plugin_id} 不存在'}), 404

            interviewer_plugin = database.get_profile_plugin(interviewer_plugin_id)
            if not interviewer_plugin:
                return jsonify({'error': f'面试官插件 {interviewer_plugin_id} 不存在'}), 404

            profile_id = database.apply_interview_profile(
                interview_id,
                position_plugin_id,
                interviewer_plugin_id,
                custom_config
            )

            return jsonify({
                'success': True,
                'message': '应用成功',
                'data': {'profile_id': profile_id}
            }), 200

        except Exception as e:
            logger.error(f"应用画像失败: {e}")
            return jsonify({'error': '应用画像失败'}), 500

    @api_bp.route('/profiles/interviews/<int:interview_id>', methods=['GET'])
    def get_interview_profiles(interview_id):
        """获取面试的画像配置"""
        try:
            profile = database.get_interview_profile(interview_id)
            if not profile:
                return jsonify({'error': '该面试未配置画像'}), 404

            return jsonify({
                'success': True,
                'data': profile
            }), 200

        except Exception as e:
            logger.error(f"获取面试画像失败: {e}")
            return jsonify({'error': '获取面试画像失败'}), 500

    logger.info("画像API路由注册完成")
