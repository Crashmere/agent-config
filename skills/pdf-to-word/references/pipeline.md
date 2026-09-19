# 运行与配置

## 内容导航

- 工作目录与依赖
- 主流程命令
- 文档配置
- 第二OCR与公式工具
- 工具维护和验证

## 工作目录与依赖

直接运行仓库中scripts的代码，把工作数据放在仓库外。PDF_WORD_WORKSPACE默认当前目录；若它落在技能仓库内，主入口会拒绝执行。不要在skill目录中创建.venv、模型、输入输出或OCR缓存。

| 任务目录中的路径 | 内容 |
| --- | --- |
| input/ | 待转换PDF；每份用唯一文件名，保留来源 |
| config/overrides.json | 可选文档配置；没有时按默认策略运行 |
| work/batch/<文件名>/ | 哈希、布局、OCR、图片、审计和检查结果 |
| work/batch/rendered/ | LibreOffice实际导出的预览 |
| output/ | Word、汇总报告和可选交付压缩包 |
| models/ | 默认本地OCR模型缓存，可配置为外部共用路径 |

使用python-environment选择健康的隔离环境，确认PyMuPDF、python-docx、Pillow、OpenCV、RapidOCR、ONNX Runtime等导入正常。需要安装时使用[scripts/requirements.txt](../scripts/requirements.txt)列出的经过验证的依赖组合，并遵守该技能的安装方法。不要为了运行本技能重建已有可用环境。

使用docx技能的office/validate.py进行XSD校验；默认查找用户主目录下.trae/skills/docx/scripts/office/validate.py，可以通过DOCX_VALIDATOR指定实际安装位置。缺少所需技能时按personal-skill-management检查来源，不能跳过验证并声称通过。

用LibreOffice导出预览；不依赖Microsoft Word激活。SOFFICE可指定可执行文件路径；默认从PATH和macOS应用路径查找。当前默认中文字体为Songti SC/Heiti SC，英文字体为Times New Roman。macOS之外必须先确认字体、渲染环境；Apple Vision只在macOS可用。

## 主流程命令

以下示例在实际任务目录运行。把PDF_WORD_SKILL和PDF_WORD_PY设置为当前实际技能位置与隔离环境解释器，避免复制旧机器路径。

~~~sh
PDF_WORD_SKILL="$HOME/agent-config/skills/pdf-to-word"
PDF_WORD_PY="$PWD/.venv/bin/python"
export PDF_WORD_WORKSPACE="$PWD"
export PYTHONDONTWRITEBYTECODE=1

"$PDF_WORD_PY" "$PDF_WORD_SKILL/scripts/convert_batch.py" --help
"$PDF_WORD_PY" "$PDF_WORD_SKILL/scripts/convert_batch.py" prepare
# 查看work/batch中的layout.txt并对照原图，再决定配置或OCR路线。
"$PDF_WORD_PY" "$PDF_WORD_SKILL/scripts/convert_batch.py" build
"$PDF_WORD_PY" "$PDF_WORD_SKILL/scripts/convert_batch.py" render
"$PDF_WORD_PY" "$PDF_WORD_SKILL/scripts/convert_batch.py" check
"$PDF_WORD_PY" "$PDF_WORD_SKILL/scripts/batch_coverage.py"
~~~

在阶段后附文件名可只处理指定文档，例如prepare example --mode ocr。mode支持auto、native、ocr；仅影响prepare或all。all串联主阶段，输出仍需视觉复核及源覆盖检查。不要未经试转就在新类型整批文档上盲目套用默认参数。

重新build覆盖同名生成Word。用户编辑过的文件应另存，不把它作为重建目标。缓存绑定源哈希，审计绑定Word哈希，渲染记录绑定Word与预览哈希。同名源文件改变时，使用新文件名或在明确旧缓存可删除后移除该文件的work目录，再prepare。

## 文档配置

