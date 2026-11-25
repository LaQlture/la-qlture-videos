"""Vidéo « Histoire racontée » : un sujet raconté phrase par phrase, carte mot-clé + sous-titres synchronisés."""
import math, os, re
from PIL import Image, ImageDraw
from common import *
from common import _dummy

CX = W // 2 - 30           # centre décalé à gauche (icônes TikTok à droite)
CARD_Y, CARD_W, CARD_H = 470, 880, 470
CAP_Y = 1110
PALETTE = [(124, 92, 255), (255, 92, 138), (0, 168, 255), (255, 159, 28), (46, 204, 113), (231, 76, 60)]
DEMAIN = {"quiz": "Abonne-toi : demain, un nouveau quiz t'attend !",
          "histoire": "Abonne-toi : demain, une nouvelle histoire t'attend !"}

def chunks(text, maxc=20):
    words, out, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if len(t) <= maxc or not cur: cur = t
        else: out.append(cur); cur = w
    out.append(cur)
    # évite un dernier morceau d'un seul petit mot
    if len(out) > 1 and len(out[-1]) <= 4: out[-2] += " " + out.pop()
    return out

class Story:
    def __init__(self, c, work):
        self.c, self.work = c, work
        self.segs = [dict(s) for s in c["segments"]]
        self.segs.append(dict(texte=DEMAIN[c.get("demain", "quiz")], carte="ABONNE-TOI", outro=True))

    def voices(self):
        t = 0.3
        for k, s in enumerate(self.segs):
            s["dur"] = say(s.get("tts", s["texte"]), os.path.join(self.work, f"s{k}.wav"))
            s["t0"] = t; s["start"] = t - (0.3 if k == 0 else 0.15)
            t += s["dur"] + (0.32 if not s.get("outro") else 0)
            # sous-titres : morceaux répartis au prorata du nombre de caractères
            cs = chunks(s["texte"]); w = [len(x) + 2 for x in cs]; tot = sum(w); acc = s["t0"]
            s["caps"] = []
            for x, ww in zip(cs, w):
                s["caps"].append((acc, x)); acc += s["dur"] * ww / tot
        self.total = round((t + 1.4) * FPS) / FPS
        for k, s in enumerate(self.segs):
            s["end"] = self.segs[k + 1]["start"] if k + 1 < len(self.segs) else self.total
            s["color"] = PALETTE[k % len(PALETTE)]

    def timeline(self):
        # une scène par segment (durées arrondies à l'image)
        tl, acc = [], 0.0
        for k, s in enumerate(self.segs):
            end = round(s["end"] * FPS) / FPS
            tl.append((f"s{k}", round((end - acc) * FPS) / FPS)); acc = end
        return tl

    # ---------- dessin ----------
    def card_img(self, s):
        txt = s["carte"].upper() if not s.get("keep_case") else s["carte"]
        col = s["color"]
        im, pad = rr_image(CARD_W, CARD_H, 48, col, shadow=True)
        # léger dégradé
        ov = Image.new("RGBA", im.size, (0, 0, 0, 0)); od = ImageDraw.Draw(ov)
        for yy in range(CARD_H):
            od.line([(pad, pad + yy), (pad + CARD_W, pad + yy)], fill=(0, 0, 0, int(70 * yy / CARD_H)))
        mask = Image.new("L", im.size, 0)
        ImageDraw.Draw(mask).rounded_rectangle([pad, pad, pad + CARD_W - 1, pad + CARD_H - 1], 48, fill=255)
        im.paste(Image.alpha_composite(im, ov), (0, 0), mask)
        d = ImageDraw.Draw(im)
        for size in (170, 150, 130, 112, 96, 84, 74, 66):
            f = font(size, "Black"); lines = wrap(txt, f, CARD_W - 110)
            if len(lines) * size * 1.12 <= CARD_H - 90 and all(_dummy.textlength(l, font=f) <= CARD_W - 110 for l in lines): break
        lh = f.size * 1.12; y0 = pad + CARD_H / 2 - lh * (len(lines) - 1) / 2
        for k, ln in enumerate(lines):
            d.text((pad + CARD_W / 2 + 4, y0 + k * lh + 6), ln, font=f, fill=(0, 0, 0, 90), anchor="mm")
            d.text((pad + CARD_W / 2, y0 + k * lh), ln, font=f, fill=WHITE, anchor="mm")
        return im, pad

    def header(self, im, t):
        d = ImageDraw.Draw(im)
        pill, _ = rr_image(250, 58, 29, YELLOW); im.alpha_composite(pill, (60, 150))
        d.text((185, 180), "HISTOIRE", font=font(34, "Black"), fill=(25, 20, 40), anchor="mm")
        d.text((330, 180), "la.qlture", font=font(34, "Bold"), fill=SOFT, anchor="lm")
        f = font(50, "Black"); lines = wrap(self.c["titre"], f, 880)[:2]
        for k, ln in enumerate(lines): d.text((60, 260 + k * 62), ln, font=f, fill=WHITE, anchor="lm")
        y = 260 + len(lines) * 62 + 10
        d.rounded_rectangle([60, y, 940, y + 12], 6, fill=(255, 255, 255, 45))
        d.rounded_rectangle([60, y, 60 + 880 * min(1, t / self.total), y + 12], 6, fill=YELLOW)

    def caption(self, im, s, t):
        cur = None
        for st, x in s["caps"]:
            if t >= st: cur = (st, x)
        if cur is None:
            if s is not self.segs[0]: return
            cur = s["caps"][0]
        st, x = cur; p = 1.0 if t < 0.3 else (t - st) / 0.12
        f = font(78, "Black"); lines = wrap(x, f, 840)
        bw = int(max(_dummy.textlength(l, font=f) for l in lines) + 70); bh = int(len(lines) * 94 + 40)
        box, bp = rr_image(bw, bh, 28, (10, 10, 30, 200))
        bd = ImageDraw.Draw(box)
        for k, ln in enumerate(lines):
            bd.text((bp + bw / 2, bp + 20 + 47 + k * 94), ln, font=f, fill=YELLOW, anchor="mm")
        paste(im, box, CX - bw // 2 - bp, CAP_Y - bp, scale=0.92 + 0.08 * ease_back(p))

    def draw(self, k, t_local, card):
        s = self.segs[k]; t = s["start"] + t_local; im = BG.copy()
        self.header(im, t)
        ci, cp = card; p = 1.0 if k == 0 and t < 0.5 else (t - s["start"]) / 0.35
        float_y = 6 * math.sin(t * 2 * math.pi / 3.0)
        paste(im, ci, CX - CARD_W // 2 - cp, CARD_Y - cp + float_y, alpha=min(1, p * 2), scale=0.75 + 0.25 * ease_back(p))
        if s.get("outro"):
            if t > s["t0"] + 0.4:
                lp = (t - s["t0"] - 0.4) / 0.35
                btn, bp = cta_button("+ ABONNE-TOI", 640, 110, 52)
                paste(im, btn, CX - 320 - bp, 1290 - bp, alpha=min(1, lp * 2), scale=(0.8 + 0.2 * ease_back(lp)) * (1 + 0.04 * math.sin(t * 2 * math.pi / 0.9)))
            nxt = "Demain : un nouveau quiz" if self.c.get("demain", "quiz") == "quiz" else "Demain : une nouvelle histoire"
            ImageDraw.Draw(im).text((CX, 1470), nxt, font=font(46, "Bold"), fill=SOFT, anchor="mm")
        self.caption(im, s, t)
        # rappel visuel d'abonnement à mi-parcours (sans voix)
        mid = self.total * 0.5
        if mid <= t < mid + 3.2 and not s.get("outro"):
            lp = (t - mid) / 0.35; out = max(0, (t - mid - 2.8) / 0.4)
            btn, bp = cta_button("+ Abonne-toi pour la suite", 620, 84, 38)
            paste(im, btn, CX - 310 - bp, 1360 - bp, alpha=min(1, lp * 2) * (1 - out), scale=0.85 + 0.15 * ease_back(lp))
        return im

    def frame_fn(self, name):
        k = int(name[1:]); card = self.card_img(self.segs[k])
        return lambda t: self.draw(k, t, card)

    def check_frames(self):
        out = [("s0", 0.0)]
        for k in (1, len(self.segs) // 2, len(self.segs) - 1):
            s = self.segs[k]; out.append((f"s{k}", s["t0"] - s["start"] + min(1.0, s["dur"] * 0.5)))
        return out

    def audio(self, tl, wav):
        tr = Track(self.total)
        for k, s in enumerate(self.segs):
            tr.add(tr.voice, load(f"{self.work}/s{k}.wav"), s["t0"])
            if k > 0: tr.add(tr.sfx, WHOOSH, s["start"], 0.12)
            tr.add(tr.sfx, POP, s["start"] + 0.12, 0.15)
        tr.add(tr.sfx, DING, self.segs[-1]["t0"] + 0.4, 0.2)
        mixdown(tr, wav, music_gain=0.5, soft=True)
