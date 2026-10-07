# 原生文档格式

目录：基础结构与文字、代码与公式、容器、表格、图片与组合、附件、链接、兼容边界。

本文说明当前格式与常用写法，实际节点/属性以 `schema [--node TYPE]` 从 Yuyan checkout 读取的结果为准。格式源为 Yuyan 的 `web/src/schema`；修改本技能不得复制或维护另一套 schema。写入用 `validate` / `create` / `edit`，不要从 DOM HTML 反推原文。

## 基础结构与文字

文档根是 `doc`，content 至少有一个块；空文档为 `{"type":"doc","content":[{"type":"paragraph"}]}`。节点使用 `type / attrs / content / text / marks`。`text` 节点的 text 非空，不带 content。

| 节点 | 内容 / 属性 |
|---|---|
| paragraph | 行内内容；textAlign: null / left / center / right |
| heading | 行内内容；level: 1–6；没有段落对齐属性 |
| hardBreak | 行内换行，无内容 |
| horizontalRule | 分隔线，块级 |
| blockquote | 一个或多个块 |
| bulletList / orderedList | 一个或多个 listItem；有序列表 start 默认 1，type 通常保留默认 null |
| listItem | 必须以 paragraph 开始，其后可有块、嵌套列表 |
| taskList / taskItem | taskList 内是 taskItem，内容同列表项；taskItem.checked 布尔值 |

文字标记：`bold`、`italic`、`strike`、`underline`、`code`；`highlight` 默认无色值，对应 `==高亮==`。标记存于 text.marks，不应写成节点。

