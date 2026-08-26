# agent-config

个人维护的全局 Agent 指令与 Skills。

## 现有内容

- [AGENTS.md](./AGENTS.md)：全局行为约束，包括 Python 环境安全、软件安装、指令管理和通用工作规范。
- [windows-ssh](./skills/windows-ssh/SKILL.md)：通过 SSH 安全连接、检查和操作远程 Windows 电脑，并处理 OpenSSH、文件传输、编码和命令转义问题。
- [openai-image-cost-report](./skills/openai-image-cost-report/SKILL.md)：使用 OpenAI Image API 生成或编辑图片，并报告每次调用的费用。
- [personal-skill-management](./skills/personal-skill-management/SKILL.md)：整理 Agent 指令，创建和维护个人 Skill，并同步更新本仓库、README、本机接入和 GitHub 版本。
- [python-environment](./skills/python-environment/SKILL.md)：管理项目级 Python 虚拟环境、依赖安装和解释器问题。
- [software-installation](./skills/software-installation/SKILL.md)：选择合适的软件安装与卸载方式；在 macOS 上根据具体软件协调官方卸载流程与 Mole，并使用 Mole 辅助空间清理。
