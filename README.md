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

### 方式一：一键启动（推荐）

**Windows:**
```cmd
scripts\start-all.bat
```

**Linux/Mac:**
```bash
./scripts/start-all.sh
```

这会自动：
1. 启动PostgreSQL数据库
2. 创建Python虚拟环境并安装依赖
3. 启动后端服务（端口8000）
4. 安装前端依赖并启动开发服务器（端口5173）

### 方式二：分步启动

#### 1. 启动数据库

```bash
# Windows
scripts\start-db.bat

# Linux/Mac
./scripts/start-db.sh
```

或手动启动：
```bash
docker-compose up -d
```

#### 2. 启动后端

```bash
cd backend

# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate

# 安装依赖
pip install -e .

# 配置环境变量
copy .env.example .env
# 编辑 .env 文件，填入 AI_API_KEY 等配置

# 启动服务
python main.py
```

后端服务将在 http://localhost:8000 启动

#### 3. 启动前端

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

前端应用将在 http://localhost:5173 启动

## 配置说明

### 环境变量 (backend/.env)

```env
# AI服务配置
AI_API_KEY=your-api-key-here
AI_BASE_URL=https://api.openai.com/v1
AI_MODEL=gpt-4o-mini

# 数据库配置
DB_HOST=localhost
DB_NAME=interview_db
DB_USER=postgres
DB_PASSWORD=postgres
```

### AI模型配置

系统支持任何兼容OpenAI API的服务。通过配置 `AI_MODEL` 环境变量即可切换模型：

**常用模型推荐：**

| 服务商 | 模型名称 | 说明 |
|--------|---------|------|
| OpenAI | `gpt-4o-mini` | 快速且性价比高 |
| OpenAI | `gpt-4o` | 最新的GPT-4 Omni |
| SiliconFlow | `Qwen/Qwen2.5-7B-Instruct` | 通义千问7B（免费/低成本） |
| SiliconFlow | `Qwen/Qwen2.5-72B-Instruct` | 通义千问72B（更强） |
| SiliconFlow | `deepseek-ai/DeepSeek-V3` | DeepSeek V3 |
| SiliconFlow | `deepseek-ai/DeepSeek-R1` | DeepSeek推理模型 |

**示例配置：**

```env
# 使用OpenAI
AI_API_KEY=sk-xxx
AI_BASE_URL=https://api.openai.com/v1
AI_MODEL=gpt-4o-mini

# 使用SiliconFlow
AI_API_KEY=sk-xxx
AI_BASE_URL=https://api.siliconflow.cn/v1
AI_MODEL=Qwen/Qwen2.5-72B-Instruct

# 使用其他兼容服务
AI_API_KEY=your-key
AI_BASE_URL=https://your-api-endpoint.com/v1
AI_MODEL=your-model-name
```

### 后端配置文件 (backend/config/config.yaml)

配置文件包含默认设置，环境变量会覆盖这些值：

```yaml
app:
  name: "interview-service"
  port: 8000

database:
  host: "localhost"
  port: 5432
  name: "interview_db"
  user: "postgres"
  password: "postgres"

ai:
  provider: "openai"
  api_key: "${AI_API_KEY}"
  base_url: "${AI_BASE_URL:https://api.openai.com/v1}"
  model: "Qwen/Qwen2.5-7B-Instruct"  # 可被AI_MODEL环境变量覆盖
  temperature: 0.7
  max_tokens: 2000
```

## API文档

### 面试管理

- `POST /api/interviews` - 创建面试
- `GET /api/interviews` - 获取面试列表
- `GET /api/interviews/:id` - 获取面试详情
- `DELETE /api/interviews/:id` - 删除面试

### 面试操作

- `POST /api/interviews/:id/start` - 开始面试
- `POST /api/interviews/:id/chat` - 发送消息
- `POST /api/interviews/:id/complete` - 完成面试并生成评估
- `GET /api/interviews/:id/evaluation` - 获取评估结果

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

## Prompt定制

系统支持通过修改 `backend/prompts/system_prompts.yaml` 来定制面试行为：

- `interviewer.system`：面试官系统提示词
- `evaluator.system`：评估系统提示词
- `skill_domains`：不同技能领域的特定提示

## 常用命令

### 数据库管理

```bash
# 启动数据库
scripts\start-db.bat

# 停止数据库
scripts\stop-db.bat

# 查看日志
docker-compose logs postgres

# 重启数据库
docker-compose restart
```

### 开发命令

```bash
# 后端开发
cd backend
python main.py

# 前端开发
cd frontend
npm run dev

# 构建前端生产版本
cd frontend
npm run build
```

## License

MIT