原生 text 中的 `**文字**` 仍是字面正文，不会由阅读页再次解释为加粗。Markdown 导入会诊断未解析的加粗，修正边界空白、闭合或乘号歧义后再保存，见 [Markdown 加粗检查](editing.md#markdown-加粗检查)；不要靠全局删星号模拟 marks。

```json
{"type":"paragraph","content":[
  {"type":"text","text":"重要内容","marks":[{"type":"bold"},{"type":"highlight"}]},
  {"type":"text","text":"链接","marks":[{"type":"link","attrs":{"href":"/docs/42"}}]}
]}
```

文字颜色用 `textColor` 标记，attrs 为 color 与可选 gradient；文字背景用 `highlight.color`。纯色推荐 #rrggbb；不支持任意 CSS、透明背景或自定义渐变。固定文字渐变：ocean、violet、sunset、flame，配套纯色回退从 `schema` 返回的 textGradients 读取。例如 ocean 的 color 为 `#14b8a6`。同类标记只出现一次；修改颜色时保留链接、粗体等其他 marks。

普通文字强调可写为 `{"type":"text","text":"性能损耗","marks":[{"type":"textColor","attrs":{"color":"#d63384"}}]}`。迁移源用行内代码模拟颜色时，确认是普通文字后移除 `code`，不能只叠加颜色；真正代码保留 `code`，混合句子拆成多个 text，见 [语义迁移](editing.md#资料迁移的语义与截图处理)。

## 代码、Mermaid 与公式

`codeBlock` 只包含无格式 text；代码放 text，保留换行和空格，不解析其中的 Markdown。attrs：language、title、titleHidden、collapsed。title 为 null 表示无标题条，空字符串表示空标题条；需要收起时提供可见标题条。

```json
{"type":"codeBlock","attrs":{"language":"go","title":"示例","collapsed":false,"titleHidden":false},"content":[{"type":"text","text":"fmt.Println(\"hello\")\n"}]}
```

Mermaid 使用 `codeBlock` 且 language 为 `mermaid`，不是单独节点。Markdown 代码围栏支持 `go title="示例" collapsed`；标题/收起会保留。代码字体配色、查找、放大、编辑快捷键属于网页行为，不存成正文属性。

公式使用 `inlineMath`（在 paragraph 内）或 `blockMath`，表达式放 attrs.latex，无 content。JSON 中反斜线需转义，例如 `{"type":"blockMath","attrs":{"latex":"E=mc^2"}}`。不要把公式当可执行程序。

## Callout、折叠、高亮块与分栏

- `callout`：content 必须依次为 calloutTitle、calloutContent；前者是行内内容，后者至少一个块。attrs.type 常用 note、info、tip、warning、danger、success、question、example、quote；fold 为 `""`（不可折叠）、`"+"`（展开）、`"-"`（收起）。代码使用 codeBlock，不再新建旧 `[!code]` 样式。
- `foldBlock`：content 依次为 foldTitle、foldContent；标题行内，正文至少一个块；attrs.collapsed 为布尔值。
- `highlightBlock`：至少一个块；backgroundColor 使用固定色板。用 `schema` 查询十种浅色值，不使用任意色值；默认蓝色 `#e1efff`。
- `columns`：2–4 个 column；每个 column 至少一个块。attrs.widths 是与栏数一致的正整数比例权重，每项 1–1000，null 表示等宽。例如 `[1,2]`。手机会纵向展示。

```json
{"type":"foldBlock","attrs":{"collapsed":true},"content":[
  {"type":"foldTitle","content":[{"type":"text","text":"展开查看"}]},
  {"type":"foldContent","content":[{"type":"paragraph","content":[{"type":"text","text":"说明内容"}]}]}
]}
```

这些容器可容纳表格、代码、分栏等符合 schema 的块。减少栏数或取消容器时按原顺序搬出全部内容，不能只保留第一栏。保存片段时补足必要容器，无法合法闭合时扩大选择范围。

## 表格

结构：`table → tableRow → tableCell / tableHeader → block+`。表头由实际 tableHeader 节点决定；可没有表头，不强制首行。不要给 table 设置不存在的 rows、columns、width 或 height 属性。

| 位置 | 属性 |
|---|---|
| table | blockAlign，整表在正文中的 left / center / right |
| tableRow | height，正数像素或 null |
| tableCell / tableHeader | colspan、rowspan（正整数，默认 1）；colwidth（每个跨列的像素宽度数组或 null） |
| 单元格 | align（列默认对齐）、cellAlign（本单元格覆盖）、backgroundColor（纯色或 null） |

合并后删除被覆盖的格子，保留其中全部内容；拆分时补齐真实单元格。按占据的网格核对跨度，确保各行覆盖同样列数。`colwidth` 长度等于 colspan；同一逻辑列的宽度与 align 在各行保持一致。如果已经固定列宽，新列也设置宽度。cellAlign 独立覆盖，不应通过改变整列 align 来只对齐一个格子。

```json
{"type":"table","content":[
  {"type":"tableRow","content":[
    {"type":"tableHeader","attrs":{"colspan":2,"colwidth":[180,180],"backgroundColor":"#e1efff"},"content":[{"type":"paragraph","content":[{"type":"text","text":"合并表头"}]}]}
  ]},
  {"type":"tableRow","attrs":{"height":48},"content":[
    {"type":"tableCell","attrs":{"colwidth":[180]},"content":[{"type":"paragraph","content":[{"type":"text","text":"左"}]}]},
    {"type":"tableCell","attrs":{"colwidth":[180],"cellAlign":"right"},"content":[{"type":"paragraph","content":[{"type":"text","text":"右"}]}]}
  ]}
]}
```

复杂表格导出为 HTML 保留尺寸、合并与颜色，普通表格可导出 Markdown。

## 图片、裁切、切分与组合

image 为行内节点，放 paragraph 等允许 inline 的容器；imageBoard 直接容纳 image。先 upload 获取真实 src，禁止猜内容 ID。src 是 `/assets/<32位id>.<扩展名>`，不带 `/yuyan` 前缀。

- 基础属性：src、alt、title、width、height、caption、shadow、blockAlign。caption 为可见说明，与 alt/title 独立；shadow 为可选布尔阴影边框。
- crop：`{x,y,width,height}`，相对原图的 0–1 范围；x+width、y+height 不超过 1；null 表示整图。sourceWidth/sourceHeight 保存原始像素尺寸，width/height 为显示尺寸。裁切后同步合理的显示宽高比例，原始素材不变。
- 物理裁剪：提取混合截图中的独立文字后，需要从上传素材中去掉文字区时，裁剪工作副本再 upload；新图 `crop:null`，`sourceWidth/sourceHeight` 为新文件实际尺寸，显示宽度按可读性设置并用 `height:null` 保持比例。与 `crop` 的阅读遮罩不同，实际文件已变小。
- 互补切分：复用同一 src，用不重叠 crop 矩形分割区域。例如左右两半为 `{x:0,y:0,width:0.5,height:1}` 和 `{x:0.5,y:0,width:0.5,height:1}`；原图不修改、不重新上传。已有 crop 时在当前区域内计算。
- `imageBoard`：attrs.width、height 为画板尺寸，blockAlign 为整体位置；content 是一个或多个真实 image。每张图片的 placement 为相对画板的 `{x,y,width,height}`。列表顺序也是叠放顺序。超出画板会被裁切。
- 改画板尺寸与整体缩放不同：前者保持图片像素位置时须按新尺寸重算 placement，后者可保持比例；根据用户意图选择。批量样式只是对所选图片合并相同 attrs，不修改无关图片。

## 可编辑画板

`drawing` 是原子块，与只包含 image 的 imageBoard 独立。attrs 为 src `/drawings/<32位ID>`、version 1、width 100–2400（首建不放大小图且不超过 800）、blockAlign left/center/right、caption，以及服务端派生的 text、previewWidth、previewHeight、previewMime。完整节点来自 `upload --kind drawing`，不能手造派生值；显示属性可局部修改，图形修改需生成并上传新包。

支持原生形状、文字、绑定连线、自由画笔和图片，包中保留 Excalidraw 场景。Markdown 导出以 HTML figure、预览和源文件链接保留；完整导出还需包及图片文件。生成、审阅、修改和跨实例导入见 [可编辑画板](drawing.md)。

## 附件

attachment 为块级节点，可嵌套于表格、分栏和折叠正文。upload --kind attachment 返回完整节点：src `/attachments/<32位id>`、name、size（非负字节数）、mime。空文件可上传；卡片改名只改 name。复制节点复用原文件，不重复上传。

阅读页支持位图、PDF、文本、音视频与常见压缩包目录等预览；工具可调用 preview API 获取文本/目录，复杂格式按其领域工具处理。HTML/SVG/XML 附件作为源码，不能当作网页执行。删除卡片不立即回收仍被历史、回收站或模板引用的文件。

## 文档与章节链接

link.attrs.href 存 `/docs/<id>` 或 `/docs/<id>#<编码后的slug>`，网页前缀由服务补齐。通过 link-targets/preview 找真实章节锚点，不自行猜 slug。文档移动/改名不改变文档 ID；章节改名或同名顺序调整可能改变 slug。

引用链接是普通文字的 link mark，没有飞书式 @人、评论或同步块。反向链接由存活正文推导，无需手工维护。模板/片段插入是独立内容副本，后续不会与来源自动同步。

## 兼容与能力边界

原生 JSON 覆盖已实现的正文能力。Markdown 方便普通写作，超出 Markdown 的内容通过项目已有 HTML 规则保留；不接受任意网页应用、脚本或自定义 CSS。可视化代码格式化、键盘选区、悬停预览、阅读位置等 UI 临时状态无需复刻为 CLI 命令。通过改最终文档结构完成用户意图即可。

维护时对照节点、属性、marks 和实际 API，检查新增格式是否需要更新本文的示例/校验；不能仅因 schemaVersion 仍为 1 就认为能力未变。尽量调用共享 schema；只在 scripts 中维护本技能的操作编排。
