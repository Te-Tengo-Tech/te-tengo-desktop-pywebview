#!/usr/bin/env bash
# Downloads the MediaPipe Pose Landmarker (lite) model into models/.
# Source: https://ai.google.dev/edge/mediapipe/solutions/vision/pose_landmarker#models
set -euo pipefail

URL="https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/latest/pose_landmarker_lite.task"
DESTINO="${1:-models/pose_landmarker_lite.task}"

mkdir -p "$(dirname "$DESTINO")"
if [[ -f "$DESTINO" ]]; then
  echo "The model already exists: $DESTINO"
  exit 0
fi
curl --fail --location --silent --show-error --output "$DESTINO" "$URL"
echo "Model downloaded to $DESTINO"
