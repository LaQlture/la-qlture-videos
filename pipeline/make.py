"""Fabrique une vidéo à partir d'un fichier de contenu JSON.

Usage : python pipeline/make.py contenu/AAAA-MM-JJ_type.json
Sortie : videos/AAAA-MM-JJ_type.mp4 + planche de vérification dans /tmp/laqlture/<date>/verif.jpg
"""
import json, multiprocessing as mp, os, subprocess, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import encode, assemble, duration, FPS, tts_close

MIN_DUR = 62.0   # monétisation TikTok : plus d'1 minute
OBJ = None

def _render(args):
    name, dur, path = args
    encode(path, dur, OBJ.frame_fn(name))
    return name

def main(src):
    global OBJ
    c = json.load(open(src))
    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    work = f"/tmp/laqlture/{c['date']}_{c['type']}"; os.makedirs(work, exist_ok=True)
    if c["type"] == "quiz":
        from quiz import Quiz; OBJ = Quiz(c, work)
    elif c["type"] == "histoire":
        from story import Story; OBJ = Story(c, work)
    else:
        raise SystemExit("type inconnu : " + c["type"])
    t = time.time()
    OBJ.voices(); tts_close()
    tl = OBJ.timeline(); total = sum(d for _, d in tl)
    print(f"voix OK ({time.time()-t:.0f}s) — durée prévue {total:.1f}s", flush=True)
    if total < MIN_DUR:
        raise SystemExit(f"TROP COURT : {total:.1f}s < {MIN_DUR}s — allonger le texte")

    # planche de vérification (les moments les plus chargés)
    from PIL import Image
    frames = [OBJ.frame_fn(n)(tt).convert("RGB").resize((360, 640)) for n, tt in OBJ.check_frames()]
    sheet = Image.new("RGB", (360 * len(frames), 640))
    for k, f in enumerate(frames): sheet.paste(f, (360 * k, 0))
    sheet.save(f"{work}/verif.jpg", quality=88)

    jobs = [(n, d, f"{work}/{n}.mp4") for n, d in tl]
    with mp.get_context("fork").Pool(max(1, min(4, os.cpu_count() or 2))) as pool:
        for n in pool.imap_unordered(_render, jobs): print("scène", n, flush=True)
    wav = f"{work}/mix.wav"; OBJ.audio(tl, wav)
    os.makedirs(f"{repo}/videos", exist_ok=True)
    out = f"{repo}/videos/{c['date']}_{c['type']}.mp4"
    assemble([j[2] for j in jobs], wav, out)
    d = duration(out)
    print(json.dumps({"video": out, "duree": round(d, 1), "verif": f"{work}/verif.jpg", "temps_s": round(time.time() - t)}))
    if d < MIN_DUR: raise SystemExit("vidéo trop courte")

if __name__ == "__main__":
    main(sys.argv[1])
