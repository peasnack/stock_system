#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPORT_DIR="$ROOT_DIR/data/reports"
DECISION_DIR="$ROOT_DIR/data/decision"
CONTEXT_DIR="$ROOT_DIR/data/context"

latest_file() {
  local dir="$1"
  local suffix="$2"
  find "$dir" -maxdepth 1 -type f -name "*$suffix" -printf "%T@ %p\n" 2>/dev/null \
    | sort -nr \
    | awk 'NR == 1 {sub(/^[^ ]+ /, ""); print}'
}

REPORT_FILE="$(latest_file "$REPORT_DIR" "_report.md")"
if [[ -z "${REPORT_FILE:-}" ]]; then
  echo "No report found under $REPORT_DIR" >&2
  exit 1
fi

if [[ "${1:-}" == "--print" ]]; then
  cat "$REPORT_FILE"
  exit 0
fi

if ! command -v codex >/dev/null 2>&1; then
  echo "codex CLI not found in PATH. Use --print and paste the report into Codex manually." >&2
  exit 1
fi

CONTEXT_FILE="$(latest_file "$CONTEXT_DIR" "_market_context.json")"
DECISION_FILE="$(latest_file "$DECISION_DIR" "_decision_guarded.json")"

{
  echo "# Latest A-share decision report"
  echo
  echo "Report file: $REPORT_FILE"
  echo
  cat "$REPORT_FILE"
  if [[ -n "${DECISION_FILE:-}" ]]; then
    echo
    echo "# Guarded decision JSON"
    echo
    cat "$DECISION_FILE"
  fi
  if [[ -n "${CONTEXT_FILE:-}" ]]; then
    echo
    echo "# Market context JSON"
    echo
    cat "$CONTEXT_FILE"
  fi
} | codex exec --sandbox read-only \
  "你是我的A股投资系统复盘助手。请阅读输入的最新报告、二次风控JSON和market_context，输出：1. 今日结论是否清晰；2. 是否存在数据缺口或风控矛盾；3. 每只股票的关键风险；4. 明天需要关注的触发条件。不要建议自动下单。"
