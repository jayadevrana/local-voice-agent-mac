"""Headless test: feed text turns through LLM->TTS, measure latency, save audio.
No mic/speaker needed. Validates the 'brain' end-to-end."""
import time, warnings, numpy as np, soundfile as sf
warnings.filterwarnings("ignore")
from app.agent import VoiceAgent, DEVANAGARI
from app.config import VOICE_HINDI, VOICE_ENGLISH, TTS_SPEED, TTS_SAMPLE_RATE

class TestAgent(VoiceAgent):
    def __init__(self):
        super().__init__()
        self._audio = []
        self._t_first = None
        self._t0 = None
    def speak(self, text):
        pipe = self.kok_hi if DEVANAGARI.search(text) else self.kok_en
        voice = VOICE_HINDI if DEVANAGARI.search(text) else VOICE_ENGLISH
        for _, _, a in pipe(text, voice=voice, speed=TTS_SPEED):
            if self._t_first is None:
                self._t_first = time.time() - self._t0   # first-audio latency
            self._audio.append(np.asarray(a, np.float32))

a = TestAgent()
queries = [
    "Hello, who is this? What does Jayadev do?",
    "नमस्ते, क्या जयदेव पाइन स्क्रिप्ट का काम करते हैं? रेट क्या है?",
    "Bhai mujhe ek binance trading bot banwana hai, kaise contact karu?",
]
for q in queries:
    a._audio = []; a._t_first = None
    a.history = a.history[:1]      # reset to system prompt each query
    print(f"\n\033[96mCaller:\033[0m {q}")
    a._t0 = time.time()
    a.respond(q)
    total = time.time() - a._t0
    au = np.concatenate(a._audio) if a._audio else np.zeros(1, np.float32)
    fn = f"data/reply_{queries.index(q)+1}.wav"
    sf.write(fn, au, TTS_SAMPLE_RATE)
    print(f"\033[90m[first-audio {a._t_first:.2f}s | full-turn {total:.2f}s | "
          f"{len(au)/TTS_SAMPLE_RATE:.1f}s speech -> {fn}]\033[0m")
print("\ndone.")
