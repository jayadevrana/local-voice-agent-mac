# Local Voice Agent (macOS)

Real-time, fully-offline AI voice assistant for macOS Apple Silicon — Silero VAD + Whisper (MLX) + Ollama LLM streaming + Kokoro TTS, with Hindi/English voice routing and barge-in interruption.

## Features

- Fully offline, on-device pipeline: nothing leaves your Mac.
- Real-time turn-taking: Silero VAD endpoints your speech; the agent replies as soon as you stop.
- Low first-audio latency: the LLM response is streamed and chunked per sentence straight into TTS.
- Automatic Hindi/English voice routing — Devanagari is spoken with a Hindi Kokoro voice, Latin text with an English voice.
- Barge-in: start speaking while the agent is talking and it stops within ~60ms.
- Whisper large-v3-turbo via MLX for fast Apple-Silicon transcription.
- Ollama LLM kept resident in RAM (`keep_alive`) so time-to-first-token stays low.
- Grounded persona driven by an editable Markdown knowledge base.

## Stack

- Python 3.12
- [MLX Whisper](https://github.com/ml-explore/mlx-examples) — speech-to-text (`mlx-community/whisper-large-v3-turbo`)
- [Silero VAD](https://github.com/snakers4/silero-vad) — voice-activity detection / endpointing
- [Ollama](https://ollama.com) — local LLM streaming (default `qwen2.5:3b-instruct`, optional `7b`)
- [Kokoro](https://github.com/hexgrad/kokoro) — text-to-speech (Hindi + English voices)
- `sounddevice` / `numpy` / `soundfile` — audio I/O

## Getting started

Requires macOS on Apple Silicon, Python 3.12, and [Ollama](https://ollama.com) installed.

```bash
# 1. create a virtualenv and install deps
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 2. pull an LLM for Ollama (first run only)
ollama pull qwen2.5:3b-instruct-q4_K_M
# optional, better Hindi:
# ollama pull qwen2.5:7b-instruct-q4_K_M

# 3. run the live mic agent
./run.sh
# or directly:
python -m app.agent
```

Speak in Hindi or English; press Ctrl-C to quit.

To pick the larger model at runtime:

```bash
LLM_MODEL=qwen2.5:7b-instruct-q4_K_M python -m app.agent
```

### Headless test (no mic/speaker)

`test_turn.py` feeds text turns through the LLM → TTS path, measures first-audio and full-turn latency, and writes the replies to `data/reply_*.wav`:

```bash
python test_turn.py
```

## Configuration

All tunables live in `app/config.py` — models, sample rates, VAD threshold, silence/endpointing timings, voices, and persona. The assistant's knowledge is a plain Markdown file at `data/knowledge.md`; edit it to change what the agent knows and how it introduces itself.

## Notes

Runs entirely on-device — audio, transcription, the LLM, and speech synthesis never touch the network. Model download (Whisper, Ollama, Kokoro voices) happens once on first use.

## Author

Built by [Jayadev Rana](https://jayadevrana.in) — @bluealgocapital · [YouTube](https://www.youtube.com/@jayadevrana3657) · [GitHub](https://github.com/jayadevrana)
