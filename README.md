# agent-config

个人维护的全局 Agent 指令与 Skills。

## 全局指令

| 文件 | 介绍 |
| --- | --- |
| [AGENTS.md](./AGENTS.md) | 全局行为约束，包括 Python 环境安全、软件安装、指令管理和通用工作规范。 |

## 配置与 Skill 维护

| Skill | 介绍 | 其他文件 |
| --- | --- | --- |
| [personal-skill-management](./skills/personal-skill-management/SKILL.md) | 整理 Agent 指令，创建和维护个人 Skill，并同步更新本仓库、README、本机接入和 GitHub 版本。 | [OpenAI 元数据](./skills/personal-skill-management/agents/openai.yaml)<br>[维护与故障修正](./skills/personal-skill-management/references/maintenance.md)<br>[仓库工作流](./skills/personal-skill-management/references/repository-workflow.md)<br>[Skill 链接同步脚本](./skills/personal-skill-management/scripts/sync-skill-links.sh) |

## 开发环境与软件管理

| Skill | 介绍 | 其他文件 |
| --- | --- | --- |
| [python-environment](./skills/python-environment/SKILL.md) | 管理项目级 Python 环境与依赖，并排查解释器、包导入及 Windows 原生模块或 DLL 问题。 | [OpenAI 元数据](./skills/python-environment/agents/openai.yaml)<br>[Python 包索引与镜像](./skills/python-environment/references/package-indexes.md)<br>[Windows 原生模块导入排查](./skills/python-environment/references/windows-native-imports.md) |
| [software-installation](./skills/software-installation/SKILL.md) | 选择合适的软件安装与卸载方式；在 macOS 上根据具体软件协调官方卸载流程与 Mole，并使用 Mole 辅助空间清理。 | [OpenAI 元数据](./skills/software-installation/agents/openai.yaml) |

## 应用工作流

| Skill | 介绍 | 其他文件 |
| --- | --- | --- |
| [comfyui-operations](./skills/comfyui-operations/SKILL.md) | 跨 Windows、macOS 和 Linux 安装、运行、维护与排查 ComfyUI，覆盖模型部署、工作流、API、缓存和图像异常。 | [OpenAI 元数据](./skills/comfyui-operations/agents/openai.yaml)<br>[已知良好基线](./skills/comfyui-operations/references/baselines.md)<br>[平台说明](./skills/comfyui-operations/references/platforms.md)<br>[故障排查](./skills/comfyui-operations/references/troubleshooting.md)<br>[工作流检查脚本](./skills/comfyui-operations/scripts/inspect_workflow.py)<br>[API 工作流运行脚本](./skills/comfyui-operations/scripts/run_prompt.py)<br>[运行脚本测试](./skills/comfyui-operations/tests/test_run_prompt.py) |
| [openai-image-cost-report](./skills/openai-image-cost-report/SKILL.md) | 使用 OpenAI Image API 生成或编辑图片，并报告每次调用的费用。 | [OpenAI 元数据](./skills/openai-image-cost-report/agents/openai.yaml)<br>[定价说明](./skills/openai-image-cost-report/references/pricing-notes.md)<br>[图片生成与费用报告脚本](./skills/openai-image-cost-report/scripts/openai_image_with_cost.py)<br>[费用报告脚本测试](./skills/openai-image-cost-report/tests/test_openai_image_with_cost.py) |

## 远程操作

| Skill | 介绍 | 其他文件 |
| --- | --- | --- |
| [windows-ssh](./skills/windows-ssh/SKILL.md) | 通过 SSH 安全连接、检查和操作远程 Windows 电脑，并处理 OpenSSH、文件传输、编码和命令转义问题。 | [OpenAI 元数据](./skills/windows-ssh/agents/openai.yaml)<br>[Windows OpenSSH 配置](./skills/windows-ssh/references/windows-openssh.md)<br>[Windows 检查脚本](./skills/windows-ssh/scripts/inspect-windows.ps1) |
