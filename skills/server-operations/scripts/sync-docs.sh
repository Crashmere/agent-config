#!/usr/bin/env bash
# Run locally: synchronize shared skill and project documentation from pushed commits to server copies, verifying every file.
# Usage: sync-docs.sh [--check] [--force] [all | shared | <project-name>...]
#   No target is equivalent to all: shared plus every project with an existing docs/SOURCE on the server.
#   --check is read-only: report drift, commits behind local HEAD, and junk files without writing to the server.
#   --force overwrites when a server copy differs from its recorded source; first confirm that live edits were returned to the repository.
# Environment: SYNC_HOST (default: ali), PROJECTS_DIR (directory containing project checkouts; default: ~/ali).
set -euo pipefail

host=${SYNC_HOST:-ali}
projects_dir=${PROJECTS_DIR:-$HOME/ali}
config=$(git -C "$(dirname "$0")" rev-parse --show-toplevel)
shared_prefix=skills/server-operations
check_only=false
force=false
targets=""
failed=""

for arg in "$@"; do
  case $arg in
    --check) check_only=true ;;
    --force) force=true ;;
    -h|--help) sed -n '2,7p' "$0"; exit 0 ;;
    *) targets="$targets $arg" ;;
  esac
done

sha256() { if command -v sha256sum >/dev/null; then sha256sum; else shasum -a 256; fi | cut -c1-64; }
die() { echo "error: $*" >&2; exit 1; }

# Print "<sha256>  <absolute-server-path>". Arguments are repository and commit; read mappings as "<repository-path> <server-path>" from stdin.
manifest() {
  local repo=$1 commit=$2 src dest
  while read -r src dest; do
    git -C "$repo" cat-file -e "$commit:$src" 2>/dev/null || die "$src does not exist in $commit"
    printf '%s  %s\n' "$(git -C "$repo" cat-file blob "$commit:$src" | sha256)" "$dest"
  done
}

remote_manifest() { # Server paths; managed paths contain no spaces.
  ssh "$host" "for f in $*; do if [ -f \"\$f\" ]; then sha256sum \"\$f\"; else echo \"missing  \$f\"; fi; done"
}

# Mapping: shared includes every skill file plus /opt/AGENTS.md and MOTD; projects include AGENTS.md and docs/*.md.
mapping() { # target repo commit
  local target=$1 repo=$2 commit=$3 app f
  if [ "$target" = shared ]; then
    git -C "$repo" ls-tree -r --name-only "$commit" -- "$shared_prefix" | while read -r f; do
      echo "$f /opt/server-context/${f#$shared_prefix/}"
    done
    echo "$shared_prefix/assets/AGENTS.md /opt/AGENTS.md"
    if [ "$host" = vps ]; then
      if git -C "$repo" cat-file -e "$commit:$shared_prefix/assets/server-context-motd.txt" 2>/dev/null; then
        echo "$shared_prefix/assets/server-context-motd.txt /etc/motd.d/30-server-context"
      fi
    else
      echo "$shared_prefix/assets/30-server-context /etc/update-motd.d/30-server-context"
    fi
  else
    app=$(echo "$target" | tr '[:upper:]' '[:lower:]')
    git -C "$repo" ls-tree -r --name-only "$commit" -- AGENTS.md docs | grep -E '^(AGENTS\.md|docs/[^/]+\.md)$' | while read -r f; do
      echo "$f /opt/$app/$f"
    done
  fi
}

