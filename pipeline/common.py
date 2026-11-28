"""Outils communs : police, fond, dessin, voix IA (Kokoro), sons, musique, encodage."""
import json, math, os, re, subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
W, H, FPS = 1080, 1920, 30
SR = 44100
FONT = os.path.join(HERE, "fonts", "Montserrat.ttf")
KOKORO_DIR = os.path.expanduser(os.environ.get("KOKORO_DIR", "~/.cache/laqlture/kokoro-multi-lang-v1_0"))

NAVY = (18, 22, 58)
CARD = (32, 38, 92)
CARD_BORDER = (78, 88, 170)
ACCENT = (124, 92, 255)
GREEN = (46, 204, 113)
WHITE = (255, 255, 255)
YELLOW = (255, 214, 10)
SOFT = (215, 215, 255)
LEVELS = {"FACILE": (46, 204, 113), "MOYEN": (241, 196, 15), "DIFFICILE": (230, 126, 34), "EXPERT": (231, 76, 60)}

# ---------------- dessin ----------------
_fc = {}
def font(size, weight="ExtraBold"):
    k = (size, weight)
    if k not in _fc:
        f = ImageFont.truetype(FONT, size); f.set_variation_by_name(weight); _fc[k] = f
    return _fc[k]

def ease_out(x): x = min(max(x, 0), 1); return 1 - (1 - x) ** 3
def ease_back(x):
    x = min(max(x, 0), 1); c1 = 1.70158; c3 = c1 + 1
    return 1 + c3 * (x - 1) ** 3 + c1 * (x - 1) ** 2

_dummy = ImageDraw.Draw(Image.new("RGB", (10, 10)))
def wrap(text, f, maxw):
    words, lines, cur = text.split(" "), [], ""   # l'espace insécable reste collé (« française ! »)
    for w in words:
        t = (cur + " " + w).strip()
        if _dummy.textlength(t, font=f) <= maxw: cur = t
        else:
            if cur: lines.append(cur)
            cur = w
    lines.append(cur)
    return lines

def rr_image(w, h, r, fill, border=None, bw=0, shadow=False):
    """Rectangle arrondi anti-aliasé (rendu en 2x). Retourne (image RGBA, marge)."""
    s = 2; pad = 30 if shadow else 0
    im = Image.new("RGBA", ((w + 2 * pad) * s, (h + 2 * pad) * s), (0, 0, 0, 0))
    if shadow:
        ImageDraw.Draw(im).rounded_rectangle([pad * s, (pad + 10) * s, (pad + w) * s, (pad + h + 10) * s], r * s, fill=(0, 0, 0, 110))
        im = im.filter(ImageFilter.GaussianBlur(18 * s))
    d = ImageDraw.Draw(im)
    box = [pad * s, pad * s, (pad + w) * s - 1, (pad + h) * s - 1]
    if border:
        d.rounded_rectangle(box, r * s, fill=border)
        box = [box[0] + bw * s, box[1] + bw * s, box[2] - bw * s, box[3] - bw * s]
        d.rounded_rectangle(box, (r - bw) * s, fill=fill)
    else:
        d.rounded_rectangle(box, r * s, fill=fill)
    return im.resize((w + 2 * pad, h + 2 * pad), Image.LANCZOS), pad

def paste(base, im, x, y, alpha=1.0, scale=1.0):
    if scale != 1.0:
        nw, nh = max(1, int(im.width * scale)), max(1, int(im.height * scale))
        x += (im.width - nw) // 2; y += (im.height - nh) // 2
        im = im.resize((nw, nh), Image.BILINEAR)
    if alpha < 1.0:
        a = im.getchannel("A").point(lambda v: int(v * max(0, alpha)))
        im = im.copy(); im.putalpha(a)
    base.alpha_composite(im, (int(x), int(y)))

