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
    <td><a href="./skills/personal-skill-management/SKILL.md">personal-skill-management</a></td>
    <td>整理 Agent 指令，创建和维护个人 Skill，并同步更新本仓库、README、本机接入和 GitHub 版本。</td>
  </tr>
</table>

## 开发环境与软件管理

<table>
  <tr>
    <td><a href="./skills/python-environment/SKILL.md">python-environment</a></td>
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
    <td><a href="./skills/pdf-to-word/SKILL.md">pdf-to-word</a></td>
    <td>以内容质量和可编辑性为优先转换 PDF 为 Word，结合本地 OCR、结构重建与渲染复核，并持续沉淀新经验和通用工具。</td>
  </tr>
  <tr>
    <td><a href="./skills/translate-pdf/SKILL.md">translate-pdf</a></td>
    <td>结合上下文完整翻译 PDF，逐段审校原意、语气与可读性，并验证图文覆盖及排版；基于 wshuyi 的开源技能维护。</td>
  </tr>
  <tr>
    <td><a href="./skills/comfyui-operations/SKILL.md">comfyui-operations</a></td>
    <td>跨 Windows、macOS 和 Linux 安装、运行、维护与排查 ComfyUI，覆盖模型部署、工作流、API、缓存和图像异常。</td>
  </tr>
  <tr>
    <td><a href="./skills/openai-image-cost-report/SKILL.md">openai-image-cost-report</a></td>
    <td>使用 OpenAI Image API 生成或编辑图片，并报告每次调用的费用。</td>
  </tr>
</table>

## 远程操作

<table>
  <tr>
    <td><a href="./skills/server-operations/SKILL.md">server-operations</a></td>
    <td>维护个人 Linux 服务器的共享部署约定、当前主机与应用清单、跨项目架构变更、服务器重建及文档同步；项目细节留在各自 docs。</td>
  </tr>
  <tr>
    <td><a href="./skills/windows-ssh/SKILL.md">windows-ssh</a></td>
    <td>通过 SSH 安全连接、检查和操作远程 Windows 电脑，并处理 OpenSSH、文件传输、编码和命令转义问题。</td>
  </tr>
</table>
