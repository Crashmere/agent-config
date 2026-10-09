# 来源与取舍

本技能按用户的“忠实还原多款游戏主线、贴合原作风格、利用攻略和视频、详略得当”要求重新组织，以独立中文说明实现统一工作流，不要求安装或调用上游技能。于 2026-10-06 核对下列作者仓库，未将其代码或运行环境作为依赖。

| 上游与核对版本 | 采用的部分 | 未采用或调整的部分 |
|---|---|---|
| [jwynia/agent-skills](https://github.com/jwynia/agent-skills/tree/e02ec7e226a6e4f8419fd3b88a1d8e472d421b32) 的 media-adaptation、shared-world、prose-style | 分析情绪与冲突结构；以来源、事实类别、关联条目维护世界设定；分层诊断文字平淡、修饰过度、节奏单调与声音漂移，区分有意风格和机械规则 | 不采用更换世界背景或原创性优先于忠实度；将 prose-style 仅诊断的定位改为本技能内的诊断与修订，不生成永久报告，不引入多人审批或上游 Deno 脚本 |
| [PenglongHuang/chinese-novelist-skill](https://github.com/PenglongHuang/chinese-novelist-skill/tree/cb6c3e7d0563c6a685e6539ea642642ab98855d7) | 分章规划、写前查前文、人物状态、术语与揭示时机、续写和语言修订 | 不采用固定 10—50 章、每章 3000—5000 字、强制开头高潮/章尾钩子或通用人物重造规则 |
| [zenstory-ai/oh-story-claudecode](https://github.com/zenstory-ai/oh-story-claudecode/tree/87f2e7e223077023e0b0c0796d5704c1b0b02088) 的 story-long-write | 区分规划与正文范围；文件状态追踪；细节须有信息和后果，避免机械情绪动作 | 不采用爽点配额、强制新增阻碍、多 Agent 运行体系、每轮章节上限或复杂脚本事务系统 |
| 同版本的 [story-deslop](https://github.com/zenstory-ai/oh-story-claudecode/blob/87f2e7e223077023e0b0c0796d5704c1b0b02088/skills/story-deslop/SKILL.md) | 按作品文风裁决；保护伏笔与剧情功能；诊断套话、重复动作、情绪空转、节奏、对白、章尾升华和解释腔，再局部修订 | 将网文默认口语改为原作风格优先；不采用禁词/标点清零、句长与删减比例指标、分级 Gate、脚本与子代理依赖、对照报告或跨书作者记忆 |
| [op7418/Humanizer-zh](https://github.com/op7418/Humanizer-zh/blob/f4518a8eab97b8bfebc66a89d34320a89bef6930/SKILL.md) | 保留信息、否定、条件和确定程度；匹配已有声音；模式是上下文线索；少改有效、好段落可不改，交付最终文本 | 将文章编辑方法用于游戏小说；不以虚构题材为由扩大润色的创作权限；不照搬全部 31 类或套用说明文语气，检查记录不随小说交付 |
| [Elowwwen/Fanfic-background-assistant](https://github.com/Elowwwen/Fanfic-background-assistant/tree/0b5da382b5f5d0150b406bc66bfbc0c4aaa11e3f) | 事实、推断与作者选择分开；来源核实；逐步维护背景资料 | 仅研究而不写剧情的边界不适合本技能，改为在原作事实内完成小说写作 |

主要查阅文件：

- `jwynia/agent-skills`：`skills/creative/fiction/application/media-adaptation/SKILL.md`、`skills/creative/fiction/application/shared-world/SKILL.md`、`skills/creative/fiction/craft/prose-style/SKILL.md`。
- `PenglongHuang/chinese-novelist-skill`：`SKILL.md`、`references/guides/chapter-guide.md`、`references/guides/character-building.md`。
- `zenstory-ai/oh-story-claudecode`：`skills/story-long-write/SKILL.md`、`skills/story-long-write/references/writing-craft.md`、`skills/story-deslop/SKILL.md`、`skills/story-deslop/references/style-resolution.md`、`skills/story-deslop/references/deslop-gates.md`。
- `op7418/Humanizer-zh`：`SKILL.md`（元数据 revision 为 `2026-09-23`）。
- `Elowwwen/Fanfic-background-assistant`：`fanfic-background-assistant/SKILL.md`、`fanfic-background-assistant/references/research-and-risk.md`。

新增的领域约束包括版本与路线隔离、主线事件到章节的覆盖表、角色知识与读者揭示双重边界、游戏机制小说化、原作风格档案、视频场景证据与详略决策。去模板化方法统一写在 `prose-revision.md`，由写作和审校共用；将保护判断强度落实到角色误信、猜测、承诺和观察时点，避免润色改变剧情。示例为本技能自行编写的教学片段。

场景与转场展开、在原动作位置扩写，以及扩写后对空间、持物、知情和段落指代的检查，来自实际长篇改稿中反复出现的问题。后续改稿又补入从整体阅读效果选择修订层次、保留记录背后的人物处境、核对回忆与呼应，以及比较新旧文字的实际效果。再后来的续修补入新读者理解断点（名称晚于事物、动机只在玩家脑中、呼应缺铺垫、回顾叙述泄露后来的知识、跨章称呼漂移、游戏外语汇）、攻略感的成因与全书层面的句式惯性，以及续修基线比对、外部文档写回和交接说明的流程。这些经验用于启发判断，不构成穷尽的写作清单；不绑定某部作品的视角、章数、篇幅、意象或游戏机制，也不以改动量作为质量指标。

按用户要求，最终作品只交付小说正文；上游的永久资料库与诊断报告改为当前任务按需使用的独立临时记录，不随作品交付。维护时以这些职责和用户当前要求为准，不因上游更新重新带入相冲突的套路或依赖。

保留的许可及出处见 [第三方许可](../THIRD_PARTY_NOTICES.md)。这些来源是工作流的来源，不是未来某款游戏剧情的证据；具体改编必须另建项目资料。
