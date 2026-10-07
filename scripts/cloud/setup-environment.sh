#!/usr/bin/env bash
# Prepares a Claude Code cloud session: Python 3.11, MediaPipe system libraries and the model.
# Runs from the SessionStart hook in .claude/settings.json and only acts in the cloud.
set -euo pipefail
[ "${CLAUDE_CODE_REMOTE:-}" = "true" ] || exit 0
cd "$CLAUDE_PROJECT_DIR"

if ! command -v uv >/dev/null 2>&1; then
  pip install --quiet uv || curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$PATH"
fi

# MediaPipe needs OpenGL ES and EGL on Linux even on CPU (clips use PyAV, no ffmpeg needed).
if ! ldconfig -p | grep -q libGLESv2; then
  SUDO=$(command -v sudo || true)
  $SUDO apt-get update -qq && $SUDO apt-get install -y -qq --no-install-recommends libgles2 libegl1 >/dev/null
fi

uv python install 3.11
uv sync
[ -f models/pose_landmarker_lite.task ] || ./scripts/descargar_modelo.sh
echo "Environment ready: $(uv run python --version), $(uv run python -c 'import mediapipe; print("mediapipe", mediapipe.__version__)')"
