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
        self._validate_required_secrets()

    def _load_config(self) -> dict:
        """加载配置文件"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"配置文件不存在: {self.config_path}")

        with open(self.config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        # 递归处理环境变量占位符 ${VAR:default}
        return self._process_env_vars(config)

    def _process_env_vars(self, config):
        """递归处理配置中的环境变量占位符"""
        if isinstance(config, dict):
            return {k: self._process_env_vars(v) for k, v in config.items()}
        elif isinstance(config, list):
            return [self._process_env_vars(item) for item in config]
        elif isinstance(config, str):
            # 处理 ${VAR:default} 格式
            import re
            match = re.match(r'\$\{([^:}]+)(?::([^}]*))?\}', config)
            if match:
                var_name = match.group(1)
                default_value = match.group(2) if match.group(2) is not None else ''
                return os.getenv(var_name, default_value)
            return config
        else:
            return config

    def _apply_env_overrides(self):
        """仅应用敏感环境变量覆盖"""
        # AI 密钥（敏感）
        if ai_key := os.getenv("AI_API_KEY"):
            self._config['ai']['api_key'] = ai_key

        # 数据库密码（敏感）
        if db_password := os.getenv("DB_PASSWORD"):
            self._config['database']['password'] = db_password

        # ASR 密钥（敏感，可选）
        if asr_api_key := os.getenv("ASR_API_KEY"):
            self._config['asr']['api_key'] = asr_api_key

    def _validate_required_secrets(self):
        """启动时校验必填敏感配置，缺失则快速失败。"""
        missing = []
        if not (self._config.get('ai', {}).get('api_key') or '').strip():
            missing.append("AI_API_KEY")
        if not (self._config.get('database', {}).get('password') or '').strip():
            missing.append("DB_PASSWORD")

        if missing:
            raise ValueError(
                "Missing required secret environment variables: "
                + ", ".join(missing)
                + ". Please set them in backend/.env."
            )

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

    # ASR 配置属性
    @property
    def asr_api_key(self) -> str:
        # 默认复用 AI API Key
        asr_config = self._config.get('asr', {})
        return asr_config.get('api_key', '') or self.ai_api_key

    @property
    def asr_base_url(self) -> str:
        # 默认复用 AI Base URL
        asr_config = self._config.get('asr', {})
        return asr_config.get('base_url', '') or self.ai_base_url

    @property
    def asr_model(self) -> str:
        return self._config.get('asr', {}).get('model', 'whisper-1')

    @property
    def asr_enabled(self) -> bool:
        return self._config.get('asr', {}).get('enabled', True)

    @property
    def cors_origins(self) -> list:
        return self.get('cors.origins', ['*'])

    def __repr__(self) -> str:
        return f"Settings(config_path={self.config_path})"


# 全局配置实例
settings = Settings()
