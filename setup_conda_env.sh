#!/usr/bin/env bash
set -euo pipefail

ENV_NAME="grf_llm"
PY_VER="3.10"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if ! command -v conda >/dev/null 2>&1; then
  echo "[ERROR] 未检测到 conda，请先安装 Miniconda/Anaconda。"
  exit 1
fi

eval "$(conda shell.bash hook)"

if conda env list | awk '{print $1}' | grep -qx "$ENV_NAME"; then
  echo "[INFO] conda 环境 $ENV_NAME 已存在，跳过创建。"
else
  echo "[INFO] 创建 conda 环境: $ENV_NAME (python=$PY_VER)"
  conda create -n "$ENV_NAME" "python=$PY_VER" -y
fi

conda activate "$ENV_NAME"

echo "[INFO] 安装 gfootball 原生依赖（OpenGL/SDL/Boost）"
conda install -y -c conda-forge \
  mesalib libglu libegl-devel libglx-devel libopengl-devel \
  sdl2 sdl2_image sdl2_ttf sdl2_gfx \
  "boost-cpp=1.84.*" "libboost=1.84.*" "libboost-headers=1.84.*" \
  "libboost-devel=1.84.*" "libboost-python=1.84.*" "libboost-python-devel=1.84.*" \
  cmake pkg-config

# CMake 在部分环境会寻找无版本后缀的 OpenGL 动态库
ln -sf "$CONDA_PREFIX/lib/libOpenGL.so.0" "$CONDA_PREFIX/lib/libOpenGL.so" || true
ln -sf "$CONDA_PREFIX/lib/libGLX.so.0" "$CONDA_PREFIX/lib/libGLX.so" || true

echo "[INFO] 升级 pip/setuptools/wheel"
pip install --upgrade pip setuptools wheel

echo "[INFO] 预装 gfootball 构建依赖: psutil"
pip install psutil

echo "[INFO] 安装除 gfootball 外的 Python 依赖"
TMP_REQ="$(mktemp)"
grep -v '^gfootball$' requirements.txt > "$TMP_REQ"
pip install -r "$TMP_REQ"
rm -f "$TMP_REQ"

echo "[INFO] 安装 gfootball（关闭构建隔离，避免 psutil 丢失）"
export CMAKE_PREFIX_PATH="$CONDA_PREFIX"
export CMAKE_LIBRARY_PATH="$CONDA_PREFIX/lib"
export CMAKE_INCLUDE_PATH="$CONDA_PREFIX/include"
export LD_LIBRARY_PATH="$CONDA_PREFIX/lib:${LD_LIBRARY_PATH:-}"
pip install --no-build-isolation gfootball

echo "[INFO] 固定 gym 版本以兼容 gfootball"
pip install "gym<0.26"

echo "[INFO] 校验关键依赖"
python - <<'PY'
import importlib
mods = ["gfootball", "openai", "yaml", "numpy", "dotenv"]
missing = [m for m in mods if importlib.util.find_spec(m) is None]
if missing:
    raise SystemExit(f"缺少依赖: {missing}")
print("依赖校验通过")
PY

echo
echo "[DONE] 环境已就绪: conda activate $ENV_NAME"
echo "[NEXT] 复制 .env.example 为 .env，并填入 LLM_API_KEY / LLM_API_BASE / LLM_MODEL"
