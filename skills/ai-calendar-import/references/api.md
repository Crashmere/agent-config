# AICalendar 接口与客户端

服务契约维护源：[API 文档](https://github.com/Crashmere/AICalendar/blob/main/docs/API.md)、[JSON Schema](https://github.com/Crashmere/AICalendar/blob/main/api/import.schema.json)、[合成示例](https://github.com/Crashmere/AICalendar/blob/main/api/import-example.json)。本机 checkout 可直接读取；配置后可 GET `/ingest/v1/schema` 查看运行版本。

## 私有配置

默认 `~/.config/aicalendar/client.json`，配置和 token 文件权限必须为 0600：

```json
{
  "base_url": "https://YOUR_SERVER/aicalendar",
  "token_file": "/private/path/import-token"
}
```

地址和秘密不写入仓库。token 用文件读取，不放命令行、URL、对话或环境日志。客户端强制 HTTPS（本机 loopback 演示例外），禁止重定向，避免凭据转发到其他地址。

导入凭据只用于 `/ingest/v1/`：Schema、批次预览/提交、批次列表/回执和规范化记录查询。不能编辑网页注释、删除数据、管理门户设备或读取其他应用。

## 固定计划

`prepare` 生成本次固定请求，默认每批最多 200 条且预留体积余量。`--upsert` 会先读取现存记录版本。计划包括目标地址、内容摘要、稳定幂等键和所有批次；覆盖声明放在最后，只有前面的记录成功才提交。

`preview` 不写业务数据；有冲突时输出完整 JSON 并以退出码 2 结束，普通错误为 1。`submit` 每批再次预览，然后提交并回读回执；失败保留计划，再次 submit 同一计划可恢复。服务以 `source + external_id` 去重，并以幂等键防止网络重试重复提交。

已成功的旧计划重放后，当前记录可能已被后续批次更新。客户端根据回执版本区分：同版本逐条核对并计入 `verified_records`；更高版本列在 `superseded_records`，返回 `committed=true, exact_current=false`，表示原提交成功且已有更新，不是网络失败。不要为此重复重试或覆盖新版本。记录缺失、版本倒退或同版本内容不同仍以错误退出。

不同请求不能共用幂等键。已有记录发生并发更新时，旧计划可能冲突；回读新版本和差异，按用户目标准备新文件、新计划。不要自行覆盖用户展示修改或减少已确认次数。

JSON 文件中的数字是当前完整快照值。记录原来 6 次、新资料确认 8 次，提交 8；不能加成 14。

## 常见错误

| 错误 | 处理 |
| --- | --- |
| 401 | 检查私有配置与当前有效 token；不要尝试门户 Cookie 或关闭认证 |
| 400 | 按运行服务 Schema 修正字段、时间范围或质量说明 |
| 409 | 阅读逐条 reason，区分版本变化、旧快照、计数下降与幂等键复用 |
| 网络失败 | 保留原计划重试，确认回执和回读结果 |
| 计划摘要/目标不符 | 不修改计划绕过校验；从审阅后的输入生成新计划 |

服务每批事务提交；一个批次冲突则该批无写入，但前面成功批次已提交。客户端回读不仅检查批次，还比较实际记录的日期、次数、主题与标签。
