# AI Interview System

基于 Vue 3 + FastAPI + PostgreSQL 的 AI 面试系统，支持面试会话管理、流式对话、语音识别、TTS，以及讯飞数字人接入。

## Stack

前端：
- Vue 3
- Vite
- Element Plus
- Pinia

后端：
- Python 3.10+
- FastAPI
- PostgreSQL
- OpenAI 兼容接口

## Current Runtime

- 后端正式入口：FastAPI / ASGI
- 本地开发启动：`uvicorn main:app --reload`
- 前端开发服务器默认地址：`http://localhost:5173`
- 后端默认地址：`http://localhost:8000`
- 前端默认 API 基础地址：`http://127.0.0.1:8000/api`

## Repository Layout

```text
interview-service/
├─ backend/
│  ├─ app/
│  │  ├─ api/
│  │  ├─ db/
│  │  ├─ models/
│  │  └─ services/
│  ├─ config/
│  ├─ migrations/
│  ├─ prompts/
│  ├─ scripts/
│  ├─ .env.example
│  ├─ main.py
│  └─ pyproject.toml
├─ frontend/
│  ├─ src/
│  ├─ .env.development
│  └─ package.json
├─ scripts/
│  ├─ start-all.bat
│  ├─ start-all.sh
│  ├─ start-db.bat
│  └─ start-db.sh
├─ docker-compose.yml
└─ README.md
```

## Prerequisites

- Python 3.10+
- Node.js 18+
- Docker Desktop 或可用的 Docker Engine
- `uv`
- npm

如果你要启用数字人或 ASR，还需要对应供应商的有效配置。

## Quick Start

### 1. Configure backend

后端配置分两层：

- `backend/.env`
  - 放密钥、密码、供应商凭证等敏感信息
- `backend/config/config.yaml`
  - 放非敏感运行配置，例如服务端口、数据库主机名、日志、语音、数字人、ASR 和业务默认参数

两者缺一不可：`.env` 负责 secrets，`config.yaml` 负责主配置结构。

#### 1.1 Configure `backend/.env`

复制环境变量模板：

Windows:
```cmd
copy backend\.env.example backend\.env
```

macOS / Linux:
```bash
cp backend/.env.example backend/.env
```

至少需要填写：

- `AI_API_KEY`
- `DB_PASSWORD`

可选配置（ASR 服务选择一个）：

- `SILICONFLOW_API_KEY` - SiliconFlow ASR（免费，当前默认）
- `ALIBABA_ASR_API_KEY` / `ALIBABA_ASR_API_SECRET` / `ALIBABA_ASR_APP_KEY` - 阿里云（推荐，准确率高）
- `XUNFEI_ASR_API_KEY` / `XUNFEI_ASR_API_SECRET` / `XUNFEI_ASR_APP_ID` - 讯飞（中文最佳）
- `WHISPER_API_KEY` - Whisper API（多语言）
- `AZURE_SPEECH_KEY` - Azure Speech

数字人配置：

- `XUNFEI_APP_ID`
- `XUNFEI_API_KEY`
- `XUNFEI_API_SECRET`
- `XUNFEI_SCENE_ID`

说明：

- 如果直接使用仓库内 `docker-compose.yml` 启动数据库，默认 PostgreSQL 密码是 `postgres`，那么 `backend/.env` 里的 `DB_PASSWORD` 也应保持一致。
- 讯飞数字人签名依赖本机时间，系统时间不准会导致 WebSocket 握手失败。

#### 1.2 Review `backend/config/config.yaml`

首次启动前建议至少检查这些配置项是否符合你的本地环境：

- `app`
  - 服务名、调试模式、监听地址和端口
- `database`
  - 主机、端口、数据库名、用户名
  - 其中密码通常从 `.env` 的 `DB_PASSWORD` 注入
- `ai`
  - 模型名、Base URL、超时、流式行为
