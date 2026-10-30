#!/usr/bin/env bash
# Compatibility entry point: backup now always includes both NAS and VPS in one NAS-built package.
set -euo pipefail
exec bash "$(dirname "$0")/backup-system.sh" "${1:-vps}"
