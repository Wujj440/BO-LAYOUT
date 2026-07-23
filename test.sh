#!/bin/bash
set -e

cd "$(dirname "$0")"
mkdir -p logs
LOG="logs/get_ori_video_$(date +%Y%m%d_%H%M%S).log"
PID_FILE="logs/get_ori_video.pid"

# ========== 门店 box_id 对照（按需修改） ==========
# IDNV001 -> 1420125020341
# IDNV033 -> 1421625036657
# IDNV017 -> 1421625036655
# IDNV011 -> 1421625037401
# IDNV041 -> 1421625036799
#
# 当前使用的 box_id（改这里即可切换门店）：
BOX_ID="${BOX_ID:-1420125020341}"   # IDNV001
# BOX_ID="${BOX_ID:-1421625036657}" # IDNV033
# BOX_ID="${BOX_ID:-1421625036655}" # IDNV017
# BOX_ID="${BOX_ID:-1421625037401}" # IDNV011
# BOX_ID="${BOX_ID:-1421625036799}" # IDNV041
# ==================================================

DURATION="${DURATION:-72}"

nohup python3 test.py \
  --box_id "$BOX_ID" \
  --duration "$DURATION" \
  >> "$LOG" 2>&1 &

echo $! > "$PID_FILE"
echo "已后台启动, box_id=$BOX_ID, PID=$(cat "$PID_FILE"), 日志=$LOG"
