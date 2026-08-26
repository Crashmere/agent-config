#!/usr/bin/env bash
set -euo pipefail

repo_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
failed=0

check_link() {
  local source=$1
  local target=$2
  if [[ -L "$target" ]] && [[ "$(readlink "$target")" == "$source" ]]; then
    echo "OK    $target"
  else
    echo "FAIL  $target (expected link to $source)"
    failed=1
  fi
}

check_link "$repo_dir/AGENTS.md" "$HOME/.trae/AGENTS.md"
check_link "$repo_dir/AGENTS.md" "$HOME/.codex/AGENTS.md"

for skill_dir in "$repo_dir"/skills/*; do
  [[ -d "$skill_dir" ]] || continue
  skill_name=$(basename -- "$skill_dir")
  [[ -f "$skill_dir/SKILL.md" ]] || {
    echo "FAIL  $skill_dir/SKILL.md is missing"
    failed=1
  }
  for client_root in .agents .trae .trae-cn .codex .claude; do
    check_link "$skill_dir" "$HOME/$client_root/skills/$skill_name"
  done
done

if command -v git >/dev/null 2>&1; then
  git -C "$repo_dir" status --short --branch
fi

exit "$failed"
