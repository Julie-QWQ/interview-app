"""
配置管理模块
"""
import os
from pathlib import Path
from typing import Any
import yaml


class Settings:
    """应用配置类"""

    def __init__(self, config_path: str = None):
        if config_path is None:
            config_path = Path(__file__).parent / "config.yaml"

        self.config_path = Path(config_path)
        self._config = self._load_config()
        self._apply_env_overrides()

    def _load_config(self) -> dict:
        """加载配置文件"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"配置文件不存在: {self.config_path}")

        with open(self.config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    def _apply_env_overrides(self):
        """应用环境变量覆盖"""
        # AI配置从环境变量读取
        if ai_key := os.getenv("AI_API_KEY"):
            self._config['ai']['api_key'] = ai_key
        if base_url := os.getenv("AI_BASE_URL"):
            self._config['ai']['base_url'] = base_url
        if ai_model := os.getenv("AI_MODEL"):
            self._config['ai']['model'] = ai_model

        # 数据库配置从环境变量读取
        if db_host := os.getenv("DB_HOST"):
            self._config['database']['host'] = db_host
        if db_name := os.getenv("DB_NAME"):
            self._config['database']['name'] = db_name
        if db_user := os.getenv("DB_USER"):
            self._config['database']['user'] = db_user
        if db_password := os.getenv("DB_PASSWORD"):
            self._config['database']['password'] = db_password

    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值，支持点号分隔的路径"""
        keys = key.split('.')
        value = self._config

        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    return default
            else:
                return default

        return value

    @property
    def app_name(self) -> str:
        return self.get('app.name', 'interview-service')

    @property
    def app_version(self) -> str:
        return self.get('app.version', '0.1.0')

    @property
    def debug(self) -> bool:
        return self.get('app.debug', True)

    @property
    def host(self) -> str:
        return self.get('app.host', '0.0.0.0')

    @property
    def port(self) -> int:
        return self.get('app.port', 8000)

    @property
    def database_url(self) -> str:
        """获取数据库连接URL"""
        db_config = self._config.get('database', {})
        return (
            f"postgresql://{db_config.get('user', 'postgres')}:"
            f"{db_config.get('password', 'postgres')}@"
            f"{db_config.get('host', 'localhost')}:{db_config.get('port', 5432)}/"
            f"{db_config.get('name', 'interview_db')}"
        )

    @property
    def ai_api_key(self) -> str:
        return self._config['ai'].get('api_key', '')

    @property
    def ai_base_url(self) -> str:
        return self._config['ai'].get('base_url', 'https://api.openai.com/v1')

    @property
    def ai_model(self) -> str:
        return self._config['ai'].get('model', 'gpt-4o-mini')

    @property
    def ai_temperature(self) -> float:
        return self._config['ai'].get('temperature', 0.7)

    @property
    def cors_origins(self) -> list:
        return self.get('cors.origins', ['*'])

    def __repr__(self) -> str:
        return f"Settings(config_path={self.config_path})"


# 全局配置实例
settings = Settings()