def make_bg(h=H, top=(16, 20, 56), bot=(52, 18, 88)):
    y = np.linspace(0, 1, h)[:, None]; x = np.linspace(0, 1, W)[None, :]
    g = np.array(top)[None, None, :] * (1 - y[..., None]) + np.array(bot)[None, None, :] * y[..., None]
    for cx, cy, r, col, k in [(0.15, 0.12, 0.45, (90, 70, 255), 0.35), (0.9, 0.85, 0.5, (255, 60, 160), 0.22), (0.85, 0.35, 0.35, (0, 180, 255), 0.15)]:
        dist = np.sqrt(((x - cx) * W / h) ** 2 + (y - cy) ** 2)
        m = np.clip(1 - dist / r, 0, 1) ** 2 * k
        g = g * (1 - m[..., None]) + np.array(col)[None, None, :] * m[..., None]
    im = Image.fromarray(np.clip(g, 0, 255).astype(np.uint8), "RGB").convert("RGBA")
    d = ImageDraw.Draw(im)
    for yy in range(40, h, 60):
        for xx in range(40 + (yy // 60 % 2) * 30, W, 60):
            d.ellipse([xx - 2, yy - 2, xx + 2, yy + 2], fill=(255, 255, 255, 14))
    return im

BG = make_bg()

def cta_button(text, w, h, size):
    btn, bp = rr_image(w, h, h // 2, (255, 44, 85), shadow=True)
    ImageDraw.Draw(btn).text((bp + w / 2, bp + h / 2 + 2), text, font=font(size, "Black"), fill=WHITE, anchor="mm")
    return btn, bp

# ---------------- encodage ----------------
def encode(path, dur, fn):
    """Encode une scène (fn(t) -> image) dans un fichier mp4 ; renommé seulement si ffmpeg réussit."""
    n = int(round(dur * FPS)); tmp = path[:-4] + ".tmp.mp4"
    p = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
                          "-i", "-", "-c:v", "libx264", "-crf", "19", "-preset", "veryfast", "-pix_fmt", "yuv420p",
                          "-r", str(FPS), tmp], stdin=subprocess.PIPE)
    for f in range(n):
        p.stdin.write(fn(f / FPS).convert("RGB").tobytes())
    p.stdin.close()
    if p.wait() != 0: raise SystemExit(f"échec encodage {path}")
    os.replace(tmp, path)

def assemble(scene_files, wav, out):
    lst = os.path.join(os.path.dirname(scene_files[0]), "list.txt")
    open(lst, "w").write("".join(f"file '{os.path.abspath(s)}'\n" for s in scene_files))
    vid = os.path.join(os.path.dirname(scene_files[0]), "video_only.mp4")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", vid], check=True)
    tmp = out[:-4] + ".tmp.mp4"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", vid, "-i", wav, "-map", "0:v", "-map", "1:a", "-c:v", "copy",
                    "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", tmp], check=True)
    os.replace(tmp, out)

def duration(path):
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path]))

# ---------------- voix IA (Kokoro, voix française ff_siwis) ----------------
_tts = {}
FIX = [(r"\bquiz\b", "kouiz"), (r"\bquizz\b", "kouiz")]

def _kokoro():
    if not _tts:
        import onnxruntime as ort
        from piper.phonemize_espeak import EspeakPhonemizer
        tok = {}
        for l in open(os.path.join(KOKORO_DIR, "tokens.txt"), encoding="utf8").read().split("\n"):
            if l: s, i = l.rsplit(" ", 1); tok[s if s else " "] = int(i)
        _tts.update(tok=tok, ph=EspeakPhonemizer(),
                    voices=np.fromfile(os.path.join(KOKORO_DIR, "voices.bin"), dtype=np.float32).reshape(54, 510, 1, 256),
                    sess=ort.InferenceSession(os.path.join(KOKORO_DIR, "model.onnx"), providers=["CPUExecutionProvider"]))
    return _tts

VOICE = os.environ.get("LAQLTURE_VOICE", "kokoro")   # kokoro (défaut) | tom | chatterbox
PIPER_DIR = os.path.expanduser("~/.cache/laqlture/piper")
_cb = {}

def _raw_kokoro(text, raw, speed=1.1, sid=30):
    k = _kokoro()
    ps = " ".join("".join(s) for s in k["ph"].phonemize("fr", text)).replace("-", "")
    ids = [k["tok"][c] for c in ps if c in k["tok"]][:508]
    audio = k["sess"].run(None, {"tokens": np.array([[0] + ids + [0]], dtype=np.int64), "style": k["voices"][sid, len(ids)],
                                 "speed": np.array([speed], dtype=np.float32)})[0].squeeze()
    import soundfile as sf
    sf.write(raw, audio, 24000)

