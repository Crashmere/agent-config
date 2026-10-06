# 接口与故障处理

## 配置来源

读取 `https://raw.githubusercontent.com/ENA-QWQ/Mscd/main/config.js` 及必要的调用代码，核对当前配置；把它作为数据阅读，不执行远程 JavaScript。初始默认值是 `https://api.qijieya.cn/meting/` 和 `https://zm.wwoyun.cn/`，属于第三方服务。脚本可用 `--meting-base`、`--netease-base` 临时覆盖；服务地址变化时先验证，再修订技能。

上游网页的 `https://mscdownload.pages.dev/proxy?url=` 主要用于浏览器跨域；本地 curl 通常直接访问接口，不需要先使用代理或启动网页。不要把第三方接口描述成网易云官方授权接口。

| 请求 | 用途/关键字段 |
| --- | --- |
| `cloudsearch?keywords=...&type=1002&limit=30&offset=0` | 昵称搜索，`result.userprofiles[].userId` |
| `cloudsearch?keywords=...&type=1&limit=30&offset=0` | 替代歌曲搜索，必要时自行翻页 |
| `user/playlist?uid=...&limit=100&offset=...` | 歌单列表，依据 `more` 翻页，区分 creator |
| `playlist/detail?id=...` | `playlist.trackCount`、`trackIds`、`tracks` |
| `playlist/track/all?id=...&limit=500&offset=...` | 数量差异交叉核对，长歌单继续翻页 |
| `song/detail?ids=...,...` | 以 ID 批量补齐歌曲详情 |
| `song/url/v1?id=...&level=lossless` | `data[0].url`、`freeTrialInfo`、`code` |
| `song/url?id=...&br=999000` | 旧版补充尝试；实际质量需 probe |
| `lyric/new?id=...` | `lrc.lyric`、`tlyric.lyric`、`yrc.lyric`、`nolyric` |
| Meting `?server=netease&type=url&id=...&br=2000` | 请求无损，可能 302、URL 文本或 `@URL`，也可能实际 MP3 |
| Meting `?server=netease&type=url&id=...&br=320` | MP3 候选，并非保证 320 kbps |
| Meting `?server=netease&type=lrc&id=...` | LRC 降级来源，须排除 HTML/JSON 错误页 |
| Meting `?server=netease&type=playlist&id=...` | 必要时第三路交叉核对歌单 |

脚本将 HTTP 源地址升级为 HTTPS，只允许 HTTPS 跳转；纯 HTTP 服务不会自动放宽。302 的 `Location` 单独解析后升级。网易云兼容接口返回的试听标记直接拒绝；Meting 未返回该标记时仍以时长和完整解码检查片段。

## 歌单数目和版本

`trackCount` 大于 `tracks.length` 很常见，不能直接用内嵌 `tracks` 当全量。先用 `trackIds` 补详情，再比较声明数与 ID 数。若 `trackIds` 也少，使用 track-all 和 Meting 交叉核对；多条接口都缺失时记为不可解析，不能猜 ID 或把差值“补平”。公开接口无法保证读取私密歌单。

默认以歌曲 ID 定义重叠。另一专辑中的同名同艺人同毫秒时长，只能认定元数据匹配；仍可能有母带、审查版、混音差异。替代时保持原条目与下载条目双重 ID；不要把原 ID 写成实际音源 ID，也不要把原专辑封面写入新的专辑发行。

## 网络和音质

- 连接重置、超时、截断：curl 有限重试并下载到 scratch，ffprobe 和完整解码成功后才发布。持续失败时重新解析临时 URL，记录原始错误类别，不缓存过期签名链接。
- 无损请求得到 MP3：用 ffprobe 的 `codec_name`、`bit_rate` 判定。保留原生编码；获准时选最高可用 MP3，否则继续其他无损歌曲并汇报。提高编码码率不会提升音质。
- NULL/404：区分某一路接口失败、某个发行不可用和整首录音不可用。尝试其他已配置接口，再查同录音的其他发行；没有授权时不能任意换歌。
- 30 秒片段：拒绝 `freeTrialInfo`，核对元数据完整时长。脚本允许最多 3 秒或 1.5% 的封装/尾音差异，但明显版本差异仍需人工判断。
- 本地格式核验：`ffmpeg -xerror` 完整解码；写标签前后音频 packet SHA-256 一致，FLAC STREAMINFO MD5 保持不变，采样率/位深/声道不变。它不证明源文件从未被有损转码。

