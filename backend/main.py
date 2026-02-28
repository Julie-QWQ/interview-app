"""
Flask应用入口文件
"""
import sys
import logging
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from app import create_app
from app.api import init_api
from config.settings import settings


def setup_logging():
    """配置日志"""
    log_level = settings.get('logging.level', 'INFO')
    log_format = settings.get('logging.format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    logging.basicConfig(
        level=getattr(logging, log_level),
        format=log_format,
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('logs/app.log', encoding='utf-8') if Path('logs').exists() else logging.StreamHandler()
        ]
    )


def main():
    """主函数"""
    # 创建日志目录
    Path('logs').mkdir(exist_ok=True)

    # 配置日志
    setup_logging()
    logger = logging.getLogger(__name__)

    # 创建应用
    app = create_app()

    # 初始化API
    init_api(app.config['settings'])

    logger.info(f"启动 {settings.app_name} v{settings.app_version}")
    logger.info(f"监听地址: {settings.host}:{settings.port}")

    # 运行应用
    app.run(
        host=settings.host,
        port=settings.port,
        debug=settings.debug
    )


if __name__ == '__main__':
    main()
