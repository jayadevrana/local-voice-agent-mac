#!/bin/bash
# Launch the Jaya voice agent (local, real-time)
cd "$(dirname "$0")"

# 1. ensure ollama is serving
if ! curl -s http://localhost:11434/api/version >/dev/null 2>&1; then
  echo "starting ollama…"
  OLLAMA_FLASH_ATTENTION="1" OLLAMA_KV_CACHE_TYPE="q8_0" \
    nohup /opt/homebrew/opt/ollama/bin/ollama serve > data/ollama.log 2>&1 &
  sleep 3
fi

# 2. run the agent
source .venv/bin/activate
export TOKENIZERS_PARALLELISM=false
python -m app.agent