- `asr`
  - **重要**: 选择 ASR 服务提供商（当前默认 SiliconFlow）
  - 切换到阿里云: 将 `<<: *siliconflow_asr` 改为 `<<: *alibaba_asr`
  - 切换到讯飞: 将 `<<: *siliconflow_asr` 改为 `<<: *xunfei_asr`
  - 详见: [ASR 配置指南](docs/asr_quick_setup.md)
- `digital_human`
  - 采样率、默认数字人参数
- `voice`
  - TTS 音色、分段播报相关配置
- `logging`
  - 日志级别和格式

如果你改了数据库主机、后端端口、AI/ASR 提供商地址，优先检查这里，而不是只改 `.env`。

### 2. Configure frontend env

检查 [frontend/.env.development](/c:/Users/22318/Desktop/fwwb-contest/project/offer-master-easy-version/interview-service/frontend/.env.development)：

```env
VITE_API_BASE_URL=http://127.0.0.1:8000/api
```

如果你修改了后端端口或反向代理地址，这里也要同步调整。

### 3. Start everything

Windows:
```cmd
scripts\start-all.bat
```

macOS / Linux:
```bash
./scripts/start-all.sh
```

启动脚本会自动执行：

1. 启动 PostgreSQL 容器
2. 创建后端虚拟环境并安装依赖
3. 执行数据库 schema bootstrap
4. 启动 FastAPI 服务
5. 安装前端依赖并启动 Vite

启动完成后访问：

- 前端：`http://localhost:5173`
- 后端：`http://localhost:8000`
- FastAPI health check：`http://localhost:8000/health`
- FastAPI OpenAPI：`http://localhost:8000/docs`

## Manual Start

### Backend

```bash
cd backend
uv venv
uv sync --frozen
uv run python scripts/migration_manager.py migrate
uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Database only

```bash
docker compose up -d
```

## Database Bootstrap

项目支持从空 PostgreSQL 实例自动初始化：

- schema 基线文件：`backend/migrations/001_full_schema.sql`
- migration 管理脚本：`backend/scripts/migration_manager.py`

常用命令：

```bash
cd backend
uv run python scripts/migration_manager.py migrate
uv run python scripts/migration_manager.py status
```

## Prompt Templates

- 主模板：`backend/prompts/interviewer_system_prompt.j2`
- 变量说明：`backend/prompts/VARIABLES.md`

后端会在运行时按上下文动态渲染 prompt。

## Tool Orchestration Docs

工具编排相关说明见：

- `backend/docs/tool-orchestration.md`

## Digital Human Notes

当前讯飞数字人接入方式是：

- 后端下发会话配置
- 前端通过 SDK 直接建立数字人连接

注意事项：

- 本机时间必须准确，否则签名会失败
- 浏览器自动播放策略会影响首帧音频播放
- 当前实现已对首个用户手势做音频解锁处理，但首次进入页面后仍建议通过真实点击触发面试开始流程

## Common Problems

### 1. `Missing required secret environment variables`

原因：
- `backend/.env` 缺失
- 或脚本运行时没有正确读取 `.env`

检查：
- `backend/.env` 是否存在
- `AI_API_KEY` 和 `DB_PASSWORD` 是否已填写

### 2. `Database is not initialized`

通常表示：
- 后端启动初始化未完成
- 或数据库没有成功 bootstrap

处理：
- 先执行 `uv run python scripts/migration_manager.py migrate`
- 再重启后端

### 3. 讯飞数字人 WebSocket 握手失败

优先检查：
- 系统时间是否准确
- `XUNFEI_*` 配置是否匹配
- `XUNFEI_SCENE_ID` 是否属于该账号

### 4. 浏览器报 `play() failed because the user didn't interact with the document first`

这是浏览器自动播放策略，不是后端错误。通常刷新页面并通过真实点击触发“开始面试”即可。

## Tests

后端示例测试：

```bash
cd backend
uv run pytest -q
```

前端类型检查：

```bash
cd frontend
npm run type-check
```

## Security

不要把真实的：

- `AI_API_KEY`
- `ASR_API_KEY`
- `XUNFEI_API_SECRET`

提交到仓库。生产环境也不应该把供应商密钥明文暴露到浏览器端。
