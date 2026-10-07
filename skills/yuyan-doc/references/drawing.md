# 可编辑画板

适用于指定空间布局的树、数据页、扫描路径、架构和事务示意。普通说明、SQL 和表格优先使用原生文档块，自动布局的流程可用 Mermaid。`imageBoard` 只组合图片；`drawing` 保存可编辑图形，两者不互换。

## 生成、审阅、插入

画板生成使用 Yuyan 自己的 Excalidraw 适配层，避免手填随机种子、版本等内部字段。第一次按 preview 参考准备浏览器与已提交源码构建；已有依赖不重复安装：

```sh
node "$YUYAN_DOC" preview-setup
node "$YUYAN_DOC" drawing --input "$work_dir/spec.json" --out "$work_dir/drawing"
node "$YUYAN_DOC" upload --kind drawing --input "$work_dir/drawing/drawing.yuyan.json" --dry-run
node "$YUYAN_DOC" upload --kind drawing --input "$work_dir/drawing/drawing.yuyan.json"
```

`drawing` 默认 Chromium，支持 `--browser webkit`；总期限默认 60000 毫秒。生成只启动临时本机实例，浏览器限制同源访问，不连接生产、不修改用户文档。复用 `preview-setup` 缓存，缺失或源码过期立即报错，不隐式构建或安装。输出目录必须不存在；输出包、预览及必要图片，返回包/图片字节数和检索文字。包已包含预览，计算长期占用时不要重复加预览文件大小。

简单输入：`{"template":"tree"}`。模板支持 `page`（数据页）、`tree`（B+ 树）、`scan`（索引扫描）、`timeline`（事务时间线）；空白用于交互绘制，不能作为无元素的持久化包。也可用 `elements` 数组代替 template，采用 Excalidraw 的 element skeleton：

```json
{
  "background": "#ffffff",
  "elements": [
    {"id":"root","type":"rectangle","x":20,"y":20,"width":160,"height":70,"label":{"text":"索引页"}},
    {"id":"leaf","type":"rectangle","x":20,"y":180,"width":160,"height":70,"label":{"text":"数据页"}},
    {"id":"edge","type":"arrow","x":100,"y":90,"width":0,"height":90,"points":[[0,0],[0,90]],"start":{"id":"root"},"end":{"id":"leaf"}}
  ]
}
```

需要图片时 `files` 采用引擎 BinaryFiles（fileId、dataURL、mimeType、created），image 元素引用 fileId；仅支持 PNG/JPEG/GIF/WebP/BMP。它只在生成/编辑内存和独立导出中使用 Base64，上传包里的图片为 Yuyan 内容寻址引用。

先实际查看预览，核对中文、数字、箭头方向、端点和图例。SVG 可用浏览器查看，PNG 可直接用图片工具；需要整篇排版时在插入后按 preview 参考局部预览。不要用“生成成功”代替图形语义检查。

upload 先读取包同目录的图片并核对哈希，再上传图片和包，返回完整 `node`。`--dry-run` 只检查本地输入，不连接生产。随后 `read --out` 当前文档，用 `edit` 的 splice/replace 插入整个块；新文档用 create。服务端会核对包、派生文字及预览属性，不能手造 src/text 绕过上传。

## 修改与读取

- `schema --node drawing` 查看属性；`read --scope keyword` 可匹配图内派生文字，并返回所属画板。
- 显示调整只改 width（100–2400）、blockAlign（left/center/right）、caption，不改 src 和派生字段。
- 编辑图形可在网页打开画板，或读取 `api --path drawings/ID`，以 elements 修改后重新生成并审阅；上传新包，用局部 replace 替换原节点并保留说明、宽度和对齐。
- 图内文字不直接参与正文的文本替换，不能改派生 text 模拟改图；新文本必须进入场景并重建预览。
- 同实例复制节点可复用原包。跨实例必须上传完整包及依赖，不直接复用另一个实例的素材地址。

## 导出、预览与兼容

单篇 export 包含原生 JSON、Markdown/HTML、画板包、单份预览及图片。画板文件是 `<ID>.yuyan.json`，图片与其同目录；HTML figure 里保留预览和源文件链接。`download --src /drawings/ID/file|preview --out FILE` 下载对应内容。独立 `.excalidraw` 文件通过网页画板的“可编辑文件”下载，其中临时嵌入所需图片。

重导完整 Markdown 文件夹使用项目导入工具，仅对空的隔离实例演练。局部恢复到现有知识库用 upload + revision 保护的 edit；不能整库重导覆盖已有编辑。缺源文件、缺图片或哈希不符必须停止。

`preview --media-dir <导出目录或attachments目录> --offline` 可复用本地包与图片；远端读取只 GET 快照所属实例的实际媒体。不匹配的包/图片拒绝预览。未知格式/引擎版本保留原包并停止写入，不删除未知内容；服务可能仍提供安全静态预览。

画板包和依赖图片受正文、回收站、历史和模板保护；未引用包的一小时宽限期也保护图片。上传后及时写入文档，不能把未引用素材当作长期仓库。既有图片重绘需另行逐图审阅，图片放进画板不等于减少了位图占用。
