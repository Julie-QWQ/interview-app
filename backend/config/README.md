# 配置文件结构说明

本目录包含按功能模块拆分的配置文件，提高了可维护性和可读性。

## 目录结构

```
config/
├── config.yaml              # 主配置文件
├── config.yaml.backup       # 原始配置文件备份
├── settings.py              # 配置加载类
└── modules/                 # 功能模块配置目录
    ├── database.yaml        # 数据库连接配置
    ├── ai.yaml              # AI 服务配置（包含 LLM 和 ASR）
    ├── digital_human.yaml   # 数字人服务配置
    ├── voice.yaml           # 语音处理配置
    ├── expression_analysis.yaml  # 表情分析配置
    ├── profiles.yaml        # 面试官配置
    ├── tools.yaml           # 工具和智能回复配置
    ├── stages.yaml          # 面试阶段配置
    ├── prompts.yaml         # 提示词模板配置
    └── system.yaml          # 系统配置（CORS、日志等）
```

## 配置文件列表

### 主配置文件
- **config.yaml** - 主配置文件，包含应用基本信息和导入映射

### 功能模块配置文件（存放在 modules/ 目录）
- **modules/database.yaml** - 数据库连接配置
- **modules/ai.yaml** - AI 服务配置（包含 LLM 和 ASR）
- **modules/digital_human.yaml** - 数字人服务配置
- **modules/voice.yaml** - 语音处理配置
- **modules/expression_analysis.yaml** - 表情分析配置
- **modules/profiles.yaml** - 面试官配置
- **modules/tools.yaml** - 工具和智能回复配置
- **modules/stages.yaml** - 面试阶段配置
- **modules/prompts.yaml** - 提示词模板配置
- **modules/system.yaml** - 系统配置（CORS、日志等）

## 配置加载机制

1. 主配置文件 `config.yaml` 定义了应用基本信息
2. 通过 `includes` 字段指定需要导入的子配置文件路径（相对于 config 目录）
3. 系统自动按顺序加载所有子配置文件并合并
4. 主配置文件的顶级配置优先级更高

## 目录组织优势

- **清晰分层**: 主配置文件和子模块配置文件分离，层次清晰
- **易于维护**: 每个功能模块独立配置，修改时互不影响
- **便于扩展**: 添加新配置模块只需在 modules/ 目录创建新文件

## 环境变量

敏感信息通过环境变量注入，支持 `${VAR:default}` 格式：
- `AI_API_KEY` - AI 服务密钥
- `DB_PASSWORD` - 数据库密码
- `ASR_API_KEY` - ASR 服务密钥（可选）
- `XUNFEI_APP_ID` - 讯飞应用 ID
- `XUNFEI_API_KEY` - 讯飞 API 密钥
- `XUNFEI_API_SECRET` - 讯飞 API 密钥
- `XUNFEI_SCENE_ID` - 讯飞场景 ID

## 备份文件

- **config.yaml.backup** - 原始配置文件备份

## 使用说明

### 修改配置

1. 找到对应的功能模块配置文件
2. 修改相应的配置项
3. 保存文件，系统会在下次启动时自动加载

### 添加新模块

1. 在 `config/modules/` 目录下创建新的 YAML 文件
2. 在 `config.yaml` 的 `includes` 列表中添加相对路径（如 `modules/新模块名`）
3. 重启应用以加载新配置

### 向后兼容

所有现有的配置访问方式保持不变，无需修改业务代码。
