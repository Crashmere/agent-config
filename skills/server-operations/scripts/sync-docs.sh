#!/usr/bin/env bash
# 在本地运行：把已推送提交中的共享技能和项目文档同步到服务器副本，并逐文件校验。
# 用法：sync-docs.sh [--check] [--force] [all | shared | <项目名>...]
#   不带目标等于 all：shared 加上服务器已有 docs/SOURCE 的全部项目。
#   --check 只读：报告漂移、是否落后于本地提交、垃圾文件，不写服务器。
#   --force 服务器副本与记录的来源不一致时仍覆盖（先确认现场修改已回写仓库）。
# 环境变量：SYNC_HOST（默认 ali）、PROJECTS_DIR（项目 checkout 所在目录，默认 ~/ali）。
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

# 打印 "<sha256>  <服务器绝对路径>"；参数为 repo commit，映射从标准输入读取 "<仓库内路径> <服务器路径>"。
manifest() {
  local repo=$1 commit=$2 src dest
  while read -r src dest; do
    git -C "$repo" cat-file -e "$commit:$src" 2>/dev/null || die "$commit 中不存在 $src"
    printf '%s  %s\n' "$(git -C "$repo" cat-file blob "$commit:$src" | sha256)" "$dest"
  done
}

remote_manifest() { # 服务器路径...（受管理路径不含空格）
  ssh "$host" "for f in $*; do if [ -f \"\$f\" ]; then sha256sum \"\$f\"; else echo \"missing  \$f\"; fi; done"
}

# 映射：shared 为技能目录全部文件 + /opt/AGENTS.md + MOTD；项目为 AGENTS.md 与 docs/*.md。
mapping() { # target repo commit
  local target=$1 repo=$2 commit=$3 app f
  if [ "$target" = shared ]; then
    git -C "$repo" ls-tree -r --name-only "$commit" -- "$shared_prefix" | while read -r f; do
      echo "$f /opt/server-context/${f#$shared_prefix/}"
    done
    echo "$shared_prefix/assets/AGENTS.md /opt/AGENTS.md"
    echo "$shared_prefix/assets/30-server-context /etc/update-motd.d/30-server-context"
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
    [ -d "$repo/.git" ] || die "找不到 $target 的 checkout：$repo"
  fi
  url=$(git -C "$repo" remote get-url origin | sed -e 's#^git@github.com:#https://github.com/#' -e 's#\.git$##')
  git -C "$repo" fetch -q origin
  commit=$(git -C "$repo" rev-parse HEAD)
  local problem=""
  git -C "$repo" merge-base --is-ancestor "$commit" '@{upstream}' || problem="HEAD 尚未推送"
  # shellcheck disable=SC2086
  [ -z "$(git -C "$repo" status --porcelain -- $managed)" ] || problem="${problem:+${problem}；}有未提交的文档修改"
  if [ -n "$problem" ]; then
    if $check_only; then echo "warn  ${target}：$problem"; else echo "SKIP  ${target}：$problem"; failed="$failed $target"; return; fi
  fi

  old=$(ssh "$host" "sed -n 's/^commit=//p' $source_file 2>/dev/null" || true)
  if [ -n "$old" ]; then
    git -C "$repo" cat-file -e "$old^{commit}" 2>/dev/null || die "$target 本地没有服务器记录的提交 $old"
    dests=$(mapping "$target" "$repo" "$old" | cut -d' ' -f2)
    expected=$(mapping "$target" "$repo" "$old" | manifest "$repo" "$old")
    # shellcheck disable=SC2086
    actual=$(remote_manifest $dests)
    if [ "$expected" != "$actual" ]; then
      echo "DRIFT ${target}：服务器副本与记录的 ${old:0:8} 不一致"
      diff <(echo "$expected") <(echo "$actual") || true
      if ! $force; then failed="$failed $target"; return; fi
    fi
  fi
  ssh "$host" "find $junk -name '._*' -type f" | sed "s/^/junk  /"

  if $check_only; then
    if [ "$old" = "$commit" ]; then echo "OK    $target @ ${commit:0:8}"; else echo "BEHIND ${target}：服务器 ${old:0:8}，本地 ${commit:0:8}"; fi
    return
  fi

  # 旧提交中有、新提交中没有的受管理文件在服务器上删除。
  remove=""
  if [ -n "$old" ]; then
    remove=$(comm -23 <(mapping "$target" "$repo" "$old" | cut -d' ' -f2 | sort) \
                      <(mapping "$target" "$repo" "$commit" | cut -d' ' -f2 | sort) | tr '\n' ' ')
  fi
  mapping "$target" "$repo" "$commit" > "${TMPDIR:-/tmp}/sync-docs-map.$$"
  # 上传 tar：每个文件按服务器绝对路径打包在 root/ 下，由远端逐个安装。
  (
    set -e
    stage=$(mktemp -d)
    trap 'rm -rf "$stage"' EXIT
    while read -r src dest; do
      mkdir -p "$stage/root$(dirname "$dest")"
      git -C "$repo" cat-file blob "$commit:$src" > "$stage/root$dest"
    done < "${TMPDIR:-/tmp}/sync-docs-map.$$"
    COPYFILE_DISABLE=1 tar -C "$stage" -cf - root
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
    echo "OK    $target @ ${commit:0:8}（$(echo "$dests" | wc -l | tr -d ' ') 个文件与提交一致）"
  else
    echo "FAIL  ${target}：同步后校验不一致"; diff <(echo "$expected") <(echo "$actual") || true
    failed="$failed $target"
  fi
}

if [ -z "${targets// /}" ] || [[ " $targets " == *" all "* ]]; then
  targets="shared $(ssh "$host" 'for f in /opt/*/docs/SOURCE; do sed -n "s#^repository=.*/##p" "$f"; done' | tr '\n' ' ')"
fi
for t in $targets; do sync_target "$t"; done
ssh "$host" 'n=$(ls -d /tmp/sync-docs.* 2>/dev/null | wc -l); [ "$n" -eq 0 ] || echo "warning: 服务器残留 $n 个 /tmp/sync-docs.* 暂存目录"'
[ -z "$failed" ] || die "未完成：$failed"
