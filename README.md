# agent-config

个人维护的全局 Agent 指令与 Skills。

## 现有内容

- [AGENTS.md](./AGENTS.md)：全局行为约束，包括 Python 环境安全、软件安装、指令管理和通用工作规范。
- [instruction-management](./skills/instruction-management/SKILL.md)：整理 Agent 指令，判断内容应放入 `AGENTS.md` 还是 Skill，并处理重复或冲突。
- [openai-image-cost-report](./skills/openai-image-cost-report/SKILL.md)：使用 OpenAI Image API 生成或编辑图片，并报告每次调用的费用。
- [personal-skill-management](./skills/personal-skill-management/SKILL.md)：创建和维护个人 Skill，并同步更新本仓库、README、本机接入和 GitHub 版本。
- [python-environment](./skills/python-environment/SKILL.md)：管理项目级 Python 虚拟环境、依赖安装和解释器问题。
- [software-installation](./skills/software-installation/SKILL.md)：选择合适的软件来源和安装方式，执行安装、升级、卸载及结果验证。
