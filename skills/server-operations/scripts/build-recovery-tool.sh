#!/usr/bin/env bash
# Build on the maintenance computer; never install a Go toolchain on NAS/VPS.
set -euo pipefail
[[ $# == 1 ]] || { echo "Usage: $0 <absolute-output-path>" >&2; exit 64; }
[[ $1 == /* ]] || { echo "Output path must be absolute." >&2; exit 64; }
source_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/recovery-tool" && pwd)
cd "$source_dir"
CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -trimpath -o "$1" .
