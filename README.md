# AI面试系统

一个基于AI的智能技术面试系统，支持前端Vue3和后端Python Flask实现。

## 功能特性

- AI智能对话：基于大语言模型的自然对话面试体验
- 自动评估：多维度自动评估候选人能力，生成详细报告
- 定制化面试：支持不同职位、技能领域和经验级别的面试配置
- 实时对话：流畅的实时面试对话界面
- 历史记录：完整的面试历史记录和消息回溯

## 技术栈

### 前端
- Vue 3
- Vite
- Element Plus
- Pinia（状态管理）
- Vue Router
- Axios

### 后端
- Python 3.10+
- Flask
- PostgreSQL
- OpenAI API（兼容接口）

## 项目结构

```
interview-service/
├── backend/                    # 后端服务（独立Python项目）
│   ├── app/
│   │   ├── api/               # API路由
│   │   ├── services/          # 业务逻辑
│   │   ├── models/            # 数据模型
│   │   ├── db/                # 数据库操作
│   │   └── __init__.py        # 应用初始化
│   ├── config/                # 配置文件
│   │   ├── config.yaml        # 主配置
│   │   └── settings.py        # 配置管理类
│   ├── prompts/               # Prompt模板
│   │   └── system_prompts.yaml
│   ├── logs/                  # 日志目录
│   ├── main.py               # 入口文件
│   ├── pyproject.toml        # Python依赖配置
│   ├── .env.example          # 环境变量示例
│   └── venv/                 # Python虚拟环境
│
├── frontend/                   # 前端服务（独立Node项目）
│   ├── src/
│   │   ├── views/             # 页面组件
│   │   ├── api/               # API调用
│   │   ├── stores/            # 状态管理
│   │   ├── router/            # 路由配置
│   │   └── styles/            # 样式文件
│   ├── index.html
│   ├── package.json           # npm依赖配置
│   └── vite.config.js         # Vite配置
│
├── scripts/                    # 启动脚本
│   ├── start-db.bat/sh        # 启动数据库
│   ├── stop-db.bat/sh         # 停止数据库
│   └── start-all.bat/sh       # 一键启动所有服务
│
├── docker-compose.yml          # PostgreSQL数据库服务
├── .gitignore
└── README.md
```

## 快速开始

### 前置要求

- Python 3.10+
- Node.js 18+
- Docker & Docker Compose
- AI API Key（OpenAI或兼容服务）

### 步骤一：配置

#### 后端配置

1. 复制环境变量模板

   **Windows:**

   ```cmd
   copy backend\.env.example backend\.env
   ```

   **Linux/Mac:**

   ```bash
   cp backend/.env.example backend/.env
   ```

2. 严格分层约定

   - `.env` 仅填写敏感信息（密钥/密码）
   - `config.yaml` 仅填写普通信息（地址、模型、端口、CORS、日志等）

3. 编辑 `backend/.env`（仅敏感项）

   - `AI_API_KEY`：必填
   - `DB_PASSWORD`：必填
   - `ASR_API_KEY`：可选，不填时默认复用 `AI_API_KEY`

4. 检查 `backend/config/config.yaml`（普通项）

   - `database.host/name/user` 在此配置
   - `ai.base_url/model` 在此配置
   - `asr.base_url/model` 在此配置
   - LLM 运行参数（如 `temperature`、`max_tokens`）由数据库 `prompt_configs.llm` 管理

#### 前端配置

当前版本前端无必填环境变量，默认可直接启动。

若后续新增前端环境变量，请以 `frontend/.env.*` 文件为准。

### 步骤二：启动

**Windows:**
```cmd
./scripts/start-all.bat
```

**Linux/Mac:**
```bash
./scripts/start-all.sh
```

这会自动：
1. 通过容器启动PostgreSQL数据库
2. 创建Python虚拟环境并安装依赖
3. 启动后端服务
4. 安装前端依赖并启动开发服务器

## 使用流程

1. **创建面试**
   - 访问首页，点击"创建面试"
   - 填写候选人信息、职位、技能等
   - 提交创建

2. **开始面试**
   - 在面试列表中找到创建的面试
   - 点击"查看"进入详情页
   - 点击"开始面试"

3. **进行对话**
   - AI会先做自我介绍并提问
   - 候选人通过输入框回答问题
   - AI会根据回答继续提问

4. **完成评估**
   - 面试结束后点击"完成面试"
   - 系统自动生成多维度评估报告
   - 查看评分、优势和改进建议
