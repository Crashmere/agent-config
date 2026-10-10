# API 与知识库操作

`api --path` 使用相对 `/api/` 的路径。默认 GET；JSON body 从 `--input file.json` 读取，支持 `-` stdin。命令只允许下表已知接口；创建和修改正文必须走 create/edit，不用泛用 API 绕过格式与冲突检查。查询值按 URL 编码，不把凭据写进 URL。

## 查找与关系

| GET path | 用途 |
|---|---|
| books / books/ID | 知识库列表 / 详情 |
| books/ID/tree | 有序文档树，节点有 id、kind、title、children；kind 区分 doc/group |
| book-groups | 首页知识库分组及 revision |
| recent / titles | 最近文档 / 文档标题索引 |
| stats | 全站及各知识库正文总字数，返回 `{chars: number, bookChars: {[bookId: string]: number}}`，与首页及各卡片右下角一致 |
| search?q=关键词 | 服务端全文匹配，最多 50 项；并非无限分页搜索 |
| link-targets | 存活文档与 H1–H6 章节，含实际 slug；不包含回收站 |
| docs/ID/preview?heading=slug | 文档/章节摘要 |
| docs/ID/backlinks | 反向链接及来源上下文 |
| docs/ID/view | 阅读 HTML、目录、邻接文档和图片尺寸 |
| templates / templates/ID | 模板/片段列表 / 完整内容与预览 |
| docs/ID/versions / versions/ID | 历史列表 / 某个历史的原生内容 |
| versions/ID/view | 历史阅读 HTML 与元信息 |
| drawings/CONTENT_ID | 受支持的不可变画板包、场景、预览与派生文字 |
| trash | 回收站 |
| attachments/CONTENT_ID/preview?name=文件名 | 素材预览类型、有限文本或压缩包目录 |

标题拼音从服务端返回，可用于筛选结果；不要引入另一份拼音词典。查找同名文档时同时查看知识库和父目录，选择后返回真实链接。

查询全站及各知识库的字数用 `node "$YUYAN_DOC" api --path stats`：`chars` 为全站总数，`bookChars` 按知识库 ID 的字符串索引，每个存活知识库都有一项，空知识库为 0；例如 ID 为 12 的知识库读取 `bookChars["12"]`。统计与阅读页及目录一致：非空白 Unicode 字符逐个计数，只统计当前存活正文，不含文档标题、目录分组、回收站文档/知识库、历史或模板；无知识库时返回 `{chars: 0, bookChars: {}}`。

## 目录与知识库

| 方法与 path | body |
|---|---|
| POST books | name、description，可选 groupId；创建与归入指定分组在一个事务保存 |
| PATCH books/ID | 仅发送需要修改的 name / description 字段 |
| PUT books/order | ids，完整知识库顺序 |
| PUT book-groups | baseRevision、groups: [{id,name,bookIds}]，可选 bookOrder（全部存活知识库 ID 的顺序）；分组与顺序在一个事务保存 |
| POST docs/ID/move | bookId、parentId（根用 null）、index（目标位置） |
| POST docs/ID/dissolve | 目录分组当前的 bookId、parentId（根用 null）、childIds（当前存活直接子项的完整有序 ID 列表，空分组为 []）；使用 --confirm |
| POST docs/batch | bookId、ids、action: copy / move / trash；copy/move 另带 targetBookId、parentId |

batch 一次最多 5000 项，选父项时必须包含其全部存活后代；先读树展开选择。服务端校验并在一个事务内完成，目录变化时 409 后重新读取。copy 会复制所选结构、重写复制范围内文档链接并共享原素材。移动禁止放进自己的子树。成功后读取目标树确认位置及数量。

在指定分组新建知识库时，先读 `book-groups` 取得目标 ID，再 POST `books`，例如 body 为 `{"name":"新知识库","description":"","groupId":"目标分组ID"}`。创建与追加归属在同一事务完成，新知识库位于该组末尾；无需再发一次移组请求。省略 `groupId` 或传空字符串时创建到“未分组”。非空目标不存在返回 404 且不创建记录，先刷新分组再根据用户意图处理，不静默改到未分组。该接口只向最新配置追加新 ID，保留既有归属与顺序，不需要 baseRevision；归组成功递增 revision，旧 revision 的完整分组写入仍会冲突。成功后合并读取一次 `books` 与 `book-groups` 核对新 ID、归属和末尾位置；失败时先确认是否已创建，不自动重试非幂等请求。网页分组菜单的“新建知识库”使用同一操作；在首页创建后停留原处，保留滚动与分组折叠状态。

移动知识库并指定组内位置时，先读取 `books` 和 `book-groups`。保留其他分组及回收站知识库的既有归属，只将目标 ID 从原组的 `bookIds` 移到新组；移至“未分组”则从各组移除。`bookIds` 只决定归属，实际显示顺序由 `books` 返回的全局顺序决定，不能只调整 `bookIds` 数组。

从全部存活知识库的有序 ID 列表中取出待移动 ID，插到目标卡片之前或之后（放到组末尾时插在该组最后一个存活 ID 之后），将完整列表作为 `bookOrder` 与更新后的 `groups`、原 `baseRevision` 一起 PUT。例如全局顺序为 `[1,2,3,4]`，将知识库 1 移入包含 2、3 的组并放在两者之间，发送 `bookOrder: [2,1,3,4]`，同时保留知识库 4 的归属。空目标组只有新移入的一项，无须改变它在全局列表的位置。

