#!/usr/bin/env bash
# Fix: ~/.config is owned by root on some Macs, so gh cannot save auth.
# This script uses a user-writable config dir instead.

set -euo pipefail
export GH_CONFIG_DIR="${GH_CONFIG_DIR:-$HOME/.local/gh}"
mkdir -p "$GH_CONFIG_DIR"

echo "Using GH_CONFIG_DIR=$GH_CONFIG_DIR"
echo ""

if ! gh auth status &>/dev/null; then
  echo "Run GitHub login (browser device flow)..."
  gh auth login -h github.com -p https -w
fi

gh auth status
echo ""

cd "$(dirname "$0")/.."
if git remote get-url origin &>/dev/null; then
  echo "Remote origin already set."
  git push -u origin main
else
  echo "Creating repo and pushing..."
  gh repo create vpeetla-ai/loop-engine-agent-platform \
    --public \
    --source=. \
    --remote=origin \
    --push \
    --description "Self-improving agent harness — LangGraph repo fix loop with PR workflow"
fi

echo ""
echo "Done: https://github.com/vpeetla-ai/loop-engine-agent-platform"
