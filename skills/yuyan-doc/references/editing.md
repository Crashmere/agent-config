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
node "$YUYAN_DOC" validate --input "$work_dir/article.md" --format markdown --out "$work_dir/article.json"
node "$YUYAN_DOC" create --book 1 --parent 10 --title '部署指南' --input "$work_dir/article.json" --out "$work_dir/created.json"
node "$YUYAN_DOC" create --book 1 --title '资料分组' --kind group
node "$YUYAN_DOC" create --book 1 --title '新周记' --template TEMPLATE_ID
```

`create` 可直接接受 `--input article.md --format markdown`；不传 input 时建立空文档。分组只有标题，不接受正文。`validate` 只本地解析，不访问服务。Markdown 中的图片必须先上传并引用 `/assets/...`；`[[名称]]` 必须先解析成真实文档链接。转换器报告降级时拒绝写入，改用原生 JSON。

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
node "$YUYAN_DOC" edit --snapshot "$work_dir/before.json" --patch "$work_dir/patch.json" --dry-run
node "$YUYAN_DOC" edit --snapshot "$work_dir/before.json" --patch "$work_dir/patch.json" --out "$work_dir/after.json"
```

重复执行旧快照会报冲突；基于最新 after.json 开始下一轮。未改变内容的补丁不会写入或增加 revision。图片是行内节点，普通正文中放入 paragraph；表格、代码、附件、分栏则是块节点。所有容器需保持最小合法结构，例如折叠块始终包含标题与正文，即使标题为空。

脚本在创建/编辑前检查所有图片和附件 URL 可访问；修改使用 `baseRevision` 和 `sessionRevision` 保护原文，保存后回读并请求结果快照。写入成功但后续失败会返回回执。若只是补记快照失败，核对当前正文后可调用 `api --method POST --path docs/42/snapshot`，无需再次提交正文。历史列表可以确认 before-edit 和结果快照。

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

`schema --node tableCell` 等命令从当前 checkout 读取属性与默认值；`validate` 检查 Tiptap 父子结构、未知属性和常见属性值，不会执行任意 HTML、代码或公式。结构合法不证明表格跨度、图表语义或排版符合用户意图。复杂内容还应查看阅读页；修改一处后可比对快照，确认其他节点保持。

所有写入都经过服务端最终校验，遇到不兼容或媒体已回收时报告原因。不得为了通过检查删掉未理解的属性或把复杂容器转成纯文本。
