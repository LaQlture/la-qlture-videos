"""Vidéo « Histoire racontée » : un sujet raconté phrase par phrase, carte mot-clé + sous-titres synchronisés."""
import math, os, re
from PIL import Image, ImageDraw, ImageFilter, ImageOps
from common import *
from common import _dummy
import captions

CX = W // 2 - 30           # centre décalé à gauche (icônes TikTok à droite)
CARD_Y, CARD_W, CARD_H = 470, 880, 470
CAP_Y = 1110
# mode photo (segment avec "image") : photo au centre, fond flouté, mot-clé en étiquette
PH_Y, PH_W, PH_H = 430, 900, 780
CAP_Y_PHOTO = 1330
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
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
        # sous-titres : groupes de mots naturels, calés sur le début réel de chaque groupe dans la voix
        f = font(78, "Black")
        fits = lambda x: len(x) <= captions.MAX_CH and len(wrap(x, f, 840)) <= 2
        words = captions.align([(os.path.join(self.work, f"s{k}.wav"), s.get("tts", s["texte"])) for k, s in enumerate(self.segs)])
        print("sous-titres calés sur la voix" if words else "sous-titres au prorata (calage indisponible)", flush=True)
        for k, s in enumerate(self.segs):
            cs = captions.chunk_text(s["texte"], fits)
            ts = captions.caption_times(cs, s["t0"], s["dur"], words[k] if words else None)
            s["caps"] = list(zip(ts, cs))
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

    # ---------- mode photo ----------
    def photo_assets(self, s):
        """Prépare une fois par segment : fond flouté, photo source agrandie, étiquette du mot-clé."""
        src = Image.open(os.path.join(REPO, s["image"]))
        src = ImageOps.exif_transpose(src).convert("RGB")
        if "crop" in s:  # [gauche, haut, droite, bas] en fractions de l'image
            l, t, r, b = s["crop"]; src = src.crop((int(l * src.width), int(t * src.height), int(r * src.width), int(b * src.height)))
        # fond : image plein écran, floutée et assombrie
        bg = ImageOps.fit(src, (W // 4, H // 4), Image.BILINEAR).filter(ImageFilter.GaussianBlur(6)).resize((W, H), Image.BILINEAR)
        dark = Image.new("RGB", (W, H), (8, 8, 24))
        bg = Image.blend(bg, dark, 0.62).convert("RGBA")
        grad = Image.new("L", (1, H)); grad.putdata([int(150 * max(0, 1 - y / 520)) for y in range(H)])
        bg.alpha_composite(Image.merge("RGBA", [Image.new("L", (W, H), 0)] * 3 + [grad.resize((W, H))]))
        # photo : recadrée au format du cadre, avec 12 % de marge pour le zoom lent
        z = 1.12
        big = ImageOps.fit(src, (int(PH_W * z), int(PH_H * z)), Image.LANCZOS, centering=s.get("centre", (0.5, 0.5)))
        mask = Image.new("L", (PH_W * 2, PH_H * 2), 0)
        ImageDraw.Draw(mask).rounded_rectangle([0, 0, PH_W * 2 - 1, PH_H * 2 - 1], 80, fill=255)
        mask = mask.resize((PH_W, PH_H), Image.LANCZOS)
        shadow, sp = rr_image(PH_W, PH_H, 40, (0, 0, 0, 0), shadow=True)
        # étiquette (mot-clé)
        txt = s["carte"].upper(); f = font(64, "Black")
        while _dummy.textlength(txt, font=f) > PH_W - 120 and f.size > 40: f = font(f.size - 4, "Black")
        lw = int(_dummy.textlength(txt, font=f) + 80); lh = f.size + 44
        lab, lp = rr_image(lw, lh, lh // 2, s["color"], shadow=True)
        ImageDraw.Draw(lab).text((lp + lw / 2, lp + lh / 2 + 3), txt, font=f, fill=WHITE, anchor="mm")
        return dict(bg=bg, big=big, mask=mask, shadow=(shadow, sp), label=(lab, lp), z=z,
                    pan=s.get("pan", 0.6 if len(s["image"]) % 2 else -0.6))

    def photo_frame(self, im, s, a, t):
        k = min(1.0, max(0.0, (t - s["start"]) / max(0.5, s["end"] - s["start"])))
        e = k * k * (3 - 2 * k)
        x0, y0 = CX - PH_W // 2, PH_Y
        p = 1.0 if s is self.segs[0] and t < 0.5 else (t - s["start"]) / 0.35
        sc = 0.9 + 0.1 * ease_back(p)
        # zoom lent (Ken Burns) avec léger déplacement horizontal
        bw, bh = a["big"].size
        zoom = 1.03 + 0.08 * e
        cw, ch = bw / zoom, bh / zoom
        mx, my = (bw - cw) / 2, (bh - ch) / 2
        cx = mx + a["pan"] * mx * (2 * e - 1)
        box = (cx, my, cx + cw, my + ch)
        ph = a["big"].resize((PH_W, PH_H), Image.BILINEAR, box=box).convert("RGBA")
        ph.putalpha(a["mask"])
        shadow, sp = a["shadow"]
        paste(im, shadow, x0 - sp, y0 - sp, alpha=min(1, p * 2), scale=sc)
        paste(im, ph, x0, y0, alpha=min(1, p * 2), scale=sc)
        lab, lp = a["label"]
        lpp = (t - s["start"] - 0.25) / 0.35
        if lpp > 0:
            paste(im, lab, CX - lab.width // 2, y0 + PH_H - 60 - lp, alpha=min(1, lpp * 2), scale=0.8 + 0.2 * ease_back(lpp))
        if s.get("credit"):
            ImageDraw.Draw(im).text((x0 + PH_W - 10, y0 + PH_H + 62), s["credit"], font=font(22, "Bold"), fill=(255, 255, 255, 110), anchor="rm")

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
        if len(lines) == 2: lines = captions.balance(x, f, 840, _dummy.textlength) or lines
        bw = int(max(_dummy.textlength(l, font=f) for l in lines) + 70); bh = int(len(lines) * 94 + 40)
        box, bp = rr_image(bw, bh, 28, (10, 10, 30, 200))
        bd = ImageDraw.Draw(box)
        for k, ln in enumerate(lines):
            bd.text((bp + bw / 2, bp + 20 + 47 + k * 94), ln, font=f, fill=YELLOW, anchor="mm")
        cy = CAP_Y_PHOTO if s.get("image") else CAP_Y
        paste(im, box, CX - bw // 2 - bp, cy - bp, scale=0.92 + 0.08 * ease_back(p))

    def draw(self, k, t_local, card):
        s = self.segs[k]; t = s["start"] + t_local
        if s.get("image"):
            im = card["bg"].copy(); self.header(im, t); self.photo_frame(im, s, card, t)
        else:
            im = BG.copy()
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
            paste(im, btn, CX - 310 - bp, (PH_Y + 40 if s.get("image") else 1360) - bp, alpha=min(1, lp * 2) * (1 - out), scale=0.85 + 0.15 * ease_back(lp))
        return im

    def frame_fn(self, name):
        k = int(name[1:]); s = self.segs[k]
        card = self.photo_assets(s) if s.get("image") else self.card_img(s)
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
