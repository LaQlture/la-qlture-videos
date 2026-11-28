"""Découpage des sous-titres en groupes de mots naturels + calage sur les mots réellement prononcés."""
import itertools, json, os, re, subprocess, unicodedata

MAX_CH = 30          # longueur visée max d'un sous-titre (≤ 2 lignes à l'écran)
# mots qu'on ne laisse jamais en fin de sous-titre (articles, prépositions, conjonctions, pronoms sujets…)
SMALL = set("""le la les l' un une des de du d' à au aux en et ou ni sa son ses ce cet cette ces mon ma mes ton ta tes
deux trois quatre cinq six sept huit neuf dix vingt cent mille leur leurs notre nos votre vos sur sous par pour dans avec sans chez vers entre qui que qu' dont où ne n' se s' il ils
elle elles on je j' tu nous vous y me m' te t' lui c' ça très plus moins si comme mais donc car même tout toute tous""".split())
BREAK_BEFORE = set("et mais ou car donc pour avec dans sans qui que qu' quand puis comme alors parce".split())
END_PUNCT = re.compile(r"[,;:!?.…»]$")

NO_BREAK_BEFORE = set("de d' du des".split())

def _key(w):
    w = w.lower().replace("\u00a0", " ").strip(" ,;:!?.…«»\"()")
    if "'" in w:
        pre, rest = w.split("'", 1)
        return rest if rest in SMALL else w      # « d'un » finit mal, « l'argent » non
    return w

def _first(w):
    w = w.lower().strip(" ,;:!?.…«»\"()")
    return w.split("'", 1)[0] + "'" if "'" in w else w

def _cap(w): return w[:1].isupper()

def words_of(text):
    t = re.sub(r"\s+([!?:;»])", "\u00a0\\1", text.strip())
    t = re.sub(r"«\s+", "«\u00a0", t)
    t = re.sub(r"(\d)\s(\d{3})", "\\1\u00a0\\2", t)
    return t.split()

def chunk_text(text, fits=lambda s: len(s) <= MAX_CH):
    ws = words_of(text)
    # 1) propositions (coupure après la ponctuation)
    clauses, cur = [], []
    for w in ws:
        cur.append(w)
        if END_PUNCT.search(w.replace("\u00a0", "")): clauses.append(cur); cur = []
    if cur: clauses.append(cur)
    # 2) propositions très courtes (1-2 mots) : « Oui, » « Problème : » vont avec la suite, « Gustave Eiffel. » avec ce qui précède
    out, i = [], 0
    while i < len(clauses):
        c = clauses[i]
        if len(c) <= 2 and i + 1 < len(clauses) and re.search(r"[,:;]$", c[-1]) and fits(" ".join(c + clauses[i + 1])):
            clauses[i + 1] = c + clauses[i + 1]
        elif len(c) <= 2 and out and fits(" ".join(out[-1] + c)):
            out[-1] = out[-1] + c
        else:
            out.append(c)
        i += 1
    # 3) découpe équilibrée des propositions trop longues
    res = []
    for c in out:
        if fits(" ".join(c)): res.append(c); continue
        best, kmin = None, None
        for k in range(2, len(c) + 1):
            if kmin and k > kmin + 1: break
            for cuts in itertools.combinations(range(1, len(c)), k - 1):
                parts = [c[a:b] for a, b in zip((0,) + cuts, cuts + (len(c),))]
                if not all(fits(" ".join(p)) for p in parts): continue
                kmin = kmin or k
                L = [len(" ".join(p)) for p in parts]; avg = sum(L) / k
                cost = sum((l - avg) ** 2 for l in L) + 250 * k
                for p, q in zip(parts, parts[1:]):
                    if _key(p[-1]) in SMALL: cost += 600
                    if _first(q[0]) in NO_BREAK_BEFORE: cost += 300
                    if _first(q[0]) in BREAK_BEFORE: cost -= 60
                    if _cap(p[-1]) and _cap(q[0]): cost += 700          # nom propre coupé
                    if re.search(r"\d$", p[-1].replace("\u00a0", "")): cost += 300  # nombre séparé de son nom
                    if END_PUNCT.search(p[-1]): cost -= 120
                cost += sum(800 for p in parts if len(p) == 1)
                if best is None or cost < best[0]: best = (cost, parts)
        res.extend(best[1] if best else [c])
    return [" ".join(p) for p in res]

