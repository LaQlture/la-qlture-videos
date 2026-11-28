"""Worker Chatterbox Multilingual (licence MIT, Resemble AI) — lancé avec le python du venv dédié.
Protocole : une ligne JSON par requête sur stdin {"text":…, "path":…} → une ligne JSON {"ok":true} sur stdout."""
import json, os, re, sys
# stdout réservé au protocole : tout ce que les bibliothèques affichent part sur stderr
PROTO = os.fdopen(os.dup(1), "w"); os.dup2(2, 1); sys.stdout = sys.stderr
import torch, torchaudio as ta
from num2words import num2words
from chatterbox.mtl_tts import ChatterboxMultilingualTTS

REF = os.environ.get("CB_REF")            # wav de référence (timbre) ; sinon voix par défaut du modèle
EXAG = float(os.environ.get("CB_EXAG", "0.5")); CFG = float(os.environ.get("CB_CFG", "0.5"))

def norm(t):
    t = re.sub(r"(\d+),(\d+)", lambda m: num2words(int(m[1]), lang="fr") + " virgule " + num2words(int(m[2]), lang="fr"), t)
    t = re.sub(r"(\d)[  ](\d{3})", r"\1\2", t)
    t = re.sub(r"\d+", lambda m: num2words(int(m[0]), lang="fr"), t)
    return t.replace("«", "").replace("»", "").replace("…", "...")

m = ChatterboxMultilingualTTS.from_pretrained(device="cpu")
if REF: m.prepare_conditionals(REF, exaggeration=EXAG)
print(json.dumps({"ready": True}), file=PROTO, flush=True)
for line in sys.stdin:
    r = json.loads(line); torch.manual_seed(r.get("seed", 1234))
    w = m.generate(norm(r["text"]), language_id="fr", exaggeration=EXAG, cfg_weight=CFG)
    ta.save(r["path"], w, m.sr)
    print(json.dumps({"ok": True}), file=PROTO, flush=True)