参考[assets/overrides.example.json](../assets/overrides.example.json)，在任务目录创建config/overrides.json。示例只展示格式；不要未经检查照搬页数或封面策略。

| 字段 | 说明 |
| --- | --- |
| source_sha256 | 原PDF哈希；非空配置必须绑定当前源文件 |
| cover_image | 默认true：第一页当封面保留原图；无封面时显式false |
| page_methods | 可选，按物理页列出native/ocr，长度须等于总页数 |
| full_image_pages | 额外整页保留的页码，从1开始 |
| regions | 页码字符串映射至矩形列表，格式[x0,y0,x1,y1] |
| replace | 经过原图核实的文字替换；属于文档配置，不自动推广 |

矩形以左上为原点，统一页面宽为595.276 pt，高度按源长宽比计算。替换为图片的文字框必须完整被裁剪覆盖，图注和边缘标记也要检查。图像保留不使其文字可编辑。

| 环境变量 | 用途 |
| --- | --- |
| PDF_WORD_WORKSPACE | 外部任务目录；默认当前目录 |
| PDF_WORD_MODELS | 外部模型缓存；默认任务目录models/ |
| SOFFICE | LibreOffice可执行文件 |
| DOCX_VALIDATOR | 安装的docx技能验证脚本 |

保持源码只读运行；用PYTHONDONTWRITEBYTECODE=1避免生成源码目录缓存。模型首次运行会按RapidOCR配置下载；复用已存在的缓存时通过PDF_WORD_MODELS指定，不复制模型到仓库。

生成器会替换默认字体、限制正文和表格字号，并启发式设置表头及首列对齐。它优先保持内容和稳定分页；对设计版式有要求时，应对照源样式调整并验证，不能仅凭文件可编辑就声称格式保真。

## 第二OCR与公式工具

在macOS上可编译Vision辅助识别器到任务目录：

~~~sh
mkdir -p work/bin
swiftc "$PDF_WORD_SKILL/scripts/vision_ocr.swift" -o work/bin/vision_ocr
work/bin/vision_ocr work/batch/example/page-*.png
"$PDF_WORD_PY" "$PDF_WORD_SKILL/scripts/batch_scan_review.py" example
~~~

扫描比较按布局选择OCR页；差异写入scan-review.json。两引擎的优劣与语言、字形相关，不能把第二引擎结果直接批量覆盖主结果。

word_math.py提供text、subscript、superscript、fraction、append_equation函数，供人工确认后创建OMML。它不识别PDF公式；每个XML节点只能插入一次。用新元素组装公式，再验证上下标、分数与渲染。精确行距可能裁切公式。

## 工具维护和验证

| 脚本 | 职责 |
| --- | --- |
| convert_batch.py / pipeline_config.py | 阶段编排、外部工作目录、哈希和文档设置 |
| batch_layout.py | 文字、字体修复、物理行、表格和OCR布局 |
| batch_convert.py | DOCX段落、表格、标题、图像和分页 |
| ocr_batch.py / vision_ocr.swift | 本地主要OCR与可选第二OCR |
| batch_check.py / batch_coverage.py | 渲染和结构、源字形/表格覆盖 |
| batch_scan_review.py | 扫描文字分歧与区域覆盖线索 |
| package_results.py | 校验当前文件哈希并汇总打包，不虚构人工复核 |
| word_math.py | 可编辑数学结构辅助函数 |
| smoke_pipeline.py | 临时合成输入验证，不保存真实文档 |

修改共用转换流程后，使用外部已有环境和模型运行合成验证；无需真实PDF：

~~~sh
"$PDF_WORD_PY" "$PDF_WORD_SKILL/scripts/smoke_pipeline.py"
# macOS且需要验证第二OCR时增加 --with-vision
~~~

自检包含原生文字、可编辑数值表、中文扫描、空白页、渲染、XSD、覆盖、哈希保护、打包和公式。仅--with-vision时在临时目录编译并运行Apple Vision。未运行的分支应明确报告；不要扩大检查到无关技能。