def _raw_tom(text, raw):
    """Voix masculine Piper fr_FR-tom-medium."""
    if "tom" not in _tts:
        from piper import PiperVoice
        _tts["tom"] = PiperVoice.load(os.path.join(PIPER_DIR, "fr_FR-tom-medium.onnx"))
    from piper.config import SynthesisConfig
    import wave
    with wave.open(raw, "wb") as wf:
        _tts["tom"].synthesize_wav(text, wf, syn_config=SynthesisConfig(length_scale=0.92))

def _raw_chatterbox(text, raw):
    """Chatterbox Multilingual (MIT) via un worker dans son propre environnement Python."""
    import json as _j
    if "p" not in _cb:
        py = os.path.expanduser(os.environ.get("CB_PYTHON", "~/.venvs/cb/bin/python"))
        _cb["p"] = subprocess.Popen([py, os.path.join(HERE, "tts_chatterbox.py")], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                    stderr=subprocess.DEVNULL, text=True)
        assert _j.loads(_cb["p"].stdout.readline()).get("ready")
    _cb["p"].stdin.write(_j.dumps({"text": text, "path": raw}) + "\n"); _cb["p"].stdin.flush()
    assert _j.loads(_cb["p"].stdout.readline()).get("ok")

def tts_close():
    """Arrête le worker Chatterbox (libère ~3 Go de mémoire avant le rendu des images)."""
    if "p" in _cb:
        _cb["p"].stdin.close(); _cb["p"].wait(timeout=60); del _cb["p"]

def say(text, path, speed=1.1, sid=30):
    """Synthétise `text` en français, coupe les silences, écrit un wav 44.1 kHz mono. Retourne la durée."""
    if os.environ.get("LAQLTURE_REUSE") and os.path.exists(path):   # relance : on garde la voix déjà générée
        return round(duration(path), 3)
    for a, b in FIX: text = re.sub(a, b, text, flags=re.I)
    raw = path[:-4] + ".raw.wav"
    if VOICE == "tom": _raw_tom(text, raw)
    elif VOICE == "chatterbox": _raw_chatterbox(text, raw)
    else: _raw_kokoro(text, raw, speed, sid)
    tempo = float(os.environ.get("LAQLTURE_TEMPO", "1.0"))
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", raw, "-af",
                    "silenceremove=start_periods=1:start_threshold=-45dB,areverse,silenceremove=start_periods=1:start_threshold=-45dB,areverse,"
                    + (f"atempo={tempo}," if tempo != 1.0 else "") + "aresample=44100",
                    "-ac", "1", path], check=True)
    os.remove(raw)
    return round(duration(path), 3)

# ---------------- audio ----------------
def load(path):
    raw = subprocess.check_output(["ffmpeg", "-v", "error", "-i", path, "-f", "f32le", "-ac", "1", "-ar", str(SR), "-"])
    return np.frombuffer(raw, np.float32).astype(np.float64)

class Track:
    def __init__(self, total):
        self.total = total; self.N = int(total * SR) + SR
        self.voice = np.zeros(self.N); self.sfx = np.zeros(self.N)
    def add(self, buf, x, t, g=1.0):
        i = int(t * SR)
        if i >= self.N: return
        j = min(self.N, i + len(x)); buf[i:j] += x[: j - i] * g

def _env(n, a, d):
    t = np.arange(n) / SR
    return np.minimum(t / a, 1) * np.exp(-t / d)

def tone(freqs, dur, a=0.002, d=0.15):
    n = int(dur * SR); t = np.arange(n) / SR
    return sum(amp * np.sin(2 * np.pi * f * t) for f, amp in freqs) * _env(n, a, d)

