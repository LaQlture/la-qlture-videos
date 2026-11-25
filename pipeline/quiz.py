"""Vidéo « Quiz » : 10 questions de facile à expert, rappel abonnement après la question 5."""
import math, os
from concurrent.futures import ProcessPoolExecutor
from PIL import Image, ImageDraw
from common import *
from common import _dummy

L = "ABC"
CX0, CW = 60, 880          # garde la colonne d'icônes TikTok à droite libre
QY, QH = 370, 360
OY, OH, OG = 790, 150, 28

INTRO_TTS = "Dix questions de culture générale, de plus en plus dures. Compte tes points !"
MID_TTS = "Tu es à la moitié ! Si tu aimes ces quiz, abonne-toi : il y a une nouvelle vidéo chaque jour. Allez, la suite est plus dure !"
OUTRO_TTS = "Alors, tu as eu combien ? Dis-le en commentaire, et abonne-toi pour la vidéo de demain !"

def check_icon(size, color):
    s = 4; im = Image.new("RGBA", (size * s, size * s), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.ellipse([0, 0, size * s - 1, size * s - 1], fill=WHITE)
    pts = [(0.27, 0.53), (0.43, 0.68), (0.73, 0.36)]
    d.line([(p[0] * size * s, p[1] * size * s) for p in pts], fill=color, width=int(size * s * 0.12), joint="curve")
    return im.resize((size, size), Image.LANCZOS)

class Quiz:
    def __init__(self, c, work):
        self.c, self.Q, self.work = c, c["questions"], work
        assert len(self.Q) == 10, "il faut exactement 10 questions"
        for q in self.Q:
            assert len(q["opts"]) == 3 and 0 <= q["ans"] <= 2 and q["level"] in LEVELS, q

    # ---------- voix ----------
    def voices(self):
        items = {"intro": INTRO_TTS, "mid": MID_TTS, "outro": OUTRO_TTS}
        for i, q in enumerate(self.Q, 1):
            items[f"q{i}"] = f"Question {i}. {q.get('tts_q', q['q'])}"
            items[f"a{i}"] = f"Réponse {L[q['ans']]} : {q['tts_ans']}"
        self.DUR = {k: say(t, os.path.join(self.work, f"{k}.wav")) for k, t in items.items()}

    # ---------- timings ----------
    def q_timing(self, i):
        qd, ad = self.DUR[f"q{i}"], self.DUR[f"a{i}"]
        t_cd = max(0.25 + qd + 0.35, 1.9); t_rev = t_cd + 3.0; t_ans = t_rev + 0.2
        return dict(t_voice=0.25, t_cd=t_cd, t_rev=t_rev, t_ans=t_ans, end=round((t_ans + ad + 0.6) * FPS) / FPS)

    def timeline(self):
        r = lambda x: round(x * FPS) / FPS
        tl = [("intro", r(0.2 + self.DUR["intro"] + 0.45))]
        for i in range(1, 11):
            tl.append((f"q{i}", self.q_timing(i)["end"]))
            if i == 5: tl.append(("mid", r(0.3 + self.DUR["mid"] + 0.6)))
        tl.append(("outro", r(0.3 + self.DUR["outro"] + 1.6)))
        return tl

    # ---------- dessin ----------
    def assets(self, q):
        a = {}
        qc, pad = rr_image(CW, QH, 36, WHITE, shadow=True); dr = ImageDraw.Draw(qc)
        f = font(64); lines = wrap(q["q"], f, CW - 110)
        if len(lines) > 3: f = font(54); lines = wrap(q["q"], f, CW - 100)
        lh = f.size * 1.22; y0 = pad + QH / 2 - lh * (len(lines) - 1) / 2
        for k, ln in enumerate(lines): dr.text((pad + CW / 2, y0 + k * lh), ln, font=f, fill=NAVY, anchor="mm")
        a["q"], a["qpad"] = qc, pad
        for k, o in enumerate(q["opts"]):
            for state in ("normal", "correct", "wrong"):
                if state == "correct": im, p = rr_image(CW, OH, 34, GREEN, border=(160, 255, 200), bw=5, shadow=True)
                elif state == "wrong": im, p = rr_image(CW, OH, 34, (40, 36, 70), border=(70, 60, 110), bw=3, shadow=True)
                else: im, p = rr_image(CW, OH, 34, CARD, border=CARD_BORDER, bw=3, shadow=True)
                dr = ImageDraw.Draw(im); bx, by, br = p + 80, p + OH / 2, 44
                bub, _ = rr_image(br * 2, br * 2, br, WHITE if state == "correct" else ACCENT if state == "normal" else (70, 62, 110))
                im.alpha_composite(bub, (int(bx - br), int(by - br)))
                dr.text((bx, by + 2), L[k], font=font(50, "Black"), fill=GREEN if state == "correct" else WHITE if state == "normal" else (150, 140, 180), anchor="mm")
                fo = font(56 if len(o) < 16 else 46, "Bold")
                dr.text((p + 150, by + 2), o, font=fo, fill=WHITE if state != "wrong" else (140, 130, 170), anchor="lm")
                if state == "correct": im.alpha_composite(check_icon(78, GREEN), (p + CW - 110, int(by - 39)))
                a[(k, state)], a["opad"] = im, p
        return a

    def header(self, base, i, level):
        d = ImageDraw.Draw(base)
        d.text((CX0, 215), "QUESTION", font=font(40, "Bold"), fill=(200, 200, 255), anchor="lm")
        qw = d.textlength("QUESTION ", font=font(40, "Bold"))
        d.text((CX0 + qw, 215), f"{i}", font=font(60, "Black"), fill=WHITE, anchor="lm")
        nw = d.textlength(f"{i}", font=font(60, "Black"))
        d.text((CX0 + qw + nw + 6, 220), "/10", font=font(40, "Bold"), fill=(200, 200, 255), anchor="lm")
        fl = font(36, "Black"); tw = d.textlength(level, font=fl)
        pill, _ = rr_image(int(tw + 60), 64, 32, LEVELS[level])
        base.alpha_composite(pill, (int(CX0 + CW - tw - 60), 183))
        d.text((CX0 + CW - (tw + 60) / 2, 216), level, font=fl, fill=(20, 20, 30), anchor="mm")
        self.progress(d, i, 285, 14)

    def progress(self, d, done, y, h):
        seg = (CW - 9 * 10) / 10
        for k in range(10):
            x = CX0 + k * (seg + 10)
            d.rounded_rectangle([x, y, x + seg, y + h], h // 2, fill=LEVELS[self.Q[k]["level"]] if k < done else (255, 255, 255, 40))

    def timer(self, base, t_in, total=3.0):
        s = 2; R = 86; size = (R + 14) * 2
        im = Image.new("RGBA", (size * s, size * s), (0, 0, 0, 0)); d = ImageDraw.Draw(im); c = size * s / 2
        d.ellipse([c - R * s, c - R * s, c + R * s, c + R * s], fill=(20, 22, 60, 235), outline=(255, 255, 255, 50), width=10 * s)
        frac = max(0.0, 1 - t_in / total); n = min(3, int(math.ceil(total - t_in - 1e-6)))
        col = [GREEN, YELLOW, (255, 80, 80)][3 - max(n, 1)]
        if frac > 0: d.arc([c - R * s, c - R * s, c + R * s, c + R * s], -90, -90 + 360 * frac, fill=col, width=12 * s)
        im = im.resize((size, size), Image.LANCZOS); dd = ImageDraw.Draw(im)
        sc = 1 + 0.25 * max(0, 1 - (t_in % 1.0) / 0.25)
        dd.text((size / 2, size / 2 + 3), str(max(n, 1)), font=font(int(78 * sc), "Black"), fill=WHITE, anchor="mm")
        base.alpha_composite(im, (W // 2 - 50 - size // 2, 1430 - size // 2))

    def fact_pill(self, base, text, p):
        f = font(44, "Bold"); tw = _dummy_len(text, f); w = int(tw + 80)
        im, pad = rr_image(w, 96, 48, YELLOW)
        ImageDraw.Draw(im).text((pad + w / 2, pad + 50), text, font=f, fill=(25, 20, 40), anchor="mm")
        paste(base, im, W // 2 - 50 - w // 2 - pad, 1385 - pad, alpha=ease_out(p), scale=0.85 + 0.15 * ease_back(p))

    def draw_q(self, i, t, A, T):
        q = self.Q[i - 1]; im = BG.copy(); self.header(im, i, q["level"])
        paste(im, A["q"], CX0 - A["qpad"], QY - A["qpad"] + (1 - ease_out(t / 0.3)) * 60, alpha=min(1, t / 0.2), scale=0.9 + 0.1 * ease_back(t / 0.35))
        for k in range(3):
            ts = 0.45 + 0.15 * k
            if t < ts: continue
            lp = (t - ts) / 0.3; y = OY + k * (OH + OG) - A["opad"]; x = CX0 - A["opad"] + (1 - ease_out(lp)) * 400
            if t >= T["t_rev"]:
                rp = t - T["t_rev"]
                if k == q["ans"]: paste(im, A[(k, "correct")], x, y, scale=1 + 0.08 * math.sin(min(rp / 0.35, 1) * math.pi))
                else: paste(im, A[(k, "wrong")], x, y, alpha=1 - 0.45 * min(rp / 0.25, 1))
            else: paste(im, A[(k, "normal")], x, y, alpha=min(1, lp * 1.5))
        if T["t_cd"] <= t < T["t_rev"]: self.timer(im, t - T["t_cd"])
        elif t >= T["t_rev"] and q.get("fact"): self.fact_pill(im, q["fact"], (t - T["t_rev"] - 0.25) / 0.35)
        if T["t_rev"] <= t < T["t_rev"] + 0.15:
            im.alpha_composite(Image.new("RGBA", (W, H), (120, 255, 170, int(70 * (1 - (t - T["t_rev"]) / 0.15)))))
        return im

    def draw_intro(self, t):
        im = BG.copy(); d = ImageDraw.Draw(im); cx = W // 2 - 30
        pill, _ = rr_image(520, 76, 38, ACCENT); im.alpha_composite(pill, (cx - 260, 300))
        d.text((cx, 339), "QUIZ CULTURE G", font=font(40, "Black"), fill=WHITE, anchor="mm")
        big = Image.new("RGBA", (1000, 360), (0, 0, 0, 0)); bd = ImageDraw.Draw(big)
        bd.text((500, 110), "10", font=font(200, "Black"), fill=YELLOW, anchor="mm")
        bd.text((500, 285), "QUESTIONS", font=font(112, "Black"), fill=WHITE, anchor="mm")
        paste(im, big, cx - 500, 430, scale=1 + 0.03 * math.sin(t * 2 * math.pi / 1.2))
        d.text((cx, 860), "de la plus facile", font=font(52, "SemiBold"), fill=SOFT, anchor="mm")
        d.text((cx, 930), "à la plus difficile", font=font(52, "SemiBold"), fill=SOFT, anchor="mm")
        names = list(LEVELS); bw, gap = 190, 18; x0 = cx - (4 * bw + 3 * gap) // 2
        for k, n in enumerate(names):
            h = 90 + k * 70; p = 1.0 if t == 0 else ease_back((t - 0.15 - 0.12 * k) / 0.35)
            hh = int(h * p)
            if hh > 4:
                bar, _ = rr_image(bw, hh, 20, LEVELS[n]); im.alpha_composite(bar, (x0 + k * (bw + gap), 1300 - hh))
            d.text((x0 + k * (bw + gap) + bw // 2, 1345), n, font=font(30, "Black"), fill=LEVELS[n], anchor="mm")
        d.text((cx, 1460), "TU FAIS COMBIEN SUR 10 ?", font=font(58, "Black"), fill=WHITE, anchor="mm")
        return im

    def draw_mid(self, t):
        im = BG.copy(); d = ImageDraw.Draw(im); cx = W // 2 - 30; p = ease_back(t / 0.4)
        big = Image.new("RGBA", (1000, 220), (0, 0, 0, 0)); bd = ImageDraw.Draw(big)
        bd.text((500, 70), "TU ES À LA", font=font(70, "Black"), fill=WHITE, anchor="mm")
        bd.text((500, 165), "MOITIÉ !", font=font(120, "Black"), fill=YELLOW, anchor="mm")
        paste(im, big, cx - 500, 330, scale=max(0.05, 0.6 + 0.4 * p))
        seg = (CW - 9 * 10) / 10
        for k in range(10):
            x = CX0 + k * (seg + 10)
            d.rounded_rectangle([x, 640, x + seg, 660], 10, fill=LEVELS[self.Q[k]["level"]] if k < 5 else (255, 255, 255, 40))
        d.text((cx, 710), "5 / 10", font=font(44, "Black"), fill=SOFT, anchor="mm")
        if t > 0.9:
            lp = (t - 0.9) / 0.35
            d.text((cx, 900), "Tu aimes ces quiz ?", font=font(64, "Black"), fill=WHITE, anchor="mm")
            btn, bp = cta_button("+ ABONNE-TOI", 700, 130, 60)
            paste(im, btn, cx - 350 - bp, 990 - bp, alpha=min(1, lp * 2), scale=(0.8 + 0.2 * ease_back(lp)) * (1 + 0.05 * math.sin((t - 0.9) * 2 * math.pi / 0.9)))
            d.text((cx, 1190), "Une nouvelle vidéo chaque jour", font=font(46, "SemiBold"), fill=SOFT, anchor="mm")
        if t > 3.6:
            lp = (t - 3.6) / 0.35
            pill, pp = rr_image(760, 96, 48, LEVELS["DIFFICILE"])
            ImageDraw.Draw(pill).text((pp + 380, pp + 50), "La suite est plus dure...", font=font(46, "Black"), fill=(25, 20, 40), anchor="mm")
            paste(im, pill, cx - 380 - pp, 1330 - pp, alpha=min(1, lp * 2), scale=0.85 + 0.15 * ease_back(lp))
        return im

    def draw_outro(self, t):
        im = BG.copy(); d = ImageDraw.Draw(im); cx = W // 2 - 30; p = ease_back(t / 0.4)
        big = Image.new("RGBA", (1000, 200), (0, 0, 0, 0))
        ImageDraw.Draw(big).text((500, 100), "C'EST FINI !", font=font(120, "Black"), fill=YELLOW, anchor="mm")
        paste(im, big, cx - 500, 300, scale=max(0.05, 0.6 + 0.4 * p))
        d.text((cx, 560), "Ton score ?", font=font(76, "Black"), fill=WHITE, anchor="mm")
        rows = [("10/10", "Génie", LEVELS["EXPERT"]), ("8-9", "Expert", LEVELS["DIFFICILE"]), ("5-7", "Bon niveau", LEVELS["MOYEN"]), ("0-4", "Débutant", LEVELS["FACILE"])]
        for k, (s, n, c) in enumerate(rows):
            ts = 0.35 + 0.15 * k
            if t < ts: continue
            lp = (t - ts) / 0.3; card, cp = rr_image(760, 112, 30, CARD, border=c, bw=4); dr = ImageDraw.Draw(card)
            dr.text((cp + 50, cp + 58), s, font=font(52, "Black"), fill=c, anchor="lm")
            dr.text((cp + 710, cp + 58), n, font=font(50, "Bold"), fill=WHITE, anchor="rm")
            paste(im, card, cx - 380 - cp + (1 - ease_out(lp)) * 300, 680 + k * 140 - cp, alpha=min(1, lp * 1.5))
        if t > 1.2:
            lp = (t - 1.2) / 0.35
            d.text((cx, 1300), "Dis-le en commentaire !", font=font(60, "Black"), fill=WHITE, anchor="mm")
            btn, bp = cta_button("+ ABONNE-TOI", 640, 110, 52)
            paste(im, btn, cx - 320 - bp, 1380 - bp, alpha=min(1, lp * 2), scale=0.8 + 0.2 * ease_back(lp))
            d.text((cx, 1540), "Nouvelle vidéo chaque jour", font=font(40, "SemiBold"), fill=SOFT, anchor="mm")
        return im

    def frame_fn(self, name):
        if name == "intro": return self.draw_intro
        if name == "mid": return self.draw_mid
        if name == "outro": return self.draw_outro
        i = int(name[1:]); A = self.assets(self.Q[i - 1]); T = self.q_timing(i)
        return lambda t: self.draw_q(i, t, A, T)

    def check_frames(self):
        """Moments les plus chargés, pour vérification visuelle avant publication."""
        out = [("intro", 0.0), ("mid", 4.5), ("outro", 3.0)]
        for i in (1, 7, 10):
            T = self.q_timing(i); out += [(f"q{i}", T["t_cd"] + 1.3), (f"q{i}", T["t_rev"] + 1.0)]
        return out

    # ---------- audio ----------
    def audio(self, tl, wav):
        total = sum(d for _, d in tl); tr = Track(total); t0 = 0.0
        for name, dur in tl:
            if name == "intro": tr.add(tr.voice, load(f"{self.work}/intro.wav"), t0 + 0.2)
            elif name in ("mid", "outro"):
                tr.add(tr.sfx, WHOOSH, t0, 0.25); tr.add(tr.voice, load(f"{self.work}/{name}.wav"), t0 + 0.3)
                if name == "outro": tr.add(tr.sfx, DING, t0 + 1.2, 0.25)
            else:
                i = int(name[1:]); T = self.q_timing(i)
                tr.add(tr.sfx, WHOOSH, t0, 0.25); tr.add(tr.voice, load(f"{self.work}/q{i}.wav"), t0 + T["t_voice"])
                for k in range(3): tr.add(tr.sfx, TICK if k % 2 == 0 else TOCK, t0 + T["t_cd"] + k, 0.5)
                tr.add(tr.sfx, DING, t0 + T["t_rev"], 0.45); tr.add(tr.voice, load(f"{self.work}/a{i}.wav"), t0 + T["t_ans"])
            t0 += dur
        mixdown(tr, wav)

def _dummy_len(text, f):
    return _dummy.textlength(text, font=f)