sync_target() {
  local target=$1 repo app source_file subdir managed junk url commit old dests remove expected actual
  if [ "$target" = shared ]; then
    repo=$config; source_file=/opt/server-context/SOURCE; subdir=$shared_prefix; managed=$shared_prefix
    junk=/opt/server-context
  else
    repo=$projects_dir/$target; app=$(echo "$target" | tr '[:upper:]' '[:lower:]')
    source_file=/opt/$app/docs/SOURCE; subdir=AGENTS.md,docs; managed="AGENTS.md docs"
    junk="/opt/$app/docs"
    [ -d "$repo/.git" ] || die "checkout for $target not found: $repo"
  fi
  url=$(git -C "$repo" remote get-url origin | sed -e 's#^git@github.com:#https://github.com/#' -e 's#\.git$##')
  git -C "$repo" fetch -q origin
  commit=$(git -C "$repo" rev-parse HEAD)
  local problem=""
  git -C "$repo" merge-base --is-ancestor "$commit" '@{upstream}' || problem="HEAD has not been pushed"
  # shellcheck disable=SC2086
  [ -z "$(git -C "$repo" status --porcelain -- $managed)" ] || problem="${problem:+${problem}; }uncommitted documentation changes"
  if [ -n "$problem" ]; then
    if $check_only; then echo "warn  ${target}: $problem"; else echo "SKIP  ${target}: $problem"; failed="$failed $target"; return; fi
  fi

  old=$(ssh "$host" "sed -n 's/^commit=//p' $source_file 2>/dev/null" || true)
  if [ -n "$old" ]; then
    git -C "$repo" cat-file -e "$old^{commit}" 2>/dev/null || die "$target has no local copy of server-recorded commit $old"
    dests=$(mapping "$target" "$repo" "$old" | cut -d' ' -f2)
    expected=$(mapping "$target" "$repo" "$old" | manifest "$repo" "$old")
    # shellcheck disable=SC2086
    actual=$(remote_manifest $dests)
    if [ "$expected" != "$actual" ]; then
      echo "DRIFT ${target}: server copy differs from recorded commit ${old:0:8}"
      diff <(echo "$expected") <(echo "$actual") || true
      if ! $force; then failed="$failed $target"; return; fi
    fi
  fi
  # A new application's docs directory is created by install -D below.
  # Missing directories are normal on first sync, including in --check mode.
  ssh "$host" "if [ -e $junk ]; then find $junk -name '._*' -type f; fi" | sed "s/^/junk  /"

  if $check_only; then
    if [ "$old" = "$commit" ]; then echo "OK    $target @ ${commit:0:8}"; else echo "BEHIND ${target}: server ${old:0:8}, local ${commit:0:8}"; fi
    return
  fi

  # Remove managed server files that exist in the old commit but not the new commit.
  remove=""
  if [ -n "$old" ]; then
    remove=$(comm -23 <(mapping "$target" "$repo" "$old" | cut -d' ' -f2 | sort) \
                      <(mapping "$target" "$repo" "$commit" | cut -d' ' -f2 | sort) | tr '\n' ' ')
  fi
  mapping "$target" "$repo" "$commit" > "${TMPDIR:-/tmp}/sync-docs-map.$$"
  # Upload a tar whose root/ tree mirrors absolute server paths; install each file remotely.
  (
    set -e
    stage=$(mktemp -d)
    trap 'rm -rf "$stage"' EXIT
    while read -r src dest; do
      mkdir -p "$stage/root$(dirname "$dest")"
      git -C "$repo" cat-file blob "$commit:$src" > "$stage/root$dest"
    done < "${TMPDIR:-/tmp}/sync-docs-map.$$"
    COPYFILE_DISABLE=1 tar --no-xattrs -C "$stage" -cf - root
  ) | ssh "$host" "set -euo pipefail
s=\$(mktemp -d /tmp/sync-docs.XXXXXX); trap 'rm -rf \"\$s\"' EXIT
tar -xf - -C \"\$s\"
cd \"\$s/root\"
find . -type f | while read -r f; do
  dest=\${f#.}; mode=0644
  case \$dest in /opt/server-context/scripts/*|/etc/update-motd.d/*|/opt/server-context/assets/30-server-context) mode=0755 ;; esac
  cmp -s \"\$f\" \"\$dest\" 2>/dev/null && [ \"\$(stat -c %a \"\$dest\")\" = \"\${mode#0}\" ] && continue
  install -D -o root -g root -m \$mode \"\$f\" \"\$dest.sync-tmp\"
  mv -f \"\$dest.sync-tmp\" \"\$dest\"
  echo \"updated \$dest\"
done
for f in $remove; do rm -f -- \"\$f\"; echo \"removed \$f\"; done
find $junk -name '._*' -type f -print -delete | sed 's/^/deleted junk /'
printf 'repository=%s\ncommit=%s\nsubdirectory=%s\nsynced_at=%s\n' '$url' '$commit' '$subdir' \"\$(date -u +%Y-%m-%dT%H:%M:%SZ)\" > $source_file.sync-tmp
chown root:root $source_file.sync-tmp; chmod 0644 $source_file.sync-tmp; mv -f $source_file.sync-tmp $source_file"
  rm -f "${TMPDIR:-/tmp}/sync-docs-map.$$"

  dests=$(mapping "$target" "$repo" "$commit" | cut -d' ' -f2)
  expected=$(mapping "$target" "$repo" "$commit" | manifest "$repo" "$commit")
  # shellcheck disable=SC2086
  actual=$(remote_manifest $dests)
  if [ "$expected" = "$actual" ]; then
    echo "OK    $target @ ${commit:0:8} ($(echo "$dests" | wc -l | tr -d ' ') files match the commit)"
  else
    echo "FAIL  ${target}: post-sync verification differs"; diff <(echo "$expected") <(echo "$actual") || true
    failed="$failed $target"
  fi
}

if [ -z "${targets// /}" ] || [[ " $targets " == *" all "* ]]; then
  targets="shared $(ssh "$host" 'for f in /opt/*/docs/SOURCE; do sed -n "s#^repository=.*/##p" "$f"; done' | tr '\n' ' ')"
fi
for t in $targets; do sync_target "$t"; done
ssh "$host" 'n=$(ls -d /tmp/sync-docs.* 2>/dev/null | wc -l); [ "$n" -eq 0 ] || echo "warning: $n /tmp/sync-docs.* staging directories remain on the server"'
[ -z "$failed" ] || die "incomplete:$failed"
