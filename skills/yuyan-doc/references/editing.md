# 读写流程与局部修改

使用入口中定义的 `YUYAN_DOC`，下面以 `work_dir` 表示本次独占临时目录；示例 ID 需替换为实际查询结果。`--server`/`YUYAN_SERVER` 选择的实例必须在整个任务中保持一致。

## 读取与定位

```sh
work_dir=$(mktemp -d "${TMPDIR:-/tmp}/yuyan-doc.XXXXXX")
node "$YUYAN_DOC" api --path books
node "$YUYAN_DOC" api --path 'search?q=部署'
node "$YUYAN_DOC" read --doc 42 --scope outline --out "$work_dir/before.json"
node "$YUYAN_DOC" read --doc 42 --scope section --path 3
node "$YUYAN_DOC" read --doc 42 --scope keyword --keyword 超时
node "$YUYAN_DOC" read --doc 42 --scope node --path 3/0
```

- `full` 默认返回完整原生 JSON；`outline` 返回所有标题及路径；`keyword` 做不区分大小写的字面匹配，最多 30 个命中并标明截断。
- `node` 的 path 是从根开始的 `content` 数组下标，例如 `3/0` = `doc.content[3].content[0]`；根路径是空字符串。返回节点 hash 可作补丁额外的 `expect`。
- `section` 只接受顶层标题路径，包含该标题直到下一个同级/更高级标题之前。容器内标题用 `node` 读取包容容器，不能假设它在顶层。
- `--out` 始终写完整快照，无论屏幕输出什么范围；每份输出用新路径。阅读结果带 revision，制作补丁时确认与快照相同。
- `--format markdown` 只用于全文阅读，复杂格式可能包含 HTML；不要删掉转义或把这份阅读输出当成无损编辑快照。

## 新建

先查询知识库与父目录；未指定放置位置时从当前任务上下文推断，存在多个合理位置才澄清。标题是独立字段，不必再把它重复写成正文 H1。

```sh
node "$YUYAN_DOC" create --book 1 --parent 10 --title '部署指南' --input "$work_dir/article.md" --format markdown --out "$work_dir/created.json"
node "$YUYAN_DOC" create --book 1 --title '资料分组' --kind group
node "$YUYAN_DOC" create --book 1 --title '新周记' --template TEMPLATE_ID
```

`create` 内置转换和格式校验；不传 input 时建立空文档。分组只有标题，不接受正文。需要提前查看转换后的 JSON 或排查格式错误时才单独运行 `validate --input article.md --format markdown --out article.json`，它只本地解析、不访问服务，不是每次创建的前置步骤。Markdown 中的图片必须先上传并引用 `/assets/...`；`[[名称]]` 必须先解析成真实文档链接。转换器报告降级时拒绝写入，改用原生 JSON。

## 补丁格式

将 JSON 保存成单独补丁文件。`operations` 依次作用于前一步结果，因此插入/删除后后续下标也要调整；适合从后向前修改不同位置。所有操作最终通过一次带 revision 的正文保存提交。

```json
{
  "operations": [
    {"op":"text","path":"1/0","text":"修改后的文字"},
    {"op":"attrs","path":"2","attrs":{"textAlign":"center"}},
    {"op":"splice","path":"","index":4,"deleteCount":0,"nodes":[
      {"type":"paragraph","content":[{"type":"text","text":"新增段落"}]}
    ]}
  ]
}
```

| 操作 | 字段 | 语义 |
|---|---|---|
| `text` | path、text | 替换一个 text 节点的完整非空文本，保留其 marks；空文本用父节点 splice 删除 |
| `attrs` | path、attrs | 合并节点属性；恢复默认可将相应属性设为 null，但需遵守该属性定义 |
| `replace` | path、node | 替换单个完整节点；改文字 marks 用此操作并保留其他标记；根路径替换是整篇重写，须明确符合用户目标 |
| `splice` | path、index、deleteCount、nodes | 在目标容器 content 中插入、删除或替换连续子节点；nodes 可为空数组 |

可在任意操作加 `expect`（读取返回的节点 hash），在执行该操作前核对目标。改标题在顶层加 `"title":"新标题"`，仍需 `operations:[]`。不要使用原始 PATCH 重命名来绕过本文的 revision 保护。

```sh
# 批量改写、整篇替换或结构重组时，先预演核对；普通文字修改可直接 edit。
node "$YUYAN_DOC" edit --snapshot "$work_dir/before.json" --patch "$work_dir/patch.json" --dry-run
node "$YUYAN_DOC" edit --snapshot "$work_dir/before.json" --patch "$work_dir/patch.json" --out "$work_dir/after.json"
```