# ---------- calage sur la voix ----------
def _norm_tokens(text):
    from num2words import num2words
    t = text.replace("\u00a0", " ")
    t = re.sub(r"(\d+),(\d+)", lambda m: m[1] + " virgule " + m[2], t)
    t = re.sub(r"(\d)\s(\d{3})", r"\1\2", t)
    t = re.sub(r"\d+", lambda m: " " + num2words(int(m[0]), lang="fr") + " ", t)
    t = unicodedata.normalize("NFD", t.lower()); t = "".join(ch for ch in t if unicodedata.category(ch) != "Mn")
    return re.sub(r"[^a-z]+", " ", t.replace("-", " ")).split()

def align(jobs):
    """jobs = [(wav, texte attendu)] → liste de [(mot, début, fin)] par fichier, ou None si l'outil n'est pas installé."""
    py = os.path.expanduser(os.environ.get("CB_PYTHON", "~/.venvs/cb/bin/python"))
    if not os.path.exists(py): return None
    try:
        out = subprocess.run([py, os.path.join(os.path.dirname(os.path.abspath(__file__)), "align_words.py")],
                             input=json.dumps(jobs), capture_output=True, text=True, timeout=1800)
        return json.loads(out.stdout.strip().splitlines()[-1])
    except Exception:
        return None

def caption_times(chunks, t0, dur, words=None):
    """Instant d'apparition de chaque sous-titre : début réel du 1er mot (si calage dispo), sinon prorata des caractères."""
    w = [len(x) + 2 for x in chunks]; tot = sum(w); acc = 0; prop = []
    for x in w: prop.append(t0 + dur * acc / tot); acc += x
    if not words: return prop
    import difflib
    ref, owner = [], []
    for i, c in enumerate(chunks):
        toks = _norm_tokens(c); ref += toks; owner += [i] * len(toks)
    hyp, hs = [], []
    for word, st, en in words:
        for tk in _norm_tokens(word): hyp.append(tk); hs.append(st)
    sm = difflib.SequenceMatcher(a=ref, b=hyp, autojunk=False)
    tmap = {}
    for b in sm.get_matching_blocks():
        for j in range(b.size): tmap[b.a + j] = hs[b.b + j]
    starts = []
    for i in range(len(chunks)):
        idx = [k for k, o in enumerate(owner) if o == i]
        hit = next((tmap[k] - (idx.index(k) * 0.0) for k in idx if k in tmap), None)
        # si le 1er mot n'est pas reconnu, on recule depuis le 1er mot reconnu du groupe (≈ 0,28 s par mot)
        if hit is not None:
            k0 = next(k for k in idx if k in tmap); hit = tmap[k0] - 0.28 * (k0 - idx[0])
        starts.append(t0 + max(0.0, hit) if hit is not None else prop[i])
    starts[0] = t0
    for i in range(1, len(starts)):           # ordre croissant garanti
        starts[i] = max(starts[i], starts[i - 1] + 0.25)
    return [min(s, t0 + dur - 0.2) for s in starts]

def balance(text, f, maxw, textlength):
    """Coupe un sous-titre de 2 lignes à l'endroit le plus équilibré (sans finir la 1re ligne sur un petit mot)."""
    ws = text.split(" "); best = None
    for i in range(1, len(ws)):
        a, b = " ".join(ws[:i]), " ".join(ws[i:])
        la, lb = textlength(a, font=f), textlength(b, font=f)
        if max(la, lb) > maxw: continue
        cost = abs(la - lb) + (400 if _key(ws[i - 1]) in SMALL else 0) + (300 if _first(ws[i]) in NO_BREAK_BEFORE else 0)
        if best is None or cost < best[0]: best = (cost, [a, b])
    return best[1] if best else None