## 封面和歌词

- 封面原 URL 403 时，用 URL API 设置 `param=1000y1000` 重试，保留其他 query，不手工拼接第二个 `?`。确认返回 JPEG/PNG；HTML 错误页不能嵌入。脚本将封面缺失视为失败，避免误报标签完整。
- 使用实际下载发行的歌名、艺人、专辑、封面、曲号和日期。网易云 `publishTime` 按 `Asia/Shanghai` 转为发行日期；直接截取 UTC ISO 日期会把中国区零点提前一天。缺少专辑名可以留空；专辑 ID 为 0 时不要用它作为共享缓存键。本脚本按歌曲建 scratch，避免缓存串封面。
- FLAC 用 Vorbis `LYRICS` 与图片块。MP3 写入 ID3v2.3 UTF-16 `USLT`；仅用 ffmpeg 的 `-metadata lyrics=...` 可能生成自定义 TXXX，播放器不一定认。脚本会重建 USLT 并反查歌词哈希。
- 翻译和逐字歌词写在 `LYRICS_TRANSLATION`、`LYRICS_YRC`；播放器对这些额外标签和 USLT 内时间戳的支持各异，不承诺每个播放器逐字滚动。
- 将 `nolyric` 或“纯音乐，请欣赏”记录为 instrumental。请求失败、无词与纯音乐不能混为一谈；普通续传不会重新获取已完成文件的缺失歌词。
- 需要补歌词/封面时，先重新获取可信数据，使用 `audio.mjs` 的 `tagAudio` 将原文件流复制到新的临时文件，核验后更新对应 record 的哈希、大小和歌词状态。保留原文件直至替换完成；随后再审计汇总。不要只改报告，也不要删除整首歌重下作为默认做法。

## 续传与文件故障

- `running.lock` 存在：查看其中 PID，并用进程信息核对是否属于该任务。仍在运行就沿用现有进程；明确进程已退出后才清理这一个过期锁。不要自动删锁后并行启动。
- 计划不同：同一输出目录绑定 `.mscd/plan.json`，增加歌单或改排除条件时新建输出目录，避免混合旧记录。修改未成功条目的 replacements 后可继续原计划；成功文件的源版本或说明变化会要求检查。
- 文件被移动：先定位实际新目录；整体移动保留相对记录，传新 `--out` 即可。只移动音频时，核对原始标签/哈希后修正记录，不把旧路径不存在等同于从未下载。
- 文件损坏或未知同名文件：先保留并检查。若是该任务自己的损坏文件，可将其明确移入本次隔离目录，再重跑；不要静默覆盖用户已有内容。审计失败会保留原记录的校验依据，便于修复后恢复。
- `.mscd/work` 遗留：确认没有活跃下载后才清理本任务生成的 scratch。不要以清缓存为由删除整份音乐库或其他任务状态。
- Unicode 路径：Node 模块路径用 `fileURLToPath(import.meta.url)`，不要直接用 URL `.pathname`，否则中文路径会保留百分号编码。
- 文件名包含引号、反引号、`$()` 或 `**`：使用 `execFile` 的参数数组；不要把文件名插入 shell 命令字符串。不要通过打印完整命令泄露下载签名。
- 多并发：同一进程最多四个 worker；每首独立记录，所有任务结束后从磁盘生成统一汇总。不要让多个进程用各自旧内存覆写 manifest。

修订脚本后运行 `node --test scripts/selftest.mjs`，覆盖离线合成音频、实际码率、试听拒绝、共享歌单、版本排除和断点审计。模拟接口通过不能证明远端仍可用；实际任务另做小规模连通性与首曲验证。
