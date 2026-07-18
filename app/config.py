"""Central config for the Jaya voice agent."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

# ---- Models ----
# 3b = fastest (lower latency, weaker Hindi); 7b = better Hindi (a bit slower).
# Override at runtime:  LLM_MODEL=qwen2.5:7b-instruct-q4_K_M python -m app.agent
LLM_MODEL = os.environ.get("LLM_MODEL", "qwen2.5:3b-instruct-q4_K_M")
WHISPER_REPO = "mlx-community/whisper-large-v3-turbo"
OLLAMA_HOST = "http://localhost:11434"
KEEP_ALIVE = "30m"   # keep LLM resident in RAM so TTFT stays ~0.1s

# ---- Audio ----
SAMPLE_RATE = 16000          # mic + whisper
TTS_SAMPLE_RATE = 24000      # kokoro output
FRAME_MS = 32                # silero frame size (512 samples @16k)
SILENCE_HANG_MS = 600        # silence after speech = end of turn
MIN_SPEECH_MS = 250          # ignore blips shorter than this
VAD_THRESHOLD = 0.5          # silero speech probability

# ---- Voices (Kokoro) ----
# Hindi voices: hf_alpha, hf_beta (female) / hm_omega, hm_psi (male)
# English voices: af_heart, af_bella (female) / am_michael, am_adam (male)
VOICE_HINDI = "hf_alpha"
VOICE_ENGLISH = "af_heart"
TTS_SPEED = 1.05

# ---- Persona ----
ASSISTANT_NAME = "Jaya"
OWNER_NAME = "Jayadev Rana"
