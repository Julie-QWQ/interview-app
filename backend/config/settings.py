"""
配置管理模块
"""
import os
from pathlib import Path
from typing import Any
from copy import deepcopy
import yaml

DEFAULT_VOICE_CONFIG = {
    'enabled': True,
    'always_on_enabled': True,
    'noise_floor_sample_ms': 800,
    'speech_start_threshold': 1.6,
    'min_speech_ms': 220,
    'end_silence_ms': 750,
    'max_segment_ms': 15000,
    'pre_roll_ms': 300,
    'barge_in_ms': 250,
    'chunk_retention_ms': 20000,
    'min_threshold': 0.0015,
    'timeslice_ms': 100,
    'auto_send_min_chars': 8,
    'typing_grace_ms': 1200,
    'short_noise_words': ['嗯', '啊', '哦', '额', '呃', '唉', '哈', '噢']
}


DEFAULT_EXPRESSION_ANALYSIS_CONFIG = {
    'enabled': True,
    'video_sample_interval_ms': 1500,
    'audio_min_segments': 1,
    'video_min_windows': 2,
    'minimum_confidence_samples': 3,
    'weights': {
        'fluency': 0.3,
        'clarity': 0.25,
        'confidence': 0.25,
        'composure': 0.2,
    }
}


class Settings:
    """应用配置类"""

    def __init__(self, config_path: str = None):
        if config_path is None:
            config_path = Path(__file__).parent / "config.yaml"

        self.config_dir = Path(config_path).parent
        self.config_path = Path(config_path)
        self._config = self._load_config()
        self._apply_env_overrides()
        self._validate_required_secrets()

    def _load_config(self) -> dict:
        """加载主配置文件并合并所有子配置文件"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"配置文件不存在: {self.config_path}")

        # 加载主配置文件
        with open(self.config_path, 'r', encoding='utf-8') as f:
            main_config = yaml.safe_load(f)

        # 获取需要导入的子配置文件列表
        includes = main_config.get('includes', [])

        # 合并所有子配置文件
        merged_config = {}
        for module_name in includes:
            module_config_path = self.config_dir / f"{module_name}.yaml"
            if module_config_path.exists():
                with open(module_config_path, 'r', encoding='utf-8') as f:
                    module_config = yaml.safe_load(f)
                    if module_config:
                        merged_config.update(module_config)
            else:
                raise FileNotFoundError(f"子配置文件不存在: {module_config_path}")

        # 主配置文件的顶级配置优先级更高（如 app 配置）
        for key, value in main_config.items():
            if key != 'includes':
                merged_config[key] = value

        # 递归处理环境变量占位符 ${VAR:default}
        return self._process_env_vars(merged_config)

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

        # 阿里云 ASR 密钥（敏感）
        if alibaba_app_key := os.getenv("ALIBABA_ASR_APP_KEY"):
            if 'asr' not in self._config:
                self._config['asr'] = {}
            self._config['asr']['app_key'] = alibaba_app_key
        if alibaba_token := os.getenv("ALIBABA_ASR_TOKEN"):
            if 'asr' not in self._config:
                self._config['asr'] = {}
            self._config['asr']['token'] = alibaba_token

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

    def reload(self):
        """Reload configuration from disk."""
        self._config = self._load_config()
        self._apply_env_overrides()
        self._validate_required_secrets()

    def save(self):
        """Persist current config to disk."""
        with open(self.config_path, 'w', encoding='utf-8') as f:
            yaml.safe_dump(self._config, f, allow_unicode=True, sort_keys=False)

    def update_section(self, section: str, value: Any):
        self._config[section] = value
        self.save()
        self.reload()

    def get_all(self) -> dict:
        """Return a deep copy of the full effective config."""
        return deepcopy(self._config)

    def replace_all(self, config: dict):
        """Replace the full config and persist to disk."""
        self._config = deepcopy(config)
        self.save()
        self.reload()

    def save_modular_config(self, config: dict) -> None:
        """
        保存模块化配置，将不同部分的配置写入对应的模块文件中

        Args:
            config: 完整的配置字典
        """
        # 定义模块映射关系：配置键 -> 模块文件名
        module_mapping = {
            'database': 'modules/database',
            'ai': 'modules/ai',
            'asr': 'modules/asr',
            'digital_human': 'modules/digital_human',
            'voice': 'modules/voice',
            'expression_analysis': 'modules/expression_analysis',
            'profiles': 'modules/profiles',
            'tools': 'modules/tools',
            'stages': 'modules/stages',
            'base_system_prompt': 'modules/prompts',
            'interviewer_style_prompt': 'modules/prompts',
            'tool_context_template': 'modules/prompts',
            'llm': 'modules/system',
        }

        # 按模块分组配置
        modular_configs = {}
        main_config = {}

        for key, value in config.items():
            if key in module_mapping:
                module_name = module_mapping[key]
                if module_name not in modular_configs:
                    modular_configs[module_name] = {}
                modular_configs[module_name][key] = value
            else:
                # 不属于任何模块的配置放入主配置文件
                main_config[key] = value

        # 确保 includes 字段存在
        main_config['includes'] = [
            'modules/database',
            'modules/ai',
            'modules/asr',
            'modules/digital_human',
            'modules/voice',
            'modules/expression_analysis',
            'modules/profiles',
            'modules/tools',
            'modules/stages',
            'modules/prompts',
            'modules/system',
        ]

        # 保存主配置文件
        with open(self.config_path, 'w', encoding='utf-8') as f:
            yaml.safe_dump(main_config, f, allow_unicode=True, sort_keys=False)

        # 保存各个模块文件
        for module_name, module_config in modular_configs.items():
            module_path = self.config_dir / f"{module_name}.yaml"
            with open(module_path, 'w', encoding='utf-8') as f:
                yaml.safe_dump(module_config, f, allow_unicode=True, sort_keys=False)

        # 重新加载配置
        self.reload()

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
    def asr_fallback_model(self) -> str:
        return self._config.get('asr', {}).get('fallback_model', '')

    @property
    def asr_enabled(self) -> bool:
        return self._config.get('asr', {}).get('enabled', True)

    @property
    def asr_api_secret(self) -> str:
        """阿里云ASR API Secret"""
        return self._config.get('asr', {}).get('api_secret', '')

    @property
    def asr_app_key(self) -> str:
        """阿里云ASR App Key"""
        return self._config.get('asr', {}).get('app_key', '')

    @property
    def asr_token(self) -> str:
        """阿里云ASR Token"""
        return self._config.get('asr', {}).get('token', '')

    @property
    def asr_language(self) -> str:
        """ASR语言设置"""
        return self._config.get('asr', {}).get('language', 'zh-CN')

    @property
    def asr_format(self) -> str:
        """ASR音频格式"""
        return self._config.get('asr', {}).get('format', 'wav')

    @property
    def asr_sample_rate(self) -> int:
        """ASR采样率"""
        return self._config.get('asr', {}).get('sample_rate', 16000)

    @property
    def asr_enable_punctuation(self) -> bool:
        """ASR是否启用标点符号"""
        return self._config.get('asr', {}).get('enable_punctuation', True)

    @property
    def asr_enable_inverse_text_normalization(self) -> bool:
        """ASR是否启用数字规范化"""
        return self._config.get('asr', {}).get('enable_inverse_text_normalization', True)

    @property
    def asr_enable_voice_detection(self) -> bool:
        """ASR是否启用人声检测"""
        return self._config.get('asr', {}).get('enable_voice_detection', True)

    @property
    def cors_origins(self) -> list:
        return self.get('cors.origins', ['*'])

    @property
    def voice_config(self) -> dict:
        config = deepcopy(DEFAULT_VOICE_CONFIG)
        config.update(self._config.get('voice', {}) or {})
        words = config.get('short_noise_words', DEFAULT_VOICE_CONFIG['short_noise_words'])
        config['short_noise_words'] = [str(word).strip() for word in words if str(word).strip()]
        return config

    # 讯飞数字人配置属性
    @property
    def expression_analysis_config(self) -> dict:
        config = deepcopy(DEFAULT_EXPRESSION_ANALYSIS_CONFIG)
        config.update(self._config.get('expression_analysis', {}) or {})
        weights = config.get('weights', {}) or {}
        normalized_weights = deepcopy(DEFAULT_EXPRESSION_ANALYSIS_CONFIG['weights'])
        normalized_weights.update({
            key: float(value)
            for key, value in weights.items()
            if key in normalized_weights
        })
        config['weights'] = normalized_weights
        config['enabled'] = bool(config.get('enabled', True))
        config['video_sample_interval_ms'] = int(config.get('video_sample_interval_ms', 1500))
        config['audio_min_segments'] = int(config.get('audio_min_segments', 1))
        config['video_min_windows'] = int(config.get('video_min_windows', 2))
        config['minimum_confidence_samples'] = int(config.get('minimum_confidence_samples', 3))
        return config

    @property
    def digital_human_provider(self) -> str:
        return self._config.get('digital_human', {}).get('provider', 'disabled')

    @property
    def xunfei_app_id(self) -> str:
        return self._config.get('digital_human', {}).get('xunfei', {}).get('app_id', '')

    @property
    def xunfei_api_key(self) -> str:
        return self._config.get('digital_human', {}).get('xunfei', {}).get('api_key', '')

    @property
    def xunfei_api_secret(self) -> str:
        return self._config.get('digital_human', {}).get('xunfei', {}).get('api_secret', '')

    @property
    def xunfei_scene_id(self) -> str:
        return self._config.get('digital_human', {}).get('xunfei', {}).get('scene_id', 'default')

    @property
    def xunfei_sample_rate(self) -> int:
        return self._config.get('digital_human', {}).get('xunfei', {}).get('sample_rate', 16000)

    @property
    def xunfei_xrtc_url(self) -> str:
        return self._config.get('digital_human', {}).get('xunfei', {}).get('xrtc_url', 'wss://bra.xfyun.cn/rtc-api')

    @property
    def interviewer_profile_presets(self) -> list[dict]:
        presets = self.get('profiles.interviewer_presets', []) or []
        normalized = []
        for preset in presets:
            if not isinstance(preset, dict):
                continue
            plugin_id = str(preset.get('plugin_id', '')).strip()
            if not plugin_id:
                continue
            normalized.append({
                'plugin_id': plugin_id,
                'type': 'interviewer',
                'name': str(preset.get('name', '')).strip(),
                'description': str(preset.get('description', '')).strip(),
                'is_system': True,
                'config': {
                    'prompt': str(preset.get('prompt', '')).strip(),
                    'difficulty': str(preset.get('difficulty', 'standard')).strip() or 'standard',
                    'style_tone': str(preset.get('style_tone', 'balanced')).strip() or 'balanced',
                    'avatar_id': str(
                        preset.get('avatar_id', self.default_interviewer_avatar_id)
                    ).strip(),
                    'vcn': str(
                        preset.get('vcn', self.default_interviewer_vcn)
                    ).strip(),
                    'image_url': str(
                        preset.get(
                            'image_url',
                            preset.get('display_image_url', self.default_interviewer_display_image_url),
                        )
                    ).strip(),
                    'display_image_url': str(preset.get('display_image_url', '')).strip(),
                }
            })
        return normalized

    @property
    def default_interviewer_avatar_id(self) -> str:
        return str(self.get('profiles.default_interviewer_avatar_id', '') or '').strip()

    @property
    def default_interviewer_vcn(self) -> str:
        return str(self.get('profiles.default_interviewer_vcn', 'xiaofeng') or 'xiaofeng').strip()

    @property
    def default_interviewer_display_image_url(self) -> str:
        return str(self.get('profiles.default_interviewer_display_image_url', '') or '').strip()

    @property
    def interviewer_preset_map(self) -> dict[str, dict]:
        return {preset['plugin_id']: preset for preset in self.interviewer_profile_presets}

    @property
    def interviewer_meta_map(self) -> dict[str, dict[str, str]]:
        meta_map = {}
        for preset in self.interviewer_profile_presets:
            config = preset.get('config') or {}
            meta_map[preset['plugin_id']] = {
                'difficulty': config.get('difficulty', 'standard'),
                'style_tone': config.get('style_tone', 'balanced'),
            }
        return meta_map

    def __repr__(self) -> str:
        return f"Settings(config_path={self.config_path})"


# 全局配置实例
settings = Settings()