`bookOrder` 必须恰好包含所有存活知识库，包括其他组和未分组，不含回收站；遗漏、重复、未知或已删除 ID 返回 400，旧 revision 返回 409，归属和顺序均不部分保存。省略 `bookOrder` 保持既有顺序，旧调用仍兼容。失败后重新读取并根据用户意图重建请求，不换新 revision 强行提交旧快照；成功后读取一次 `books` 与 `book-groups` 核对归属、组内顺序及其他组保持情况。网页拖放会立即预览落点，失败时恢复已确认状态。

解散目录分组时，先从 `books/ID/tree` 定位 `kind=group` 的节点，将其 `parentId` 与 `children` 的直接子项 ID 顺序原样发送到 `docs/分组ID/dissolve`。这会在一个事务内用子项替换分组原来的位置，子分组及文档的内部层级、正文、ID、revision 和历史保留；仅空分组进入回收站。已在回收站的直接子项也上移父级但保持删除状态，恢复或彻底删除空分组不会带走已移出的内容。该操作不写正文，不需要正文 baseRevision；目标不是分组或缺少 childIds 返回 400，所在知识库、父级、子项及其顺序不符返回 409，分组或知识库已删除返回 404。失败后重新读取目录并重选，不拆成多次移动再删除。用户明确要求解散后带 `--confirm` 执行，也可先 `--dry-run` 预览；成功后读取一次相关知识库树核对替换位置和所有子项。

从其他知识库移入文档时，目标是指定知识库的根目录，沿用 `POST docs/batch`，body 为 `bookId: 来源知识库ID`、`ids: 所选节点及全部存活后代ID`、`action: "move"`、`targetBookId: 目标知识库ID`、`parentId: null`。每次选择一个来源知识库，允许选择其不同目录中的文档；根项按来源目录顺序追加到目标末尾，文档 ID、正文、历史、内部链接和子树保留。网页首页知识库卡片的“从其他知识库移入”提供分栏选择器，支持勾选、Command/Ctrl 多选和 Shift 连选；API 不需要经过网页选择器。成功后读取来源与目标树各一次核对，409 后重新选择，非幂等移动失败先核对结果再处理。

## 模板与片段

```sh
node "$YUYAN_DOC" api --path templates
node "$YUYAN_DOC" api --method POST --path templates --input "$work_dir/template.json"
node "$YUYAN_DOC" create --book 1 --title '新笔记' --template TEMPLATE_ID
```

创建 body：`{"name":"模板名","kind":"document","content":{"type":"doc","content":[...]}}`。kind 为 document 或 snippet；名称最多 100 个字符。从现有文档/选区保存时保留完整 JSON 和真实素材引用，片段也要形成合法 doc 根（补齐表格、分栏、Callout 等必要外层），不能截取无法闭合的节点序列。

模板插入已有文档：GET templates/ID 后，将其 content.content 通过 edit 的 splice 插到合适容器。模板是独立快照，删除或修改来源不影响它。

PATCH templates/ID 只支持重命名：name、baseRevision。DELETE 同样要求 baseRevision 和 --confirm。服务尚无原地修改模板正文接口；用户要求变更模板内容时可新建修订模板，确认替代范围后再删除旧模板，不伪造 PATCH 正文功能。

## 历史与删除

- 改正文使用 edit，它会同事务保存编辑前内容，并在完成后补记结果快照；历史保留 30 天，不保底保留一条。GET versions 返回的历史 ID 不等同于文档 revision。
- POST versions/VERSION_ID/restore，body 为当前文档的 baseRevision；使用 --confirm。先查看该历史正文和当前版本，明确恢复目标。服务同事务保留恢复前快照。恢复后重新读取文档和历史确认。
- POST docs/ID/snapshot 手动补记当前正文，用于完成阶段失败后的修复；不能把它当作数据库备份。
- DELETE docs/ID、DELETE books/ID 是移入回收站；POST 相应的 /restore 恢复。知识库/目录操作会影响其内容，先核对树。
- DELETE trash/docs/ID、DELETE trash/books/ID 是彻底删除；DELETE trash 清空回收站。此类动作没有历史撤销保障，必须有明确用户授权，工具要求 --confirm。
- 回收站恢复与历史恢复都要求 --confirm；用户已明确请求具体操作时无需重复询问。模糊的“清理一下”不等于同意清空全部数据。

泛用 API 写入返回服务响应，随后按任务读取一次必要的树、列表、文档或历史核验，确认受影响对象后结束；批量操作合并核对，不逐篇重复获取全文和历史。create/edit 已在脚本中回读比对，不因使用了 API 参考就再检查一遍。`--dry-run` 返回请求计划且不写入。网络失败不可自动重试 copy/create 等非幂等操作，先核对是否已成功。

## 画板与客户端兼容

`api/meta` 的 features 包含 drawing-v1 表示支持画板。新 CLI 自动携带 `X-Yuyan-Features: drawing-v1`；含画板的当前文档保存和取消编辑拒绝旧客户端，revision 检查仍适用。

包发布走 `upload --kind drawing`，不通过泛用 API 写入。它调用 POST /api/drawings，返回完整 drawing 节点；包限 12 MiB，依赖图片必须已存在且类型匹配。GET drawings/ID 读取包；媒体下载路径不含 /api，使用 download 的 `/drawings/ID/file` 或 `/drawings/ID/preview`。未知版本不能编辑，允许保留原文件和服务端校验通过的静态预览。详见 [可编辑画板](drawing.md)。

## 运行与维护边界

本技能不提供数据库迁移、直接 SQL、生产 GC、部署、修改门户鉴权或备份恢复接口。相关任务交给 server-operations 和项目文档。新增 API 时先核对实际路由及契约，再更新本参考和脚本允许列表；不要从网页按钮名称猜接口。
