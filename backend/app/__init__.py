"""
Flask应用初始化
"""
from flask import Flask
from flask_cors import CORS
from .db.database import init_db


def create_app(config_path=None):
    """创建Flask应用实例"""
    app = Flask(__name__)

    # 加载配置
    from config.settings import settings
    app.config['settings'] = settings

    # 启用CORS
    CORS(app,
         origins=settings.cors_origins,
         methods=settings.get('cors.methods', ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS']),
         supports_credentials=True)

    # 初始化数据库
    init_db(settings.database_url)

    # 注册蓝图
    from .api import api_bp
    app.register_blueprint(api_bp, url_prefix='/api')

    # 健康检查端点
    @app.route('/health')
    def health_check():
        return {'status': 'healthy', 'service': 'interview-service'}

    return app
