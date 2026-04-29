#!/bin/bash
# Proto dosyasından Python stub'ları üretir
set -e

PROTO_DIR="$(dirname "$0")/proto"
OUT_DIR="$(dirname "$0")"

python -m grpc_tools.protoc \
  -I"$PROTO_DIR" \
  --python_out="$OUT_DIR" \
  --grpc_python_out="$OUT_DIR" \
  "$PROTO_DIR/video_analysis.proto"

echo "Proto stubs generated in $OUT_DIR"
