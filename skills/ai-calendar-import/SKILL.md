---
name: ai-calendar-import
description: 手动整理 AI 使用历史并导入个人 AICalendar：从本地 TraeX 历史或用户提供的导出资料提取日期与发送次数，归纳主题，生成稳定记录，预览、分批提交并回读核验。仅在用户要求导入、补录、整理 AI 日历记录或显式调用本 skill 时使用；不在普通聊天中自动记录，不安装 hooks 或定时任务。
---

# AI 日历导入

把服务当作规范化记录的保存与展示端。来源资料的理解和转换在本地完成；不要求服务接入任何 AI 平台。

## 边界与维护源

- 服务源码和 API 契约：`Crashmere/AICalendar`，通常在 `~/ali/AICalendar`。先读 [接口与客户端](references/api.md)。JSON Schema 的维护源为服务 `api/import.schema.json`，不在技能中另存副本。
- 读取 TraeX / traecli 时，再读 [Trae 历史](references/trae-history.md)。其他平台按用户指定文件理解字段，保留原始标识和不确定性，不套用 Trae 格式。
- 只在用户要求整理时运行。不增加全局 AGENTS 上报规则、hooks、常驻进程或定时任务。
- 标题、摘要、标签由当前 agent 归纳；时间、次数、稳定标识由确定性脚本提取。不要凭主题推测次数、耗时或日期。
- 原始对话、临时 JSON、导入计划和凭据留在 Git 外的私有目录。服务只收到整理后的记录与来源说明。只读本地文件仍可能把选定片段带入当前模型，不把它描述为本地模型推理。

## 完整流程

1. 确定来源和日期。用户指定优先；首次「最近」默认 7 天，后续先用 `status` 查看成功覆盖，向前重叠 7 天补充迟到记录。未知范围不要当作已经完整覆盖。
2. 在 `~/.local/state/aicalendar/` 下为本次任务创建独立私有目录。读取源资料；Trae 使用提取脚本生成候选记录与单独的审阅片段。
3. 审阅片段，必要时按会话追加只读查询，归纳简洁标题、1–3 句摘要和少量标签。修改候选 `records` 中的主题字段，将 `quality.topic` 设为 `agent_summary`。长会话不要仅凭前几条片段断言整日主题；先扩展该会话取样或保留较宽的标题。
4. 核对一条记录代表同一来源会话在同一天的完整快照。`source` 是账户命名空间，`external_id` 稳定；重导不生成随机 ID，不把发送次数累加到旧值。原始信息不足时使用 null/unknown。
5. 运行本地 `validate`，再 `prepare` 生成不可覆盖的固定计划。已存在且用户要求补全的记录用 `--upsert` 读取当前版本；普通首次导入用 insert_only。
6. 运行 `preview`。对已获授权的新增导入直接继续；发现真实覆盖冲突、减少已确认次数、删除或回退时展示具体差异并按已有授权处理，不能强行换 ID 绕过去重。
7. 运行 `submit`。它逐批重新预览、幂等提交、核对回执，最后回读记录；网络失败使用**原计划**重试。不要更换幂等键，也不要跳过失败批次先提交完整覆盖声明。
8. 报告实际来源/日期范围、新增与更新、重试跳过、未解决冲突与数据局限，给出日历链接。发生 replay 时回执中的 inserted 是原批次结果，不称为本次再次新增。`superseded_records` 表示原计划成功后已有较新版本；明确说明当前数据已更新，不把旧计划当失败反复提交。

## 命令

下列路径按实际 skill 根目录解析。脚本只依赖 Python 标准库。

```sh
python3 scripts/extract_trae.py --from 2026-10-01 --to 2026-10-07 \
  --out /private/task/draft.json --context-out /private/task/context.json
python3 scripts/import_records.py validate --file /private/task/reviewed.json
python3 scripts/import_records.py prepare --file /private/task/reviewed.json --out /private/task/plan.json
python3 scripts/import_records.py preview --plan /private/task/plan.json
python3 scripts/import_records.py submit --plan /private/task/plan.json
```

`--config /private/client.json` 写在子命令之前；默认 `~/.config/aicalendar/client.json`。`status` 查询导入范围，`lookup --source trae-personal` 查询现存记录（含隐藏项与版本）。

## 记录语义

- `user_message_count` 只计可恢复的用户实际发送，执行中追加消息也计数；子 agent、工具调用、自动续跑和压缩不算本人发送。
- 日期、来源会话、时区确定后不通过普通 upsert 更换。第一版自动阻止降低已确认次数或数据质量；需要真实更正时交给受控维护流程。
- `first_activity_at` / `last_activity_at` 可以只表示发送时间点；只有时间点时使用 `quality.time=observed_timestamps`，`spans=[]`。不要拿首尾相减当投入时长。
- 同一天多个活动区间可以放进 spans；跨天按时区拆分。时间未知时为 null；次数未知时为 null 且 quality.count=unknown。
- `quality.count=observed` 只表示所选资料中可直接辨认的发送数，不保证平台保留了全部历史。无法确认覆盖完整性时声明 partial。
- 用户在网页改过的标题、摘要、标签与隐藏状态独立保存；重导不得覆盖这层修改。
- 导出包包含 `activities[].record` 和 `activities[].annotation`。再导入前明确抽取 record；注释的恢复属于单独操作，不直接把导出包当导入请求。

技能或脚本遇到真实格式变化时，先解决本次任务，再按 personal-skill-management 修正本技能；不得把旧格式解释成空数据后报告成功。
