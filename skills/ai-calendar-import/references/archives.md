# 完整聊天存档

## 数据与范围

每个会话保存不可变快照，通过 `source + conversation_id` 与每日记录关联；新增对话内容时保存新快照，旧快照保留。同一内容重复上传去重，不能覆盖已完成快照。消息正文、代码和工具返回不做摘要替换。统一格式为 UTF-8 JSONL + gzip；长消息只分段，不截断；原始来源文件按字节保存并核验 SHA-256。服务 Schema 维护源为 AICalendar `api/archive.schema.json`，不要在技能中复制。

日历次数仍只计用户实际发送；存档消息总数包含 AI、工具及系统等内容，与使用次数含义不同。摘要的隐藏状态不删除完整存档。

保存用户指定的导出资料，包括其中附带的图片、音频、附件实体和未知字段。只有 URL、本地路径、临时资源 ID 时保留引用，报告原件未提供；不要自行读取聊天之外的本地文件或抓取外链。Trae 提取器默认保留完整 rollout 与历史投影，不自动读取日志里提及的附件路径、其他项目文件或独立子 agent 数据库。它的 coverage 为 partial，表示本机可取得资料的快照，不能证明平台历史从未丢失。

## Trae 导入

`extract_trae.py` 默认产生 archives/index.json。为其中每份 archive 执行：

```sh
python3 scripts/archive_conversations.py prepare --archive /private/task/archives/THREAD.jsonl.gz --out /private/task/archive-plan.json
python3 scripts/archive_conversations.py submit --plan /private/task/archive-plan.json
```

先完成存档，再导入日历摘要；两个步骤各自可重试，不假称跨接口整批原子提交。Trae 提取可加 `--source-label "Trae · 工作电脑"`，通用 pack 可用同名参数覆盖展示来源标签；稳定 source 不随标签改名。只完成存档而摘要失败时，保留存档并继续重试原摘要计划。

标签保存在服务清单中；同一 gzip 内容仅更改清单的 source_label 后生成新计划、重新 prepare/submit，可更新展示标签而不产生新快照。不要编辑已有固定计划；也不要改写原始导出只为改标签。省略或空标签保留服务上的已有值。日历记录的标签另用摘要 upsert 同步，两个接口不会互相修改。网页存档列表支持标签关键词筛选。

## 其他平台

外部 agent 将导出转换为本地统一 JSON：source、conversation_id、title、coverage、note、messages，以及可选 source_label（用户给出的来源标签）。messages 中每条包含稳定 id、role、at（带时区或 null）、content（原样文本或结构）、attributes（可选原模型、工具名等小型元数据）。role 使用 user、assistant、tool、system、developer、unknown。保留消息顺序、空消息与原始语言，不把多轮揉成摘要。转换无法覆盖的字段仍在原始导出中保留。

统一 content 的结构化值会转成 JSON 文本供展示；精确原类型及平台未知字段仍在逐字节保存的原始文件中。原始文件名单独保留，不因内部临时快照命名改变。

```sh
python3 scripts/archive_conversations.py pack --file /private/task/conversation.json --source-file /private/export.json --source-file /private/attachment.png --out /private/task/conversation.jsonl.gz
```

统一输入文件也会作为原始资料保存。额外 --source-file 可重复；打包先复制固定快照，后续上传使用这些确定字节。每份存档最多压缩后 128 MiB / 展开后 512 MiB；超限明确失败，按连续分卷保存并在 note 标明范围，不丢弃超限内容、不声称完成。

## 可靠上传与取回

`prepare` 固定目标地址、文件路径、整体 SHA-256 和分块清单；`submit` 上传缺少的 384 KiB 分块，再请求服务验证 gzip、统一消息顺序、原始资料分块及每份来源 SHA-256。仅完整验证后可浏览。最后下载实际存储字节，比较整体哈希和长度。原计划重试已完成存档返回 replay，不新增副本。

网络失败保留文件和计划，重新执行同一个 submit。收到 400/409 时检查明确错误；不能通过改哈希、丢分块或减少计数骗过校验。503 表示服务未启用存档扩展，应完成维护后重试。

批量回读清单使用 `GET /ingest/v1/archives?source=...&offset=0&limit=100`，每页最多 100 条。当前接口始终返回 `next_offset=offset+本页条数`，末页不以 null 标记结束；本页为空或少于指定 limit 时停止，否则使用返回的 next_offset。核对所有快照 ID、已提交状态、清单哈希及会话关联，修订快照不重复计作新会话。

网页「聊天存档」可按快照查看消息并下载 `.jsonl.gz`。完整还原：

```sh
python3 scripts/archive_conversations.py unpack --archive /private/download.jsonl.gz --out /private/new-directory
```

输出合并长消息后的 messages.jsonl、逐份原始文件 original-NNN.bin 和文件名/类型/哈希映射 sources.json；原始文件逐份核验。输出目录必须不存在，不跟随来源文件名写任意路径。服务没有自动清理完整存档或删除原文的接口。

上传保存不等于已做备份。备份范围以服务 [运维文档](https://github.com/Crashmere/AICalendar/blob/main/docs/OPERATIONS.md) 为准：当前每日 SQLite 备份只包含活动与导入审计数据，不包含完整聊天、原始资料及其上传分块和索引。需要长期保留的原始资料应由用户另行保存，不因上传成功就自行删除本地原件。
