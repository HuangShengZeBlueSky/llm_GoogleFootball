#!/usr/bin/env bash
set -euo pipefail

ENV_NAME="grf_llm"
EPISODES="${1:-5}"
INTERVAL="${2:-5}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if ! command -v conda >/dev/null 2>&1; then
  echo "[ERROR] 未检测到 conda，请先安装 Miniconda/Anaconda。"
  exit 1
fi

eval "$(conda shell.bash hook)"
conda activate "$ENV_NAME"

if [[ ! -f ".env" ]]; then
  echo "[ERROR] 未找到 .env，请先执行: cp .env.example .env 并填写 API 配置。"
  exit 1
fi

mkdir -p logs grf_logs

# 服务器无图形界面时建议使用 dummy 驱动
export SDL_VIDEODRIVER="${SDL_VIDEODRIVER:-dummy}"
export LD_LIBRARY_PATH="$CONDA_PREFIX/lib:${LD_LIBRARY_PATH:-}"
export PYTHONUNBUFFERED=1

python llm_football_agent/run_game.py \
  --config configs/config.yaml \
  --episodes "$EPISODES" \
  --interval "$INTERVAL" \
  --compact

echo
echo "[DONE] 运行完成。"
echo "日志目录: $SCRIPT_DIR/logs"
echo "视频与回放目录: $SCRIPT_DIR/grf_logs"
