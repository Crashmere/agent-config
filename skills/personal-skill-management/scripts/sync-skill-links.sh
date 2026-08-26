#!/usr/bin/env bash

set -eu

usage() {
  cat <<'EOF'
Usage: sync-skill-links.sh [--apply]

Check links from supported agent clients to skills in this repository.
The default mode only reports changes. --apply creates missing links and
client skill directories, but never overwrites an existing path.
EOF
}

apply=false
case "${1:-}" in
  "") ;;
  --apply) apply=true ;;
  -h|--help) usage; exit 0 ;;
  *) usage >&2; exit 64 ;;
esac

if [ "$#" -gt 1 ]; then
  usage >&2
  exit 64
fi

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
skill_dir=$(CDPATH= cd -- "$script_dir/.." && pwd -P)
skills_dir=$(CDPATH= cd -- "$skill_dir/.." && pwd -P)

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

printf '%s\n' "Repository skills: $skills_dir"
if [ "$apply" = true ]; then
  printf '%s\n' "Mode: apply"
else
  printf '%s\n' "Mode: report only (use --apply to create missing links)"
fi

for skill_file in "$skills_dir"/*/SKILL.md; do
  [ -f "$skill_file" ] || continue
  source_dir=$(dirname "$skill_file")
  skill_name=$(basename "$source_dir")

  while IFS= read -r client_root; do
    [ -n "$client_root" ] || continue
    target=$client_root/$skill_name
    checked=$((checked + 1))

    if [ -L "$target" ]; then
      resolved=$(resolve_link "$target")
      if [ "$resolved" = "$source_dir" ]; then
        continue
      fi
      printf 'CONFLICT %s -> %s (expected %s)\n' "$target" "$(readlink "$target")" "$source_dir"
      conflicts=$((conflicts + 1))
    elif [ -e "$target" ]; then
      printf 'CONFLICT %s exists and is not a symlink (expected %s)\n' "$target" "$source_dir"
      conflicts=$((conflicts + 1))
    elif [ "$apply" = true ]; then
      mkdir -p "$client_root"
      ln -s "$source_dir" "$target"
      printf 'CREATED  %s -> %s\n' "$target" "$source_dir"
      created=$((created + 1))
    else
      printf 'MISSING  %s -> %s\n' "$target" "$source_dir"
      missing=$((missing + 1))
    fi
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

printf 'Summary: checked=%s created=%s missing=%s conflicts=%s stale=%s\n' \
  "$checked" "$created" "$missing" "$conflicts" "$stale"

if [ "$conflicts" -gt 0 ]; then
  exit 2
fi