_rng = np.random.default_rng(3)
TICK = tone([(1800, .6), (3600, .25), (900, .3)], 0.08, 0.0005, 0.012)
TOCK = tone([(1300, .6), (2600, .25), (650, .3)], 0.08, 0.0005, 0.012)
DING = np.pad(tone([(1046.5, .5), (2093, .15), (3139, .05)], 0.12, 0.002, 0.3)[: int(0.09 * SR)], (0, int(0.9 * SR)))
DING[int(0.09 * SR): int(0.09 * SR) + int(0.9 * SR)] += tone([(1568, .5), (3136, .15), (4704, .05)], 0.9, 0.002, 0.35)
def _whoosh():
    n = int(0.35 * SR); noise = _rng.standard_normal(n); out = np.zeros(n); y = 0.0
    for k in range(n):
        a = 0.02 + 0.25 * np.sin(np.pi * k / n); y += a * (noise[k] - y); out[k] = y
    out *= np.sin(np.pi * np.arange(n) / n) ** 2
    return out / np.abs(out).max()
WHOOSH = _whoosh()
POP = tone([(660, .5), (990, .3)], 0.15, 0.001, 0.04)

def music_bed(total, chords=None, bpm=100, soft=False):
    """Boucle musicale originale (libre de droits) : nappe + arpège + rythme léger."""
    chords = chords or [[57, 60, 64], [53, 57, 60], [48, 55, 60], [55, 59, 62]]
    beat = 60 / bpm; bar = 4 * beat; mf = lambda m: 440 * 2 ** ((m - 69) / 12)
    N = int(total * SR) + SR; music = np.zeros(N)
    def add(x, t):
        i = int(t * SR)
        if i >= N: return
        j = min(N, i + len(x)); music[i:j] += x[: j - i]
    for b in range(int(total / bar) + 2):
        ch = chords[b % len(chords)]; st = b * bar; n = int(bar * SR); t = np.arange(n) / SR
        pad = sum(np.sin(2 * np.pi * mf(m) * t) + 0.5 * np.sin(2 * np.pi * mf(m) * 1.003 * t) for m in ch)
        add(pad * np.minimum(t / 0.4, 1) * np.minimum((bar - t) / 0.4, 1) * 0.05, st)
        bass = np.sin(2 * np.pi * mf(ch[0] - 12) * t) * np.minimum(t / 0.02, 1) * np.exp(-t / 0.9)
        add(bass * 0.12, st); add(bass * 0.08, st + 2 * beat)
        arp = [ch[0] + 12, ch[1] + 12, ch[2] + 12, ch[1] + 12, ch[0] + 24, ch[2] + 12, ch[1] + 12, ch[2] + 12]
        for k, m in enumerate(arp):
            add(tone([(mf(m), .6), (mf(m) * 2, .15)], 0.5, 0.003, 0.18) * (0.05 if soft else 0.07), st + k * beat / 2)
        for k in range(4):
            kn = int(0.25 * SR); tk = np.arange(kn) / SR
            kick = np.sin(2 * np.pi * (50 + 80 * np.exp(-tk / 0.03)) * tk) * np.exp(-tk / 0.12)
            add(kick * (0.10 if soft else 0.18), st + k * beat)
            hat = _rng.standard_normal(int(0.04 * SR)); hat = np.diff(hat, prepend=0) * _env(len(hat), 0.0005, 0.01)
            add(hat * 0.03, st + k * beat + beat / 2)
    return music

def mixdown(track, out_wav, music_gain=0.55, soft=False):
    end = int(track.total * SR)
    music = music_bed(track.total, soft=soft)[: track.N]
    fade = int(1.5 * SR); music[end - fade:end] *= np.linspace(1, 0, fade); music[end:] = 0
    k = int(0.05 * SR); venv = np.convolve(np.abs(track.voice), np.ones(k) / k, mode="same")
    duck = 1 - 0.65 * np.clip(venv / 0.03, 0, 1)
    k2 = int(0.15 * SR); duck = np.convolve(duck, np.ones(k2) / k2, mode="same")
    mix = track.voice / max(np.abs(track.voice).max(), 1e-6) * 0.8 + track.sfx + music * duck * music_gain
    mix = mix[:end]; mix /= max(1.0, np.abs(mix).max() / 0.95)
    f32 = out_wav + ".f32"
    open(f32, "wb").write(np.stack([mix, mix], 1).astype(np.float32).tobytes())
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", f32,
                    "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-ar", str(SR), out_wav], check=True)
    os.remove(f32)
