"""
Jaya — real-time local voice agent for macOS (Apple Silicon).

Pipeline:  mic -> Silero VAD (endpoint) -> Whisper (MLX) -> Ollama LLM (stream)
           -> sentence chunker -> Kokoro TTS -> speaker
Features:  streaming, per-sentence TTS for low first-audio latency,
           Hindi/English voice routing, barge-in (interrupt on speak).

Run:  python -m app.agent
"""
import sys, time, queue, threading, warnings, re
warnings.filterwarnings("ignore")

import numpy as np
import sounddevice as sd

from .config import (
    SAMPLE_RATE, TTS_SAMPLE_RATE, FRAME_MS, SILENCE_HANG_MS, MIN_SPEECH_MS,
    VAD_THRESHOLD, LLM_MODEL, WHISPER_REPO, KEEP_ALIVE, OLLAMA_HOST,
    VOICE_HINDI, VOICE_ENGLISH, TTS_SPEED, ASSISTANT_NAME,
)
from .knowledge import system_prompt

FRAME = int(SAMPLE_RATE * FRAME_MS / 1000)      # samples per VAD frame (512 @16k/32ms)
DEVANAGARI = re.compile(r"[ऀ-ॿ]")
SENT_END = re.compile(r"[.!?।\n]")


def log(msg): print(f"\033[90m{msg}\033[0m", flush=True)


class VoiceAgent:
    def __init__(self):
        log("Loading models…")
        import mlx_whisper
        from silero_vad import load_silero_vad
        from kokoro import KPipeline
        import ollama

        self.mlx_whisper = mlx_whisper
        self.vad = load_silero_vad()
        import torch
        self.torch = torch
        self.kok_hi = KPipeline(lang_code="h")   # Hindi
        self.kok_en = KPipeline(lang_code="a")   # American English
        self.llm = ollama.Client(host=OLLAMA_HOST)

        self.history = [{"role": "system", "content": system_prompt()}]
        self.interrupt = threading.Event()   # set when caller barges in
        self.speaking = threading.Event()     # set while TTS is playing
        self._warm()
        log("Ready.\n")

    def _warm(self):
        # pin LLM in RAM + warm whisper so first real turn is fast
        try:
            self.llm.chat(model=LLM_MODEL, messages=[{"role": "user", "content": "hi"}],
                          keep_alive=KEEP_ALIVE, options={"num_predict": 1})
        except Exception as e:
            log(f"LLM warm failed: {e}")
        self.mlx_whisper.transcribe(np.zeros(SAMPLE_RATE, np.float32),
                                    path_or_hf_repo=WHISPER_REPO, language="hi")

    # ---------- STT ----------
    def transcribe(self, audio: np.ndarray) -> str:
        r = self.mlx_whisper.transcribe(audio, path_or_hf_repo=WHISPER_REPO)
        return r["text"].strip()

    # ---------- TTS + playback (interruptible) ----------
    def speak(self, text: str):
        pipe = self.kok_hi if DEVANAGARI.search(text) else self.kok_en
        voice = VOICE_HINDI if DEVANAGARI.search(text) else VOICE_ENGLISH
        for _, _, audio in pipe(text, voice=voice, speed=TTS_SPEED):
            if self.interrupt.is_set():
                return
            a = np.asarray(audio, dtype=np.float32)
            # play in small blocks so barge-in stops within ~60ms
            blk = int(TTS_SAMPLE_RATE * 0.06)
            with sd.OutputStream(samplerate=TTS_SAMPLE_RATE, channels=1, dtype="float32") as out:
                for i in range(0, len(a), blk):
                    if self.interrupt.is_set():
                        return
                    out.write(a[i:i + blk])

    # ---------- LLM (streaming, sentence-chunked to TTS) ----------
    def respond(self, user_text: str):
        self.history.append({"role": "user", "content": user_text})
        self.interrupt.clear()
        self.speaking.set()
        buf, full = "", ""
        try:
            stream = self.llm.chat(model=LLM_MODEL, messages=self.history, stream=True,
                                   keep_alive=KEEP_ALIVE,
                                   options={"num_predict": 220, "temperature": 0.6})
            for ch in stream:
                if self.interrupt.is_set():
                    break
                tok = ch["message"]["content"]
                buf += tok; full += tok
                # flush a chunk to TTS as soon as a sentence completes
                if SENT_END.search(tok) and len(buf.strip()) > 2:
                    print(f"\033[92m{ASSISTANT_NAME}:\033[0m {buf.strip()}", flush=True)
                    self.speak(buf.strip())
                    buf = ""
            if buf.strip() and not self.interrupt.is_set():
                print(f"\033[92m{ASSISTANT_NAME}:\033[0m {buf.strip()}", flush=True)
                self.speak(buf.strip())
        finally:
            self.speaking.clear()
        if full.strip():
            self.history.append({"role": "assistant", "content": full.strip()})

    # ---------- main mic loop with VAD endpointing + barge-in ----------
    def run(self):
        q = queue.Queue()

        def cb(indata, frames, t, status):
            q.put(indata[:, 0].copy())

        speech, buf = [], np.zeros(0, np.float32)
        in_speech = False
        silence_ms = 0.0
        speech_ms = 0.0

        log("🎤 Listening. Speak in Hindi or English. Ctrl-C to quit.")
        with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="float32",
                            blocksize=FRAME, callback=cb):
            while True:
                chunk = q.get()
                buf = np.concatenate([buf, chunk])
                while len(buf) >= FRAME:
                    frame, buf = buf[:FRAME], buf[FRAME:]
                    prob = self.vad(self.torch.from_numpy(frame), SAMPLE_RATE).item()
                    voiced = prob >= VAD_THRESHOLD

                    # barge-in: caller speaks while agent is talking
                    if voiced and self.speaking.is_set():
                        self.interrupt.set()

                    if voiced:
                        if not in_speech:
                            in_speech = True; speech = []; speech_ms = 0.0
                        speech.append(frame); speech_ms += FRAME_MS; silence_ms = 0.0
                    elif in_speech:
                        speech.append(frame); silence_ms += FRAME_MS
                        if silence_ms >= SILENCE_HANG_MS:
                            in_speech = False
                            if speech_ms >= MIN_SPEECH_MS:
                                utt = np.concatenate(speech)
                                t0 = time.time()
                                text = self.transcribe(utt)
                                if text:
                                    print(f"\033[96mCaller:\033[0m {text}  "
                                          f"\033[90m[stt {time.time()-t0:.2f}s]\033[0m", flush=True)
                                    self.respond(text)
                                    log("🎤 Listening…")
                            speech = []


if __name__ == "__main__":
    try:
        VoiceAgent().run()
    except KeyboardInterrupt:
        print("\nbye.")
        sys.exit(0)
