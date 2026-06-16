# 多角色智能问答 Agent 系统

一个面向中文场景的多角色协作 AI 对话系统：用户注册登录后提出问题，由调度器自动决定哪些角色（客服 / 技术支持 / 产品经理）参与回答，技术支持角色还会基于知识库做 RAG 检索增强，所有对话按用户归属保存在 PostgreSQL 中支持多轮上下文。对话支持 SSE 流式输出，前端实时逐字显示回复。

项目分为 `backend`（FastAPI）与 `frontend`（Next.js）两部分。

---

## 一、技术架构

### 整体架构

```
用户浏览器
   │
   ▼
Next.js 前端 (App Router, React 19, Tailwind v4)
   │  /api/chat/stream、/api/conversations、/api/auth/...
   ▼
Next.js API Route 代理层 (_proxy.ts)
   │  转发至 BACKEND_BASE_URL
   ▼
FastAPI 后端
   ├─ JWT 鉴权中间件（Bearer Token）
   ├─ Auth 路由（注册 / 登录 / 当前用户）
   ├─ Orchestrator（角色调度器）
   │     └─ 通义千问做意图分类，决定参与角色
   ├─ 客服 Agent (CustomerServiceAgent)
   ├─ 技术支持 Agent (TechnicalSupportAgent)  ──► RAG 检索 (pgvector)
   └─ 产品经理 Agent (ProductManagerAgent)
   │
   ├─ PostgreSQL  (用户 / 会话 / 消息 持久化)
   └─ pgvector    (文档分片向量检索)
```

### 后端技术栈

- 语言：Python 3.11+
- Web 框架：FastAPI + Uvicorn
- LLM 框架：LangChain（`langchain-community.ChatTongyi` 与 `langchain-openai.ChatOpenAI` 兼容模式）
- LLM：阿里云通义千问 DashScope（聊天模型 `qwen3.6-plus`，向量模型 `text-embedding-v3`）
- 数据库：PostgreSQL + pgvector 扩展
- ORM：SQLAlchemy 2.x（async）+ asyncpg
- 鉴权：python-jose（JWT）+ passlib（bcrypt 密码哈希）
- 配置：python-dotenv + dataclass Settings

### 前端技术栈

- Next.js 16（App Router）
- React 19 + TypeScript 5
- Tailwind CSS v4（PostCSS 插件）
- 中文字体：`Noto Sans SC`（正文）+ `ZCOOL XiaoWei`（标题）
- API 层：Route Handlers 转发到后端，避免浏览器跨域
- 认证：JWT 存储于 localStorage，全局 AuthContext 管理登录态

### 数据模型

- `users`：用户表（id、username、email、hashed_password、created_at）
- `conversations`：会话主表（id、user_id FK -> users、title、data JSONB、created_at）
- `messages`：消息明细（role、content、sources JSONB）
- `documents`：知识库文档元信息
- `chunks`：文档切片 + `vector` 向量（pgvector）

---

## 二、已实现功能

### 用户认证

- `POST /api/auth/register` 注册（username + email + password，bcrypt 哈希）
- `POST /api/auth/login` 登录，返回 JWT Token（默认 24 小时过期）
- `GET /api/auth/me` 获取当前用户信息
- 所有对话、聊天、知识库灌入接口均需携带 `Authorization: Bearer <token>`
- 会话按 `user_id` 归属，用户只能访问自己的会话

### 多角色协作

- `Orchestrator` 调用通义千问做角色分类，使用中文 Router Prompt 精确匹配场景：
  - 使用 / 操作类 -> 客服
  - 错误 / 排查类 -> 技术支持
  - 产品策略类 -> 产品经理
  - 跨领域问题可组合多角色
  - 模糊 / 闲聊 -> 降级到客服
- 解析失败或为空时降级到客服角色
- 命中的角色按顺序串行生成回复，统一聚合返回

### 角色定义（system prompt）

- 客服：清晰礼貌，聚焦使用引导与流程
- 技术支持：基于检索到的知识库片段给出可执行的排查步骤
- 产品经理：结构化的产品分析、权衡与下一步建议

### RAG 检索增强

- `/api/ingest` 接收文档列表，按 `CHUNK_SIZE` / `CHUNK_OVERLAP` 切片
- 调用 DashScope 文本向量模型生成 embedding 并写入 pgvector
- 技术支持 Agent 在每次回答前用 cosine 距离召回 Top-K（默认 5），低于 `RAG_MIN_SIMILARITY`（默认 0.2）的片段会被过滤
- 引用信息（document_id、chunk_id、source、score）随回复返回，前端可展开查看

### SSE 流式输出

- `POST /api/chat/stream` 返回 `text/event-stream`，逐 token 推送
- 事件类型：`start`（含 conversation_id）-> 每角色 `role_start` / `token` / `citations` / `role_end` -> `done`
- 前端实时渲染流式光标与逐字显示，各角色独立流式消息
- 流式结束后消息持久化到数据库

