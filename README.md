# agent-config

Private, version-controlled source for global agent instructions and personally maintained skills. Runtime state, credentials, caches, and third-party installed copies do not belong in this repository.

## Layout

```text
AGENTS.md                    Shared global instructions
skills/<name>/SKILL.md       Personally maintained skills
manifests/                   Sources for externally managed skills
bootstrap.sh                 Preview or install local symlinks
doctor.sh                    Verify the installed links
```

## Install on macOS or Linux

Clone the repository into the home directory:

```bash
git clone https://github.com/Crashmere/agent-config.git ~/agent-config
cd ~/agent-config
./bootstrap.sh
./bootstrap.sh --apply
./doctor.sh
```

Without `--apply`, `bootstrap.sh` is a dry run. During an applied run, existing targets are moved to a timestamped temporary backup before links are created.

The shared `AGENTS.md` is linked to both `~/.trae/AGENTS.md` and `~/.codex/AGENTS.md`. Each repository-owned skill is linked into the user skill roots for Agents, Trae, Trae CN, Codex, and Claude.

After deployment, restart the relevant client. In TraeX, use `/status` to confirm the global instructions and `/skills` to confirm skill discovery.

## Updating

```bash
cd ~/agent-config
git pull --ff-only
./bootstrap.sh --apply
./doctor.sh
```

Edit shared configuration in this repository, commit it, and push it normally. Do not edit generated links as if they were separate copies.

## External skills

Official and third-party skills remain installer-managed. Their sources and reinstall commands are documented in `manifests/external-skills.md`. This avoids duplicated upstream code and prevents Git from fighting the package installer.

## Security

Keep this repository private. Never commit API keys, tokens, cookies, authentication files, chat history, memories, logs, SQLite databases, plugin caches, or machine-specific runtime state. A private GitHub repository is version control, not a secret store.
