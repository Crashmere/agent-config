# API 与知识库操作

`api --path` 使用相对 `/api/` 的路径。默认 GET；JSON body 从 `--input file.json` 读取，支持 `-` stdin。命令只允许下表已知接口；创建和修改正文必须走 create/edit，不用泛用 API 绕过格式与冲突检查。查询值按 URL 编码，不把凭据写进 URL。

## 查找与关系

| GET path | 用途 |
|---|---|
| books / books/ID | 知识库列表 / 详情 |
| books/ID/tree | 有序文档树，节点有 id、kind、title、children；kind 区分 doc/group |
| book-groups | 首页知识库分组及 revision |
| recent / titles | 最近文档 / 文档标题索引 |
| search?q=关键词 | 服务端全文匹配，最多 50 项；并非无限分页搜索 |
| link-targets | 存活文档与 H1–H6 章节，含实际 slug；不包含回收站 |
| docs/ID/preview?heading=slug | 文档/章节摘要 |
| docs/ID/backlinks | 反向链接及来源上下文 |
| docs/ID/view | 阅读 HTML、目录、邻接文档和图片尺寸 |
| templates / templates/ID | 模板/片段列表 / 完整内容与预览 |
| docs/ID/versions / versions/ID | 历史列表 / 某个历史的原生内容 |
| versions/ID/view | 历史阅读 HTML 与元信息 |
| trash | 回收站 |
| attachments/CONTENT_ID/preview?name=文件名 | 素材预览类型、有限文本或压缩包目录 |

标题拼音从服务端返回，可用于筛选结果；不要引入另一份拼音词典。查找同名文档时同时查看知识库和父目录，选择后返回真实链接。

## 目录与知识库

| 方法与 path | body |
|---|---|
| POST books | name、description |
| PATCH books/ID | 仅发送需要修改的 name / description 字段 |
| PUT books/order | ids，完整知识库顺序 |
| PUT book-groups | baseRevision、groups: [{id,name,bookIds}]；先读取当前配置并保留其他分组 |
| POST docs/ID/move | bookId、parentId（根用 null）、index（目标位置） |
| POST docs/batch | bookId、ids、action: copy / move / trash；copy/move 另带 targetBookId、parentId |

batch 一次最多 5000 项，选父项时必须包含其全部存活后代；先读树展开选择。服务端校验并在一个事务内完成，目录变化时 409 后重新读取。copy 会复制所选结构、重写复制范围内文档链接并共享原素材。移动禁止放进自己的子树。成功后读取目标树确认位置及数量。

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

泛用 API 写入返回服务响应，随后按任务读取树、列表、文档或历史核验。`--dry-run` 返回请求计划且不写入。网络失败不可自动重试 copy/create 等非幂等操作，先核对是否已成功。

## 运行与维护边界

本技能不提供数据库迁移、直接 SQL、生产 GC、部署、修改门户鉴权或备份恢复接口。相关任务交给 server-operations 和项目文档。新增 API 时先核对实际路由及契约，再更新本参考和脚本允许列表；不要从网页按钮名称猜接口。