### 会话与历史

- 自动创建会话，首条消息自动截取前 32 字作为标题
- 每次对话仅取最近 10 条历史拼接到 LLM 上下文
- `GET /api/conversations` 列出当前用户的会话（含消息数、最后消息时间）
- `GET /api/conversations/{id}` 拉取完整消息历史
- `DELETE /api/conversations/{id}` 删除会话（级联删除消息）
- 启动时自动 `CREATE EXTENSION IF NOT EXISTS vector` 并 `create_all` 建表，兼容旧库自动补建 `user_id` 列

### 前端界面

- 登录 / 注册页面，表单校验，注册后自动登录
- 左侧会话列表（新建、切换、删除确认、显示消息数与最近时间、当前用户名与退出按钮）
- 右侧对话区，按角色显示彩色徽章（客服绿、技术支持黄、产品经理蓝）
- SSE 流式消息实时渲染，含打字光标动画
- 引用来源可折叠展开，显示来源文件名与相似度百分比
- 输入框支持 Enter 发送、Shift+Enter 换行
- 全中文 UI，暖色调设计，自适应桌面与移动布局

---

## 三、目录结构

```
act01/
├─ backend/
│  ├─ app/
│  │  ├─ main.py                FastAPI 入口，启动时初始化数据库 + CORS
│  │  ├─ config.py              环境变量与默认值（含 JWT 配置）
│  │  ├─ db.py                  async engine / session / init_db
│  │  ├─ models.py              SQLAlchemy 模型（users / conversations / messages / documents / chunks）
│  │  ├─ schemas.py             Pydantic 请求 / 响应模型
│  │  ├─ auth.py                JWT 生成与验证、密码哈希、get_current_user 依赖
│  │  ├─ orchestrator.py        角色调度器（含流式 run_orchestrator_stream）
│  │  ├─ agents/                三个角色 Agent 实现（含 respond_stream）
│  │  ├─ rag/
│  │  │  ├─ ingest.py           文档切片 + embedding 入库
│  │  │  └─ retriever.py        向量检索 Top-K
│  │  ├─ llm/qwen.py            DashScope / ChatTongyi 客户端封装（含 chat_stream）
│  │  ├─ utils/chunking.py      简单的滑动窗口切片
│  │  └─ api/
│  │     ├─ routes.py           /health /chat /chat/stream /ingest /conversations
│  │     └─ auth_routes.py      /auth/register /auth/login /auth/me
│  ├─ requirements.txt
│  └─ .env.example
└─ frontend/
   ├─ app/
   │  ├─ layout.tsx             根布局 + 中文字体
   │  ├─ providers.tsx          全局 Provider（AuthProvider）
   │  ├─ page.tsx               主对话界面（含 SSE 流式渲染）
   │  ├─ login/page.tsx         登录页
   │  ├─ register/page.tsx      注册页
   │  ├─ contexts/
   │  │  └─ AuthContext.tsx      认证状态管理
   │  ├─ lib/
   │  │  ├─ api.ts              authFetch 封装（自动携带 Token、401 跳转）
   │  │  └─ auth.ts             Token / User 的 localStorage 操作
   │  └─ api/
   │     ├─ _proxy.ts           通用代理实现
   │     ├─ chat/route.ts       同步聊天代理
   │     ├─ chat/stream/route.ts  SSE 流式聊天代理
   │     ├─ auth/login/route.ts
   │     ├─ auth/register/route.ts
   │     ├─ auth/me/route.ts
   │     └─ conversations/...
   ├─ package.json
   └─ next.config.ts
```

---

## 四、环境准备

### 1. PostgreSQL + pgvector

需要一个开启了 `vector` 扩展的 PostgreSQL 实例，默认连接：

```
postgresql+asyncpg://postgres:123456@192.168.10.174:5432/agentdb
```

可在 `backend/.env` 中通过 `DATABASE_URL` 覆盖。后端启动时会自动执行 `CREATE EXTENSION IF NOT EXISTS vector` 和建表，无需手动迁移。

### 2. 通义千问 API Key

在阿里云 DashScope 控制台申请 API Key，并写入 `backend/.env` 的 `DASHSCOPE_API_KEY`。如使用兼容模式端点，再设置 `DASHSCOPE_HTTP_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1`。

### 3. JWT 密钥（可选）

生产环境建议在 `.env` 中设置 `JWT_SECRET_KEY` 为随机强密码，默认值 `change-me-in-production` 仅适用于开发。

### 4. Node.js

前端基于 Next.js 16，建议 Node.js 20+。

---

## 五、启动方式

### 后端

```cmd
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
:: 编辑 .env，填入 DASHSCOPE_API_KEY、DATABASE_URL，可选设置 JWT_SECRET_KEY
uvicorn app.main:app --reload
```

服务启动后监听 `http://localhost:8000`，OpenAPI 文档位于 `http://localhost:8000/docs`。

### 前端

