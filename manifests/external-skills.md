# Externally managed skills

These skills are intentionally not copied into this repository. Install them from their upstream source, then let the corresponding installer manage updates.

| Skills | Source | Install or update |
| --- | --- | --- |
| `lark-*` | `larksuite/cli` | `npx skills add larksuite/cli -g -y` |
| `mole` | `tw93/Mole`, path `.claude/skills/mole` | Use the Trae skill installer |
| `find-skills` | `vercel-labs/skills` | Use the Trae skill installer |
| `bytedcli` | ByteDance-managed distribution | Use the official ByteDance installer/update flow |

Do not commit installed copies here unless they are intentionally forked and maintained as local source.
