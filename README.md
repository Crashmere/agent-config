# agent-config

个人维护的全局 Agent 指令与 Skills。

## 全局指令

<table>
  <tr>
    <td><a href="./AGENTS.md">AGENTS.md</a></td>
    <td>全局行为约束，包括 Python 环境安全、软件安装、指令管理和通用工作规范。</td>
  </tr>
</table>

## 配置与 Skill 维护

<table>
  <tr>
    <td><a href="./skills/personal-skill-management/SKILL.md">personal-skill-management</a><br><a href="./skills/personal-skill-management/references/maintenance.md">maintenance.md</a> · <a href="./skills/personal-skill-management/references/repository-workflow.md">repository-workflow.md</a> · <a href="./skills/personal-skill-management/scripts/sync-skill-links.sh">sync-skill-links.sh</a></td>
    <td>整理 Agent 指令，创建和维护个人 Skill，并同步更新本仓库、README、本机接入和 GitHub 版本。</td>
  </tr>
</table>

## 开发环境与软件管理

<table>
  <tr>
    <td><a href="./skills/python-environment/SKILL.md">python-environment</a><br><a href="./skills/python-environment/references/package-indexes.md">package-indexes.md</a> · <a href="./skills/python-environment/references/windows-native-imports.md">windows-native-imports.md</a></td>
    <td>管理项目级 Python 环境与依赖，并排查解释器、包导入及 Windows 原生模块或 DLL 问题。</td>
  </tr>
  <tr>
    <td><a href="./skills/software-installation/SKILL.md">software-installation</a></td>
    <td>选择合适的软件安装与卸载方式；在 macOS 上根据具体软件协调官方卸载流程与 Mole，并使用 Mole 辅助空间清理。</td>
  </tr>
</table>

## 应用工作流

<table>
  <tr>
    <td><a href="./skills/comfyui-operations/SKILL.md">comfyui-operations</a><br><a href="./skills/comfyui-operations/references/baselines.md">baselines.md</a> · <a href="./skills/comfyui-operations/references/platforms.md">platforms.md</a> · <a href="./skills/comfyui-operations/references/troubleshooting.md">troubleshooting.md</a><br><a href="./skills/comfyui-operations/scripts/inspect_workflow.py">inspect_workflow.py</a> · <a href="./skills/comfyui-operations/scripts/run_prompt.py">run_prompt.py</a> · <a href="./skills/comfyui-operations/tests/test_run_prompt.py">test_run_prompt.py</a></td>
    <td>跨 Windows、macOS 和 Linux 安装、运行、维护与排查 ComfyUI，覆盖模型部署、工作流、API、缓存和图像异常。</td>
  </tr>
  <tr>
    <td><a href="./skills/openai-image-cost-report/SKILL.md">openai-image-cost-report</a><br><a href="./skills/openai-image-cost-report/references/pricing-notes.md">pricing-notes.md</a> · <a href="./skills/openai-image-cost-report/scripts/openai_image_with_cost.py">openai_image_with_cost.py</a> · <a href="./skills/openai-image-cost-report/tests/test_openai_image_with_cost.py">test_openai_image_with_cost.py</a></td>
    <td>使用 OpenAI Image API 生成或编辑图片，并报告每次调用的费用。</td>
  </tr>
</table>

## 远程操作

<table>
  <tr>
    <td><a href="./skills/windows-ssh/SKILL.md">windows-ssh</a><br><a href="./skills/windows-ssh/references/windows-openssh.md">windows-openssh.md</a> · <a href="./skills/windows-ssh/scripts/inspect-windows.ps1">inspect-windows.ps1</a></td>
    <td>通过 SSH 安全连接、检查和操作远程 Windows 电脑，并处理 OpenSSH、文件传输、编码和命令转义问题。</td>
  </tr>
</table>
