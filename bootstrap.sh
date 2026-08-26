#!/usr/bin/env bash
set -euo pipefail

repo_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
backup_root="${TMPDIR:-/tmp}/agent-config-backup-$(date +%Y%m%d-%H%M%S)"
apply=false

if [[ "${1:-}" == "--apply" ]]; then
  apply=true
elif [[ $# -gt 0 ]]; then
  echo "Usage: $0 [--apply]" >&2
  exit 2
fi

link_item() {
  local source=$1
  local target=$2

  if [[ -L "$target" ]] && [[ "$(readlink "$target")" == "$source" ]]; then
    echo "OK    $target -> $source"
    return
  fi

  if [[ "$apply" != true ]]; then
    if [[ -e "$target" || -L "$target" ]]; then
      echo "WOULD backup $target and link it to $source"
    else
      echo "WOULD link $target -> $source"
    fi
    return
  fi

  mkdir -p "$(dirname -- "$target")"
  if [[ -e "$target" || -L "$target" ]]; then
    mkdir -p "$backup_root"
    mv "$target" "$backup_root/$(echo "$target" | sed 's#^/##; s#/#__#g')"
  fi
  ln -s "$source" "$target"
  echo "LINK  $target -> $source"
}

link_item "$repo_dir/AGENTS.md" "$HOME/.trae/AGENTS.md"
link_item "$repo_dir/AGENTS.md" "$HOME/.codex/AGENTS.md"

for skill_dir in "$repo_dir"/skills/*; do
  [[ -d "$skill_dir" ]] || continue
  skill_name=$(basename -- "$skill_dir")
  for client_root in .agents .trae .trae-cn .codex .claude; do
    link_item "$skill_dir" "$HOME/$client_root/skills/$skill_name"
  done
done

if [[ "$apply" == true && -d "$backup_root" ]]; then
  echo "Backups: $backup_root"
fi
