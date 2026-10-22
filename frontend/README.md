# Frontend

Next.js 16（App Router）前端：多角色智能问答对话界面。

## 功能

- 登录 / 注册（注册后自动登录），JWT 存储于 localStorage，全局 AuthContext 管理登录态
- 会话侧栏：新建、切换、删除确认，显示消息数与最近时间
- 多角色消息气泡（客服 / 技术支持 / 产品经理 彩色徽章），SSE 流式逐字渲染
- 引用按文件分组，显示引用编号、行号范围与相似度；点击行号或正文中的 `[1]` 可打开带行号、高亮的引用片段预览
- 旧文档未保存完整原文时标注“预览行号”，避免将还原文本的行号误认为原文件行号
- 管理员专属知识库面板：拖拽 / 选择上传 txt / md / docx / xlsx / pdf（≤20MB）、下载、删除
- `proxy.ts` 路由守卫：未登录访问 `/` 重定向到 `/login`
- 全中文 UI，暖色调设计，自适应桌面与移动布局

## Quick start

```cmd
npm install
npm run dev
```

默认访问 `http://localhost:3000`。

## 环境变量

复制 `.env.local.example` 为 `.env.local` 按需修改：

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `BACKEND_BASE_URL` | `http://localhost:8000` | 后端地址（BFF 代理转发目标） |

## 技术栈

- Next.js 16（App Router、Turbopack）
- React 19 + TypeScript 5
- Tailwind CSS v4（PostCSS 插件）
- 中文字体：`Noto Sans SC`（正文）+ `ZCOOL XiaoWei`（标题）

所有对后端的请求经 `app/api/*` Route Handler 代理转发，浏览器不直连后端。

## 验证

运行 `npm test` 检查引用分组、去重、引用编号和行号标注；运行 `npx tsc --noEmit` 检查类型。
