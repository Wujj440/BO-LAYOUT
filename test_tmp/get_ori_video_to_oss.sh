#!/bin/bash
set -e

cd "$(dirname "$0")"
mkdir -p logs
LOG="logs/get_ori_video_$(date +%Y%m%d_%H%M%S).log"

BOX_ID="${BOX_ID:-1420125020341}"
CAMERA_ID="${CAMERA_ID:-DS-2CD3786G2-IZS20230731AAWRAE4588060}"
DURATION="${DURATION:-60}"

python3 -m pip install -q opencv-python-headless oss2

python3 get_ori_video_to_oss.py \
  --box_id "$BOX_ID" \
  --camera_id "$CAMERA_ID" \
  --duration "$DURATION" \
  2>&1 | tee "$LOG"