```cmd
cd frontend
npm install
npm run dev
```

默认访问 `http://localhost:3000`。前端通过 `BACKEND_BASE_URL` 环境变量指向后端，未设置时使用 `http://localhost:8000`。

---

## 六、使用流程

### 1. 注册与登录

打开前端首页，首次使用需先注册账号（用户名 + 邮箱 + 密码），注册成功后自动登录。已有账号可直接登录。

### 2. （可选）灌入知识库

技术支持角色会基于知识库回答，建议先调用 `/api/ingest` 灌入文档（需携带 JWT Token）：

```cmd
curl -X POST http://localhost:8000/api/ingest ^
  -H "Content-Type: application/json" ^
  -H "Authorization: Bearer <your-token>" ^
  -d "{\"documents\":[{\"title\":\"产品手册\",\"source\":\"manual.md\",\"text\":\"......\"}]}"
```

返回 `{ "documents": 1, "chunks": N }` 表示入库成功。

### 3. 发起对话

登录后在输入框提问，回复将以 SSE 流式推送，逐字实时显示，例如：

- "这个产品怎么注册？"（客服会响应）
- "登录时报 502 错误怎么排查？"（技术支持会响应并附引用）
- "我们应该优先做哪个功能？"（产品经理会响应）

调度器会自动决定参与角色，可能多个角色同时回复。每条 AI 消息下方若有引用，会显示"引用来源"按钮，可展开查看文档片段与相似度。

### 4. 管理会话

左侧会话列表展示所有历史会话，点击即可加载完整消息记录，支持继续追问并自动衔接上下文。悬停会话项可显示删除按钮，确认后删除整个会话。

---

## 七、主要 HTTP 接口

### 认证

| 方法 | 路径 | 鉴权 | 说明 |
| --- | --- | --- | --- |
| POST | `/api/auth/register` | 无 | 用户注册 |
| POST | `/api/auth/login` | 无 | 用户登录，返回 JWT |
| GET | `/api/auth/me` | JWT | 获取当前用户信息 |

### 业务

| 方法 | 路径 | 鉴权 | 说明 |
| --- | --- | --- | --- |
| GET | `/api/health` | 无 | 健康检查 |
| POST | `/api/chat` | JWT | 发送消息，返回多角色回复（一次性 JSON） |
| POST | `/api/chat/stream` | JWT | 发送消息，SSE 流式返回多角色回复 |
| GET | `/api/conversations` | JWT | 当前用户的会话列表（支持 `limit`、`offset`） |
| GET | `/api/conversations/{id}` | JWT | 单个会话的完整消息 |
| DELETE | `/api/conversations/{id}` | JWT | 删除会话（级联删除消息） |
| POST | `/api/ingest` | JWT | 批量灌入知识库文档 |

`/api/chat/stream` SSE 事件序列：

```
event: start       data: {"conversation_id": "uuid"}
event: role_start  data: {"role": "technical_support"}
event: token       data: {"content": "建议"}
event: token       data: {"content": "先确认"}
...
event: citations   data: [{"document_id": "uuid", "chunk_id": "uuid", "source": "manual.md", "score": 0.83}]
event: role_end    data: {"role": "technical_support"}
event: done        data: {}
```

---

## 八、可配置项（backend/.env）

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `DATABASE_URL` | `postgresql+asyncpg://postgres:123456@192.168.10.174:5432/agentdb` | 数据库连接串 |
| `DASHSCOPE_API_KEY` | 空 | 通义千问 API Key |
| `DASHSCOPE_HTTP_BASE_URL` | 空 | 兼容模式端点（设置后走 OpenAI 兼容协议） |
| `QWEN_MODEL` | `qwen3.6-plus` | 聊天模型 |
| `QWEN_EMBEDDING_MODEL` | `text-embedding-v3` | 向量模型 |
| `RAG_TOP_K` | `5` | 向量召回数量 |
| `RAG_MIN_SIMILARITY` | `0.2` | 相似度阈值 |
| `CHUNK_SIZE` | `800` | 文档切片大小（字符） |
| `CHUNK_OVERLAP` | `100` | 切片重叠 |
| `JWT_SECRET_KEY` | `change-me-in-production` | JWT 签名密钥（生产环境务必修改） |
| `JWT_ALGORITHM` | `HS256` | JWT 签名算法 |
| `JWT_EXPIRE_MINUTES` | `1440` | JWT 过期时间（分钟，默认 24 小时） |
| `LOG_LEVEL` | `INFO` | 日志级别 |
| `DB_ECHO` | `false` | 是否打印 SQL |

前端可通过环境变量 `BACKEND_BASE_URL` 指向非默认的后端地址。

---

## 九、当前限制

- 角色调度依赖 LLM 的输出格式，极端情况下会回退到客服单角色
- 历史上下文窗口固定为最近 10 条，未做 token 级裁剪
- 角色间无交互式协作（如客服追问技术支持的结论），各角色独立生成回复
