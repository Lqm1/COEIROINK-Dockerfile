#!/bin/sh
set -e

INTERNAL_PORT=50032 # エンジンがリッスンする内部ポート
EXTERNAL_PORT=8000  # socatが外部に公開するポート

echo "Starting socat: Forwarding 0.0.0.0:${EXTERNAL_PORT} -> 127.0.0.1:${INTERNAL_PORT}"
socat TCP-LISTEN:${EXTERNAL_PORT},fork,reuseaddr TCP:127.0.0.1:${INTERNAL_PORT} &

echo "Starting engine: Expected to listen on 127.0.0.1:${INTERNAL_PORT}"
exec /app/coeiroink/engine/engine