重复执行旧快照会报冲突；基于最新 after.json 开始下一轮。未改变内容的补丁不会写入或增加 revision。图片是行内节点，普通正文中放入 paragraph；表格、代码、附件、分栏则是块节点。所有容器需保持最小合法结构，例如折叠块始终包含标题与正文，即使标题为空。

脚本在创建/编辑前检查所有图片和附件 URL 可访问；修改使用 `baseRevision` 和 `sessionRevision` 保护原文，保存后回读比对标题与完整正文，并请求结果快照。成功返回 `verified:true`，这些检查不需要 agent 另发一轮请求重复完成。写入成功但后续失败会返回回执。若只是补记快照失败，核对当前正文后可调用 `api --method POST --path docs/42/snapshot`，无需再次提交正文；只有排查快照失败或用户要求查历史时，才额外读取历史列表。

## 核验与结束条件

| 情况 | 必要检查与结束条件 |
| --- | --- |
| 普通新建、改字、润色、代码或已有表格内容修改 | 提交前审阅内容与用户要求；create/edit 返回 `ok:true, verified:true` 即交付，不额外读取正文、历史或打开阅读页 |
| 用户要求完整导入、指定字数、批量重组或跨文档链接 | 在输入和 `--out` 快照上一次核对对应的完整性、数量、顺序或链接目标；目录变化额外读取一次受影响的树；没有新问题即结束 |
| 本次新增/改变必须实际渲染判断的布局，或用户明确要求排版验收 | 优先使用 [本地预览](preview.md) 和保存后的快照，只检查受影响章节与必要视口，修复后只复查受影响部分；线上访问行为用真实页面检查 |
| 报错、409、writeReceipt、未确认的写入结果或发现实际缺陷 | 按错误和具体问题重新读取、修复并核验；不能用停止规则掩盖未完成事项 |

`--out` 快照来自脚本已回读的完整结果；额外内容检查优先读它，不再从服务下载同一份正文。单纯为了“再确认一下”而重复 GET、逐图下载算哈希、打开所有链接、导出重导入、查看版本列表或运行项目 roundtrip，都不属于普通文档交付步骤。用户明确要求素材逐字节一致或完整迁移时，按该要求做一次针对性核验。

视觉核验可发现 JSON 一致性不能证明的布局问题，但应有明确目标，例如导入图片的窄屏比例或刚修改的合并表格。`preview` 不连接远端正文、不写生产，复用本地素材并按需读取缺失图片；附件只检查卡片。它的 `checksPassed` 只说明机器检查未发现渲染错误，仍需查看本次关注的截图。可选检查失败最多一次有依据的修正/重试；之后说明未核验视觉效果并交付已保存内容，不转去搭建代理、安装浏览器或调试项目运行环境。用户明确要求的视觉验收或已发现的排版缺陷尚未解决时，必须明确报告，不能称为完全验收通过。

## 素材与导出

```sh
node "$YUYAN_DOC" upload --input ./diagram.png --kind image
node "$YUYAN_DOC" upload --input ./report.pdf --kind attachment --timeout 0
node "$YUYAN_DOC" download --src /attachments/CONTENT_ID --out "$work_dir/report.pdf" --timeout 0
node "$YUYAN_DOC" export --doc 42 --out "$work_dir/export"
```

upload 返回素材元信息与可插入的原生 node；图片可加 caption、shadow、crop、placement 等属性，见格式参考。工具按文件流上传；图片上限 25 MiB，附件没有工具大小上限。附件重命名只改当前节点 name，不改存储对象。没有“下载并执行附件”的工作流。

export 导出当前单篇 Markdown/HTML、原生 JSON 和实际引用文件，包括仅以文字链接引用的本服务媒体；本地文件路径替换 Markdown 中的媒体链接，外部链接保持原样且不下载。文档链接保留为可打开的网页链接。输出目录必须不存在；失败时目录可能只包含部分文件，不能当作完整导出，使用新目录重试。导出不包含子文档、历史、模板库或数据库；需要全库导出/一致性备份时使用 Yuyan 已有项目工具与 server-operations。

## 格式核验

`schema --node tableCell` 等命令从当前 checkout 读取属性与默认值；`validate` 检查 Tiptap 父子结构、未知属性和常见属性值，不会执行任意 HTML、代码或公式。结构合法不证明表格跨度、图表语义或排版符合用户意图。根据[核验与结束条件](#核验与结束条件)检查本次受影响的内容，不能仅因文档已有复杂块就扩大到整篇排版验收。

所有写入都经过服务端最终校验，遇到不兼容或媒体已回收时报告原因。不得为了通过检查删掉未理解的属性或把复杂容器转成纯文本。
