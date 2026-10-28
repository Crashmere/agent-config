#!/usr/bin/env bash

set -eu

usage() {
  cat <<'EOF'
Usage: sync-skill-links.sh [--apply] [--instructions-only]

Check links from supported agent clients to skills and global instructions.
The default mode only reports changes. --apply creates missing links and
client directories, but never overwrites an existing path.
--instructions-only checks global instruction links without touching skills.
EOF
}

apply=false
instructions_only=false
for option in "$@"; do
  case "$option" in
    --apply) apply=true ;;
    --instructions-only) instructions_only=true ;;
    -h|--help) usage; exit 0 ;;
    *) usage >&2; exit 64 ;;
  esac
done

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
skill_dir=$(CDPATH= cd -- "$script_dir/.." && pwd -P)
skills_dir=$(CDPATH= cd -- "$skill_dir/.." && pwd -P)
repository_root=$(CDPATH= cd -- "$skills_dir/.." && pwd -P)

client_roots="
${SKILL_LINK_HOME:-$HOME}/.agents/skills
${SKILL_LINK_HOME:-$HOME}/.trae/skills
${SKILL_LINK_HOME:-$HOME}/.trae-cn/skills
${SKILL_LINK_HOME:-$HOME}/.codex/skills
${SKILL_LINK_HOME:-$HOME}/.claude/skills
"

checked=0
created=0
missing=0
conflicts=0
stale=0

resolve_link() {
  link_path=$1
  link_value=$(readlink "$link_path") || return 1
  case "$link_value" in
    /*) candidate=$link_value ;;
    *) candidate=$(dirname "$link_path")/$link_value ;;
  esac

  candidate_dir=$(dirname "$candidate")
  candidate_name=$(basename "$candidate")
  if resolved_dir=$(CDPATH= cd -- "$candidate_dir" 2>/dev/null && pwd -P); then
    printf '%s/%s\n' "$resolved_dir" "$candidate_name"
  else
    printf '%s\n' "$candidate"
  fi
}

sync_link() {
  local link_source=$1
  local link_target=$2
  local resolved
  checked=$((checked + 1))

  if [ -L "$link_target" ]; then
    resolved=$(resolve_link "$link_target")
    if [ "$resolved" = "$link_source" ]; then
      return
    fi
    printf 'CONFLICT %s -> %s (expected %s)\n' "$link_target" "$(readlink "$link_target")" "$link_source"
    conflicts=$((conflicts + 1))
  elif [ -e "$link_target" ]; then
    printf 'CONFLICT %s exists and is not a symlink (expected %s)\n' "$link_target" "$link_source"
    conflicts=$((conflicts + 1))
  elif [ "$apply" = true ]; then
    mkdir -p "$(dirname "$link_target")"
    ln -s "$link_source" "$link_target"
    printf 'CREATED  %s -> %s\n' "$link_target" "$link_source"
    created=$((created + 1))
  else
    printf 'MISSING  %s -> %s\n' "$link_target" "$link_source"
    missing=$((missing + 1))
  fi
}

printf '%s\n' "Repository skills: $skills_dir"
printf '%s\n' "Global instructions: $repository_root/AGENTS.md"
if [ "$apply" = true ]; then
  printf '%s\n' "Mode: apply"
else
  printf '%s\n' "Mode: report only (use --apply to create missing links)"
fi

if [ "$instructions_only" = false ]; then
  for skill_file in "$skills_dir"/*/SKILL.md; do
    [ -f "$skill_file" ] || continue
    source_dir=$(dirname "$skill_file")
    skill_name=$(basename "$source_dir")

    while IFS= read -r client_root; do
      [ -n "$client_root" ] || continue
      sync_link "$source_dir" "$client_root/$skill_name"
    done <<EOF
$client_roots
EOF
  done

  while IFS= read -r client_root; do
    [ -d "$client_root" ] || continue
    for target in "$client_root"/*; do
      [ -L "$target" ] || continue
      resolved=$(resolve_link "$target")
      case "$resolved" in
        "$skills_dir"/*)
          if [ ! -f "$resolved/SKILL.md" ]; then
            printf 'STALE    %s -> %s (review manually)\n' "$target" "$(readlink "$target")"
            stale=$((stale + 1))
          fi
          ;;
      esac
    done
  done <<EOF
$client_roots
EOF
fi

for client in .trae .codex; do
  sync_link "$repository_root/AGENTS.md" "${SKILL_LINK_HOME:-$HOME}/$client/AGENTS.md"
done

printf 'Summary: checked=%s created=%s missing=%s conflicts=%s stale=%s\n' \
  "$checked" "$created" "$missing" "$conflicts" "$stale"

if [ "$conflicts" -gt 0 ]; then
  exit 2
fi
