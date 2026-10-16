# RAG 评测报告

- 时间：2026-10-16 16:16:54
- 模式：检索 + LLM 问答
- 模型：`qwen3.7-flash-2026-07-15` / 嵌入 `text-embedding-v3`
- 检索参数：top_k=5, min_similarity=0.2
- 语料：FastAPI 中文文档 10 章（MIT），评测后默认清理
- 总耗时：740s

## 汇总指标

| 指标 | 定义 | 结果 |
| --- | --- | --- |
| 检索命中率 Hit@5 | 期望文档出现在召回结果（可答题） | 100.0% |
| 关键词覆盖率 | 期望关键词出现在召回内容（可答题） | 96.9% |
| 引用准确率 | 回答引用含期望文档（可答题） | 100.0% |
| 拒答正确率 | 无证据题给出拒答 | 100.0% |
| 澄清率 | 模糊题给出澄清追问 | 0.0% |
| 综合通过率 | 各题型按判定标准全部通过 | 90.0% |

## 逐题明细

| ID | 类型 | 问题 | 命中 | 关键词 | 引用 | 拒答 | 澄清 | 通过 | 回答摘录 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| q001 | answerable | 启动 FastAPI 开发服务器的命令是什么？ | ✓ | ✓ | ✓ | ✗ | ✗ | ✓ | 根据知识库，启动 FastAPI 开发服务器的标准命令是： ```bash uv |
| q002 | answerable | FastAPI 自动生成的交互式 API 文档由哪个工具提供 | ✓ | ✓ | ✓ | ✗ | ✗ | ✓ | 根据知识库内容，FastAPI 自动生成的交互式 API 文档是由 **Swag |
| q003 | answerable | FastAPI 除了 Swagger UI 之外还提供另一套 | ✓ | ✓ | ✓ | ✗ | ✗ | ✓ | FastAPI 提供的另一套可选 API 文档名为 **ReDoc**。  你可 |
| q004 | answerable | 通过 FastAPI 能使用 Starlette 的所有功能 | ✓ | ✓ | ✓ | ✗ | ✗ | ✓ | 是的，可以通过 FastAPI 使用 Starlette 的所有功能。这是因为  |
| q005 | answerable | 把路径参数声明为 int 类型后，访问 /items/foo | ✓ | ✓ | ✓ | ✗ | ✗ | ✓ | 根据知识库内容，当路径参数被声明为 `int` 类型后，访问 `/items/f |
| q006 | answerable | FastAPI 的所有数据校验都由哪个库在幕后完成？ | ✓ | ✗ | ✓ | ✗ | ✗ | ✗ | 根据提供的知识库片段，**未找到**关于 FastAPI 数据校验底层具体由哪个 |
| q007 | answerable | 同时需要 /users/me 和 /users/{user_ | ✓ | ✓ | ✓ | ✗ | ✗ | ✓ | 在 FastAPI 中，当同时需要 `/users/me` 和 `/users/ |
| q008 | answerable | 怎么限制一个路径参数只能取预设的几个固定值？ | ✓ | ✓ | ✓ | ✗ | ✗ | ✓ | 根据知识库内容，你可以通过使用 Python 标准库中的 `Enum`（枚举）来 |
| q009 | answerable | 如果路径参数本身也要包含一段路径（比如 /files/hom | ✓ | ✓ | ✓ | ✗ | ✗ | ✓ | 在 FastAPI 中，若要让路径参数本身包含完整的路径片段（如 `home/j |
| q010 | answerable | 查询参数在 URL 中位于什么位置、键值对之间用什么分隔？ | ✓ | ✓ | ✓ | ✗ | ✗ | ✓ | 根据知识库内容，查询参数（查询字符串）位于 URL 的 `?` 符号之后，其中的 |
| q011 | answerable | 怎么把一个查询参数声明为可选参数？ | ✓ | ✓ | ✓ | ✗ | ✓ | ✓ | 在 FastAPI 中，将查询参数声明为可选非常直接：**只需在路径操作函数的参 |
| q012 | answerable | bool 类型的查询参数，哪些写法会被自动转换成 True？ | ✓ | ✓ | ✓ | ✗ | ✓ | ✓ | 根据知识库内容，当 FastAPI 的路径操作函数中声明了 `bool` 类型的 |
| q013 | answerable | FastAPI 从哪个版本开始支持用 Pydantic 模型 | ✓ | ✓ | ✓ | ✗ | ✗ | ✓ | 根据知识库内容，FastAPI 从 `0.115.0` 版本开始支持使用 Pyd |
| q014 | answerable | 怎么禁止客户端发送额外的查询参数并让其收到错误？ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | 根据知识库提供的信息，你可以通过 **Pydantic 模型的配置**来实现该需 |
| q015 | answerable | 声明请求体应该使用什么方式？ | ✓ | ✓ | ✓ | ✗ | ✗ | ✓ | 根据知识库内容，声明请求体推荐使用 **Pydantic 的 `BaseMode |
| q016 | answerable | FastAPI 是按什么规则区分函数参数是路径参数、查询参数 | ✓ | ✓ | ✓ | ✗ | ✗ | ✓ | 根据知识库内容，FastAPI 主要依据**参数是否在路径中声明**以及**参数 |
| q017 | answerable | 客户端向 API 发送数据应该使用哪些 HTTP 方法？用  | ✓ | ✓ | ✓ | ✗ | ✗ | ✓ | 根据知识库内容，回答如下：  **推荐使用的 HTTP 方法** 客户端向 AP |
| q018 | answerable | 声明 header 参数必须使用什么？如果不用会发生什么？ | ✓ | ✓ | ✓ | ✗ | ✗ | ✓ | 根据知识库内容：  * **必须使用**：`Header`（FastAPI 提供 |
| q019 | answerable | Header 参数名中的下划线默认会被自动转换成什么字符？ | ✓ | ✓ | ✓ | ✗ | ✗ | ✓ | 根据知识库内容，Header 参数名中的下划线（`_`）默认会被自动转换成**连 |
| q020 | answerable | 如何禁用 Header 参数下划线的自动转换？启用时有什么风 | ✓ | ✓ | ✓ | ✗ | ✗ | ✓ | 根据知识库内容，回答如下：  * **如何禁用**：在声明 `Header` 参 |
| q021 | answerable | 要向 API 客户端返回 HTTP 错误响应，应该使用什么？ | ✓ | ✓ | ✓ | ✗ | ✗ | ✓ | 要向 API 客户端返回 HTTP 错误响应，应该使用 **`HTTPExcep |
| q022 | answerable | HTTPException 的 detail 参数可以传递哪 | ✓ | ✓ | ✓ | ✗ | ✗ | ✓ | 根据知识库内容，`HTTPException` 的 `detail` 参数可以传 |
| q023 | answerable | 怎么为自己的自定义异常安装全局的异常处理器？ | ✓ | ✓ | ✓ | ✗ | ✗ | ✓ | 在 FastAPI 中，为自定义异常安装全局异常处理器的标准方法是使用 `@ap |
| q024 | answerable | 想覆盖请求校验错误的默认响应行为，应该处理哪个异常类？ | ✓ | ✓ | ✓ | ✗ | ✗ | ✓ | 要覆盖请求校验错误的默认响应行为，你应该处理 **`RequestValidat |
| q025 | answerable | 注册 HTTPException 的异常处理器时应该注册哪一 | ✓ | ✓ | ✓ | ✗ | ✗ | ✓ | 根据知识库内容，注册异常处理器时，**应该注册到 Starlette 的 `HT |
| q026 | answerable | OAuth2 的 Password 流程配合 Bearer  | ✓ | ✓ | ✓ | ✗ | ✗ | ✓ | FastAPI 提供了 `OAuth2PasswordBearer` 类来实现  |
| q027 | answerable | 为什么在 FastAPI 中使用 OAuth2 需要安装 p | ✓ | ✓ | ✓ | ✗ | ✗ | ✓ | 根据知识库说明，在 FastAPI 中使用 OAuth2 需要安装 `pytho |
| q028 | answerable | OAuth2PasswordBearer 在请求缺少 Aut | ✓ | ✓ | ✓ | ✗ | ✗ | ✓ | 当请求缺少 `Authorization` 请求头时，`OAuth2Passwo |
| q029 | answerable | 应用挂在会移除路径前缀的代理后面时，应该怎么配置？ | ✓ | ✓ | ✓ | ✗ | ✗ | ✓ | 根据知识库内容，当应用部署在会“移除路径前缀”的代理（如 Traefik、Ngi |
| q030 | answerable | 繁重的后台计算任务不建议用 BackgroundTasks  | ✓ | ✓ | ✓ | ✗ | ✗ | ✓ | 根据知识库内容，当需要执行**繁重的后台计算任务**且不一定需要由同一进程运行时 |
| q031 | answerable | 在同一个请求中同时接收表单数据和上传文件，应该怎么声明参数？ | ✓ | ✓ | ✓ | ✗ | ✗ | ✓ | 根据知识库内容，在同一个请求中同时接收表单数据和上传文件的声明方法及限制如下：  |
| q032 | answerable | 接收文件上传或表单数据之前，需要先安装什么包？ | ✓ | ✓ | ✓ | ✗ | ✗ | ✓ | 在接收文件上传或表单数据之前，需要先安装 **`python-multipart |
| q033 | no_evidence | FastAPI 应该怎么配置数据库连接池的最大连接数？ | - | - | - | ✓ | ✗ | ✓ | 根据提供的知识库检索片段，其中并未包含关于 FastAPI 配置数据库连接池最大 |
| q034 | no_evidence | FastAPI 商业版的企业授权费用是多少钱一年？ | - | - | - | ✓ | ✗ | ✓ | 根据提供的知识库内容，**未找到关于 FastAPI 商业版或企业授权费用的相关 |
| q035 | no_evidence | 如何将 FastAPI 应用打包成 Docker 镜像并推送 | - | - | - | ✓ | ✗ | ✓ | 根据提供的知识库片段，其中**并未包含**将 FastAPI 应用打包为 Doc |
| q036 | no_evidence | FastAPI 与 Django ORM 集成的推荐步骤是什 | - | - | - | ✓ | ✗ | ✓ | 根据您提供的知识库检索片段，其中**并未包含**关于“FastAPI 与 Dja |
| q037 | no_evidence | 怎么为 FastAPI 的 WebSocket 端点实现心跳 | - | - | - | ✓ | ✗ | ✓ | 根据您提供的知识库检索片段，**其中并未包含关于 FastAPI WebSock |
| q038 | no_evidence | FastAPI 官方目前列出的赞助商公司有哪些？ | - | - | - | ✓ | ✗ | ✓ | 根据提供的知识库内容，仅提及了 **FastAPI Cloud** 是 *Fas |
| q039 | ambiguous | FastAPI 里的参数怎么用？ | - | - | - | ✗ | ✗ | ✗ | 根据提供的知识库，FastAPI 主要通过 **Python 类型声明** 和  |
| q040 | ambiguous | 用 FastAPI 写个东西要注意什么？ | - | - | - | ✗ | ✗ | ✗ | 根据提供的知识库内容，使用 FastAPI 进行开发时需注意以下核心事项。这些要 |

> 判定标准：answerable = 检索命中 + 关键词覆盖 + 引用期望文档 + 未拒答（严格拒答标记）；
> no_evidence = 回答命中拒答标记（宽松）；ambiguous = 回答包含澄清追问（或拒答）。
> 完整回答与引用明细见 `eval/details.jsonl`。