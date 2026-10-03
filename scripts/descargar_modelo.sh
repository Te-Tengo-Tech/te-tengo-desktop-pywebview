#!/usr/bin/env bash
# Descarga el modelo MediaPipe Pose Landmarker (lite) en models/.
# Fuente: https://ai.google.dev/edge/mediapipe/solutions/vision/pose_landmarker#models
set -euo pipefail

URL="https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/latest/pose_landmarker_lite.task"
DESTINO="${1:-models/pose_landmarker_lite.task}"

mkdir -p "$(dirname "$DESTINO")"
if [[ -f "$DESTINO" ]]; then
  echo "El modelo ya existe: $DESTINO"
  exit 0
fi
curl --fail --location --silent --show-error --output "$DESTINO" "$URL"
echo "Modelo descargado en $DESTINO"
