"""Lancé avec le python du venv : horodatage des mots (faster-whisper small, français). stdin : [[wav, texte], …]."""
import json, os, sys
PROTO = os.fdopen(os.dup(1), "w"); os.dup2(2, 1); sys.stdout = sys.stderr
import librosa
from faster_whisper import WhisperModel
jobs = json.load(sys.stdin)
m = WhisperModel("small", device="cpu", compute_type="int8")
res = []
for wav, text in jobs:
    segs, _ = m.transcribe(librosa.load(wav, sr=16000)[0], language="fr", word_timestamps=True, initial_prompt=text, beam_size=3)
    res.append([[w.word, round(w.start, 3), round(w.end, 3)] for s in segs for w in s.words])
print(json.dumps(res), file=PROTO, flush=True)
