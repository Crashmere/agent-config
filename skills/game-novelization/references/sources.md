# 来源与取舍

本技能按用户的“忠实还原多款游戏主线、贴合原作风格、利用攻略和视频、详略得当”要求重新组织，以独立中文说明实现统一工作流，不要求安装或调用上游技能。于 2026-10-06 核对下列作者仓库，未将其代码或运行环境作为依赖。

| 上游与核对版本 | 采用的部分 | 未采用或调整的部分 |
|---|---|---|
| [jwynia/agent-skills](https://github.com/jwynia/agent-skills/tree/e02ec7e226a6e4f8419fd3b88a1d8e472d421b32) 的 media-adaptation、shared-world | 分析情绪与冲突结构；以来源、事实类别、关联条目维护世界设定 | 不采用更换世界背景、用原创性优先于忠实度的目标；不引入多人审批角色或上游 Deno 脚本 |
| [PenglongHuang/chinese-novelist-skill](https://github.com/PenglongHuang/chinese-novelist-skill/tree/cb6c3e7d0563c6a685e6539ea642642ab98855d7) | 分章规划、写前查前文、人物状态、术语与揭示时机、续写和语言修订 | 不采用固定 10—50 章、每章 3000—5000 字、强制开头高潮/章尾钩子或通用人物重造规则 |
| [zenstory-ai/oh-story-claudecode](https://github.com/zenstory-ai/oh-story-claudecode/tree/87f2e7e223077023e0b0c0796d5704c1b0b02088) 的 story-long-write | 区分规划与正文范围；文件状态追踪；细节须有信息和后果，避免机械情绪动作 | 不采用爽点配额、强制新增阻碍、多 Agent 运行体系、每轮章节上限或复杂脚本事务系统 |
| [Elowwwen/Fanfic-background-assistant](https://github.com/Elowwwen/Fanfic-background-assistant/tree/0b5da382b5f5d0150b406bc66bfbc0c4aaa11e3f) | 事实、推断与作者选择分开；来源核实；逐步维护背景资料 | 仅研究而不写剧情的边界不适合本技能，改为在原作事实内完成小说写作 |

主要查阅文件：

- `jwynia/agent-skills`：`skills/creative/fiction/application/media-adaptation/SKILL.md`、`skills/creative/fiction/application/shared-world/SKILL.md`。
- `PenglongHuang/chinese-novelist-skill`：`SKILL.md`、`references/guides/chapter-guide.md`、`references/guides/character-building.md`。
- `zenstory-ai/oh-story-claudecode`：`skills/story-long-write/SKILL.md`、`skills/story-long-write/references/writing-craft.md`。
- `Elowwwen/Fanfic-background-assistant`：`fanfic-background-assistant/SKILL.md`、`fanfic-background-assistant/references/research-and-risk.md`。

新增的领域约束包括版本与路线隔离、主线事件到章节的覆盖表、角色知识与读者揭示双重边界、游戏机制小说化、原作风格档案、视频场景证据与详略决策。按用户要求，最终作品只交付小说正文；上游的永久资料库改为当前任务的独立临时工作资料，不随作品交付。维护时以这些职责和用户当前要求为准，不因上游更新重新带入相冲突的套路或依赖。

保留的许可及出处见 [第三方许可](../THIRD_PARTY_NOTICES.md)。这些来源是工作流的来源，不是未来某款游戏剧情的证据；具体改编必须另建项目资料。
