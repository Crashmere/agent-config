# 本地 TraeX 历史

当前提取器面向本次实测的 TraeX / traecli `~/.trae/cli/`，不承诺兼容所有 Trae IDE。遵从 TRAECLI_HOME，或 TRAE_HOME 下的 cli。

## 实测来源

- `state_5.sqlite`：线程 ID、来源、名称/标题与 rollout 路径。
- `thread_history_1.sqlite`：`thread_items.userMessage` 投影，含消息创建毫秒与结构化内容。
- `sessions/**/rollout-*.jsonl`：旧 `event_msg.user_message` 与新 `history_mutation`，可辅助缺少投影的资料。

数据库以 mode=ro / query_only 打开，不修改源文件或 journal 模式。需要一致性副本时使用 SQLite backup API，不能只复制 WAL 数据库主文件。

## 计数规则与限制

1. 只处理 source=cli 的本人交互线程。exec 和子 agent 默认跳过；需要纳入自动任务时另定统计口径。
2. 有结构化用户消息投影时优先使用，不同时叠加原始日志。原始 user role 可能是 AGENTS、环境、skill、压缩摘要或重放。
3. 无投影时，仅接受显式 `event_msg.user_message`，或带 `user.text` 与原始 `create_time` 的消息。用原始时间和本地内容指纹消除明显重放；fallback 标记 estimated。
4. 压缩会重新生成 item ID；不能单靠 ID 去重。实测长任务 81 个 user 片段、27 个不同 user.text item ID，仅对应 1 个原始创建时间与 1 条投影输入。
5. 投影有回退/修订控制时标记 estimated。投影可能只保留当前可见路径，不能保证包含所有曾发送后被回退的输入；导入覆盖保持 partial。
6. 跨格式迁移、分叉继承和旧版时间精度可能产生不能自动判断的重复。发现明显异常时审阅具体会话，不用扩大模糊去重掩盖差异。
7. 按用户消息时间分日，不能用 rollout 文件创建日筛掉后来恢复的旧会话。脚本会检查所有可用交互线程，再按指定日期过滤。
8. 不生成耗时推测。首尾字段只保存可恢复的消息时间点，time=observed_timestamps、spans=[]。
9. 旧投影的 created_at_ms=0 表示未知，不能解释成 1970 年后被日期过滤静默丢弃。整份用户投影均为零值且原始日志仍在时，使用日志中的显式用户事件替代整份投影，保持 estimated，不叠加两者；旧投影可能只包含会话后半段。其余缺少发送时间的投影可用 thread_turns.started_at 确认轮次日期，设 time=date_only、首尾时间为 null，不把轮次启动当作发送时刻。连日期也无法确认时明确失败，不能猜测。
10. rollout 缺失时仍检查消息投影，存档保留投影与轮次元数据并注明原日志缺失；不能直接跳过仍可恢复的消息。只有标题或空会话元数据时不推测发送次数。
11. 极旧 history_mutation.append 可能只有 turn_id，没有 content_item_kinds / create_time，且没有投影。脚本将这类候选放入上下文的 unresolved_legacy_threads，返回 requires_manual_review；不能据 raw user role 自动计数或当作空历史报告完成。逐条审阅原始行，区别真正输入、AGENTS、技能提醒和压缩摘要，只恢复可确认的初始 append，并记录行号与 item_id 作为私有证据。replace 重放不重复计数；补充记录保留 estimated，同时补充完整存档。

输出包括：候选日历 JSON、包含少量用户片段及待核实旧格式候选的审阅上下文，以及 `archives/index.json` 指向的每会话完整 `.jsonl.gz` 存档。存档保存全部可取得的用户、AI、工具及系统事件的统一消息，并按字节保留可取得的 rollout 快照、投影和轮次原始行；不仅保存用户发送。零值消息时间在统一存档中为 null，原始行仍保留零值。归档采样不受 `max-snippets` 限制，计数仍沿用前述规则。

每个选中会话连同日期范围外的上下文一并归档。默认存档目录为候选文件同目录的 archives，可用 `--archive-out-dir` 指定；仅用户明确要求摘要时使用 `--summary-only`。投影优先用于阅读，原始 rollout 保留修订、重放和未完成末行，以便未来重新解析。

上下文用于归纳，不能上传到日历 API。默认每条最多 8 个片段、每段 800 字；必要时使用 `--max-snippets` 和 `--snippet-chars` 扩大指定范围，或针对一个会话追加只读调查。

本机仍在运行的线程会持续变化，提取器将当前自然日候选标记 partial；审阅完提取时快照后仍按 SKILL.md 判断整理进度，可设 final。后续新增内容用稳定 ID 补充，不因会话仍活跃而永久保留待整理状态。完整性声明不能因为脚本成功执行就改成 complete。真正想得到完整历史需先确保来源保留和导出范围完整。
