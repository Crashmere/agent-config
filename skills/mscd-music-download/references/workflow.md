# 查询、计划与下载

导航：[准备目录](#1-准备本次工作目录) · [查询](#2-查用户与完整曲目) · [差集](#3-分析重叠与生成差集) · [下载与替代](#4-下载与受控替代) · [续传与交付](#5-续传输出和交付)

## 1. 准备本次工作目录

使用已有 Node.js 20+、curl、ffmpeg 与 ffprobe。示例采用 POSIX shell；脚本由 `node` 调用，不需要上游仓库安装或启动网页服务。

```bash
mscd_skill="$HOME/agent-config/skills/mscd-music-download"
mscd_work="$(mktemp -d "${TMPDIR:-/tmp}/mscd-task.XXXXXX")"
command -v node curl ffmpeg ffprobe
node "$mscd_skill/scripts/library.mjs" --help
node "$mscd_skill/scripts/download.mjs" --help
```

选择本次音乐输出目录，优先沿用用户明确给出的位置。工作目录保存查询快照、计划与替代规则；最终输出内的 `.mscd` 保存续传所需状态。结束时保留用户需要的快照和报告，不把它们提交到技能仓库。

## 2. 查用户与完整曲目

以下变量填入本次核实的值，不把个人账号写进 skill：

```bash
node "$mscd_skill/scripts/library.mjs" search-users "$mscd_nickname" --out "$mscd_work/users.json"
node "$mscd_skill/scripts/library.mjs" user-playlists "$mscd_uid" --out "$mscd_work/playlists.json"
node "$mscd_skill/scripts/library.mjs" playlist "$mscd_playlist_id" --out "$mscd_work/target.json"
node "$mscd_skill/scripts/library.mjs" playlist "$mscd_liked_id" --out "$mscd_work/liked.json"
```

从 `users.json` 选出匹配的数字 UID，不将昵称当 UID。`createdByUser` 区分创建/收藏；喜欢的歌单名称随用户而变，不凭固定名称或历史数量选取。指定了几个字符歌单时，逐一读取其 ID 并保存快照。

`playlist` 以 `trackIds` 的顺序补齐 `/song/detail`，保留 `declaredCount`、`returnedIds`、`unresolvedIds`、`countGap`。它不自动使用所有交叉核对接口；出现缺口时读取 API 故障说明并检查。所有查询命令的 `--out` 都拒绝覆盖已有文件；刷新时用新的文件名。

## 3. 分析重叠与生成差集

```bash
node "$mscd_skill/scripts/library.mjs" overlap \
  --snapshot "$mscd_work/target-a.json" --snapshot "$mscd_work/target-b.json" \
  --snapshot "$mscd_work/liked.json" --out "$mscd_work/overlap.json"
node "$mscd_skill/scripts/library.mjs" plan \
  --snapshot "$mscd_work/target-a.json" --snapshot "$mscd_work/target-b.json" \
  --exclude "$mscd_work/liked.json" --out "$mscd_work/plan.json"
```

- 重复 `--snapshot` 添加目标，重复 `--exclude` 添加排除歌单。单歌单下载只需一个 `--snapshot`，不需要排除时省略 `--exclude`。
- `overlap.json` 的矩阵顺序与 `playlists` 一致，单元格是共同歌曲 ID 数组；`unique` 是唯一 ID 数，`records` 是各列表记录总数。
- 计划中 `items` 按 ID 合并目标歌单，`memberships` 保留每个原位置，`skipped` 记录排除原因。
- `versionCandidates` 只比较目标与排除歌单：歌名和艺人匹配、时长相差不超过 20 ms、ID 不同。默认仍下载；用户明确接受这种元数据匹配去重时再用 `--dedupe-versions`。它不能证明录音相同，也不合并目标歌单内不同 ID 的发行。
- `--exclude` 根据歌单成员关系排除，不扫描本地磁盘。若用户要按本地实际文件排除，先核验清单和文件；只把确实有效的原/替代 ID 加入工作计划，保留可追溯的排除记录。
- 不完整快照默认阻止计划生成。排查后仍少 ID 时可用 `--allow-partial` 下载已解析部分；此标志不消除缺失，最终报告必须列出。排除快照中已知 ID 即使无详情也会被排除，但接口未返回的 ID 无法推断。

## 4. 下载与受控替代

```bash
node "$mscd_skill/scripts/download.mjs" \
  --plan "$mscd_work/plan.json" --out "$mscd_output" --jobs 3
```

用户允许有损补齐时加 `--allow-mp3`。脚本先尝试 Meting 无损，再尝试网易云兼容的无损/旧版地址和 Meting 320；首个有效 FLAC 优先。没有 FLAC 时比较实际 MP3 码率，可能只有 192 或 128 kbps，不能写成 320。此流程不搜索所有平台，也不保证在多个 FLAC 之间找最高采样率。

失败条目需要其他发行时，先搜索再获取候选的规范化详情：

```bash
node "$mscd_skill/scripts/library.mjs" search-songs "$mscd_search_text" --out "$mscd_work/candidates.json"
node "$mscd_skill/scripts/library.mjs" song "$mscd_candidate_id" --out "$mscd_work/candidate.json"
```

在本次 `replacements.json` 中用原 ID 作为键，`song` 填入候选完整对象，`note` 写明核对过的差异与替代理由：

```json
{
  "10001": {
    "song": {
      "id": "10002", "title": "示例歌曲",
      "artists": [{"id": "20001", "name": "示例歌手"}],
      "album": {"id": "30002", "name": "示例专辑", "cover": "https://example.com/cover.jpg"},
      "durationMs": 180000, "track": 1, "disc": "1", "publishTime": 0
    },
    "note": "原单曲不可用；已核对艺人、时长及版本信息，使用获准的专辑发行。"
  }
}
```

示例 ID/URL 仅解释格式，不可直接下载。使用 `--replacements "$mscd_work/replacements.json"`；后续续传和审计同样传入。脚本要求艺人匹配、时长差不超过 2 秒且有说明，歌名不同还需 `acceptTitleDifference: true`；这个布尔值只能在实际核对且获得必要授权后设置。脚本不能代替试听或版本判断。替代源若与本计划另一首或排除 ID 冲突，会提前拒绝；先调整计划或排除策略，不重复下载。

## 5. 续传、输出和交付

重复原命令即可续传。审计使用相同计划、音质和替代参数，再加 `--audit`；审计不会获取音频、歌词或封面，但会更新核验记录和报告。移动整个输出目录后，只需改 `--out`；相对路径和 M3U 引用仍可用。

| 文件 | 用途 |
| --- | --- |
| `<歌单名> [ID]/<位置> - <歌曲> [原ID].flac/mp3` | 已核验音频；共享曲目放在第一个目标歌单目录 |
| 每个歌单的 `playlist.m3u8` | 当前补充结果，按原顺序引用共享文件；排除歌曲不会出现在此 M3U |
| `manifest.json`、`results.csv` | 成功/失败、实际音质、歌词、封面、源 ID、替代说明与相对路径 |
| `.mscd/plan.json` | 固定的原始下载计划；换任务用新输出目录 |
| `.mscd/records/<原ID>.json` | 单曲进度、哈希及核验结果 |
| `.mscd/summary.json`、`running.lock` | 汇总和进程锁；正常结束后移除锁 |

退出码 `0` 表示本计划全部成功且没有歌词不可用/快照缺口；`2` 表示有单曲失败、歌词不可用或快照缺口，需读取报告分别处理；`1` 表示参数、锁或其他全局错误。纯音乐不计入歌词不可用。

已有成功文件的续传会检查标签、歌词哈希、时长、文件大小和音频包哈希；`--audit` 另做完整解码。歌词暂时不可用的成功音频不会因普通续传重新取词；需要按故障说明补写，不能期待无限重跑自动恢复。文件损坏时保留文件并记失败，不静默覆盖。

最终提供输出目录与清单链接，并区分“可解析计划完成”和“歌单原始总量完整”。报告实际 MP3 码率分布、歌词/纯音乐/缺失、替代发行、尚未解决的错误；不把个人账号、音乐或运行状态提交到仓库。
