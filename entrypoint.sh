#!/bin/sh
set -e

INTERNAL_PORT=50032  # エンジンがリッスンする内部ポート
EXTERNAL_PORT=2080   # Caddy が外部に公開するポート

echo "Starting engine: Expected to listen on 127.0.0.1:${INTERNAL_PORT}"
/app/coeiroink/engine/engine &

echo "Starting Caddy: Forwarding 0.0.0.0:${EXTERNAL_PORT} -> 127.0.0.1:${INTERNAL_PORT}"
exec caddy reverse-proxy --from :${EXTERNAL_PORT} --to 127.0.0.1:${INTERNAL_PORT}  
