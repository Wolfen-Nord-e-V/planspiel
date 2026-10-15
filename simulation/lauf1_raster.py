"""
Regel-Simulation „Wer baut Wolfen-Nord?“ – Stand der Spielanleitung vom 14.10.2026.

Spielt viele Partien mit einfachen, kooperativen Strategien durch, um die Zahlen
zu prüfen (Kümmerzeit, Mittel, Fläche, Ziele). Verhandlungen, Veto und das
Teilen in der Konfliktrunde sind NICHT modelliert – die werden am Tisch ausgehandelt.

Alle Werte, die in der Anleitung noch offen sind, stehen als Platzhalter in ANNAHMEN.
"""
import random, itertools, statistics, json, sys
from collections import Counter, defaultdict

# ---------------------------------------------------------------- Annahmen
ANNAHMEN = dict(
    personen_pro_gruppe=2,       # 8 Personen am Tisch (Plan A)
    runden=3,
    mittel_nachschub=2,          # pro Person und Runde
    kuemmer_kurs=3,              # so viele Mittel kostet 1 Kümmerzeit (offen!)
    ereignisse=True,
    karten_pro_typ=2,            # Exemplare je Baukarte im Set
    raster=(4, 4),               # 16 Felder, davon 2 Bestand
    nachbar_reichweite_treff=2,  # „5 Minuten“ = 2 Felder (Wollfaden)
)

GRUPPEN = {  # Mittel, Kümmerzeit
    "Bleibende": (2, 2),
    "Ankommende": (2, 1),
    "Rahmengebende": (5, 1),
    "Kuemmernde": (1, 4),
}

# Karte: (Mittel, Kümmer, Tags, erlaubte Flächentypen)
FREI = {"Bau", "Gruen"}
INNEN = {"Bau", "Gebaeude"}
ALLE = {"Bau", "Gruen", "Gebaeude"}
KARTEN = {
    "Kartoffelacker": (1, 1, {"Gruen", "Essen"}, FREI),
    "SoLaWi-Parzelle": (2, 2, {"Gruen", "Essen"}, FREI),
    "Bluehwiese": (1, 0, {"Gruen", "Kinder"}, FREI),
    "Streuobstwiese": (1, 1, {"Gruen", "Alt"}, FREI),
    "Imkerei": (1, 1, {"Gruen", "Handwerk"}, FREI),
    "Regenrueckhalt": (2, 0, {"Gruen"}, FREI),
    "Spielplatz": (2, 0, {"Kinder"}, FREI),
    "Bolzplatz": (1, 0, {"Jung"}, FREI),
    "Werkstatt": (2, 2, {"Handwerk", "Jung", "Alt"}, INNEN),
    "Kleingewerbe-Hof": (2, 1, {"Handwerk"}, INNEN),
    "Jugendtreff": (1, 2, {"Jung", "Begegnung"}, INNEN),
    "MehrGen-Cafe": (2, 2, {"Alt", "Kinder", "Begegnung"}, INNEN),
    "Gemeinschaftskueche": (2, 2, {"Essen", "Begegnung"}, INNEN),
    "Tauschschrank": (0, 1, {"Begegnung"}, ALLE),
    "Freiluftbuehne": (2, 1, {"Begegnung", "Jung"}, FREI),
    "Rufbus": (3, 1, {"Weg"}, ALLE),
    "Wege+Baenke": (2, 0, {"Weg", "Alt"}, ALLE),
    "Umbau Leerstand": (3, 1, {"Wohnen"}, {"Gebaeude"}),
    "Gemeinschaftswohnen": (3, 2, {"Wohnen", "Alt", "Jung"}, {"Bau"}),
}
EINNAHMEN = {"Kleingewerbe-Hof", "SoLaWi-Parzelle", "MehrGen-Cafe"}

# ---------------------------------------------------------------- Ziele
def nachbarn(pos, W, H, r=1):
    x, y = pos
    for dx in range(-r, r + 1):
        for dy in range(-r, r + 1):
            if (dx or dy) and abs(dx) + abs(dy) <= r and 0 <= x + dx < W and 0 <= y + dy < H:
                yield (x + dx, y + dy)

def tags_at(spiel, p):
    c = spiel["belegt"].get(p)
    if c is None: return set()
    if c["aktiv"] is False: return set()
    return c["tags"]

def ziel_generationen(s):
    for p, c in s["belegt"].items():
        if not c["aktiv"]: continue
        t = set(c["tags"])
        for n in nachbarn(p, *s["WH"]): t |= tags_at(s, n)
        if {"Kinder", "Jung", "Alt"} <= t: return True
    return False

def ziel_treff(s):
    wohn = [p for p, c in s["belegt"].items() if c["aktiv"] and "Wohnen" in c["tags"]]
    if not wohn: return None  # nicht prüfbar
    r = s["A"]["nachbar_reichweite_treff"]
    return all(any("Begegnung" in tags_at(s, n) for n in nachbarn(w, *s["WH"], r=r)) for w in wohn)

def ziel_weiterlauf(s):
    return any(c["aktiv"] and c["gebunden"] > 0 and not c.get("bestand") for c in s["belegt"].values())

def ziel_kein_chip(s):
    return sum(sp["k"] for sp in s["spieler"]) == 0

def ziel_einnahmen(s):
    return any(c["aktiv"] and c["name"] in EINNAHMEN for c in s["belegt"].values())

def ziel_84er(s):
    return sum(1 for n in nachbarn(s["pos84"], *s["WH"]) if n in s["belegt"] and s["belegt"][n]["aktiv"]) >= 2

def ziel_gruen(s):
    total = len(s["felder"])
    bebaut = sum(1 for p, c in s["belegt"].items() if c["aktiv"] and "Gruen" not in c["tags"])
    return bebaut <= total / 2

def ziel_jede_gruppe(s):
    gelegt = {c["gruppe"] for c in s["belegt"].values() if not c.get("bestand")}
    return set(GRUPPEN) <= gelegt

ZIELE = {
    "Drei Generationen": ziel_generationen,
    "Treffpunkt 5 Min": ziel_treff,
    "Läuft nach Förderende": ziel_weiterlauf,
    "Kein Chip übrig": ziel_kein_chip,
    "Einnahmen": ziel_einnahmen,
    "84er verbunden": ziel_84er,
    "Hälfte grün/offen": ziel_gruen,
    "Jede Gruppe gelegt": ziel_jede_gruppe,
}

# ---------------------------------------------------------------- Wünsche
def aktiv(s, name): return any(c["aktiv"] and c["name"] == name for c in s["belegt"].values())
def aktiv_tag(s, tag): return any(c["aktiv"] and tag in c["tags"] and not c.get("bestand") for c in s["belegt"].values())

WUENSCHE = {  # Bedingung, ungefähre Kümmerzeit, um ihn zu erfüllen
    "Weg zum Kaufmarkt": (lambda s: aktiv_tag(s, "Weg"), 0),
    "Kein Gewerbehof": (lambda s: not aktiv(s, "Kleingewerbe-Hof"), 0),
    "Trampelpfad bleibt": (lambda s: any(t == "Gruen" and p not in s["belegt"] for p, t in s["felder"].items()), 0),
    "Abends was los": (lambda s: any(aktiv(s, n) for n in ["Jugendtreff", "MehrGen-Cafe", "Freiluftbuehne", "Gemeinschaftskueche"]), 1),
    "Ort für Kinder": (lambda s: aktiv(s, "Spielplatz") or aktiv(s, "Bluehwiese"), 0),
    "Tiny House / Jurte": (lambda s: aktiv_tag(s, "Wohnen"), 1),
    "Kein Leerstand": (lambda s: aktiv(s, "Umbau Leerstand"), 1),
    "Keine Dauerlast": (lambda s: all(c["aktiv"] for c in s["belegt"].values()), 0),
    "Max. zwei Orte": (lambda s: True, 0),  # nicht sinnvoll simulierbar
    "Verein sichtbar": (lambda s: any("Begegnung" in tags_at(s, n) for n in nachbarn(s["pos84"], *s["WH"])), 1),
}
WUNSCH_ZIELKARTEN = {
    "Weg zum Kaufmarkt": ["Wege+Baenke", "Rufbus"], "Abends was los": ["Freiluftbuehne", "Jugendtreff", "MehrGen-Cafe"],
    "Ort für Kinder": ["Spielplatz", "Bluehwiese"], "Tiny House / Jurte": ["Gemeinschaftswohnen", "Umbau Leerstand"],
    "Kein Leerstand": ["Umbau Leerstand"], "Verein sichtbar": ["Freiluftbuehne", "Tauschschrank", "Jugendtreff"],
}

# ---------------------------------------------------------------- Spielaufbau
def neues_spiel(A, rng):
    W, H = A["raster"]
    alle = [(x, y) for x in range(W) for y in range(H)]
    rng.shuffle(alle)
    n = len(alle)
    typen = ["Gebaeude"] * max(2, n // 6) + ["Gruen"] * (n // 3)
    typen += ["Bau"] * (n - len(typen))
    felder = dict(zip(alle, typen))
    s = dict(A=A, WH=(W, H), felder=felder, belegt={}, log=Counter())
    # Bestand: 84er (Gebäude) und Gemeinschaftsgarten (Grün)
    p84 = next(p for p, t in felder.items() if t == "Gebaeude")
    pg = next(p for p, t in felder.items() if t == "Gruen")
    s["pos84"] = p84
    s["belegt"][p84] = dict(name="84er", tags={"Begegnung", "Jung"}, aktiv=True, gebunden=0, gruppe=None, bestand=True, bonus_gegeben=False)
    s["belegt"][pg] = dict(name="Gemeinschaftsgarten", tags={"Gruen", "Essen"}, aktiv=True, gebunden=0, gruppe=None, bestand=True, bonus_gegeben=False)
    spieler = []
    for g, (m, k) in GRUPPEN.items():
        for i in range(A["personen_pro_gruppe"]):
            spieler.append(dict(gruppe=g, m=m, k=k, wunsch=rng.choice(list(WUENSCHE)), extra_frei=(g == "Ankommende")))
    s["spieler"] = spieler
    deck = [k for k in KARTEN for _ in range(A["karten_pro_typ"])]
    s["deck"] = Counter(deck)
    s["ziele"] = rng.sample(list(ZIELE), 3)
    return s

def freie_felder(s, erlaubt):
    return [p for p, t in s["felder"].items() if p not in s["belegt"] and t in erlaubt]

def bonus(s, p, tags):
    for n in nachbarn(p, *s["WH"]):
        c = s["belegt"].get(n)
        if c and c["aktiv"] and not c["bonus_gegeben"] and (c["tags"] & tags):
            return n
    return None

def kosten(s, sp, name, p):
    m, k, tags, _ = KARTEN[name]
    partner = bonus(s, p, tags) if k > 0 else None
    if partner is not None: k -= 1
    return m, k, partner

def bezahlbar(s, sp, m, k, leihen=True):
    """Kann der Spieler (mit Leihen bei Kümmernden und Kauf von Kümmerzeit) zahlen?"""
    fehl_k = max(0, k - sp["k"])
    if fehl_k and leihen:
        pool = sum(o["k"] for o in s["spieler"] if o is not sp and o["gruppe"] == "Kuemmernde")
        geliehen = min(fehl_k, pool)
    else:
        geliehen = 0
    rest = fehl_k - geliehen
    kauf = rest * s["A"]["kuemmer_kurs"]
    return sp["m"] >= m + kauf, geliehen, rest

def zahlen(s, sp, m, k):
    ok, geliehen, kauf = bezahlbar(s, sp, m, k)
    eigen = k - geliehen - kauf
    sp["k"] -= eigen
    for o in s["spieler"]:
        if geliehen == 0: break
        if o is not sp and o["gruppe"] == "Kuemmernde":
            x = min(o["k"], geliehen); o["k"] -= x; geliehen -= x
            s["log"]["geliehen"] += x
    sp["m"] -= m + kauf * s["A"]["kuemmer_kurs"]
    s["log"]["kuemmer_gekauft"] += kauf

def bewertung(s, sp, name, p, rng, offen, n84):
    tags = KARTEN[name][2]
    w = rng.random()  # etwas Zufall: Menschen sind nicht optimal
    if name in WUNSCH_ZIELKARTEN.get(sp["wunsch"], []): w += 3
    if sp["wunsch"] == "Kein Gewerbehof" and name == "Kleingewerbe-Hof": w -= 10
    if "Einnahmen" in offen and name in EINNAHMEN: w += 2
    if "84er verbunden" in offen and p in n84: w += 2
    if "Treffpunkt 5 Min" in offen and "Begegnung" in tags: w += 1
    if "Drei Generationen" in offen and tags & {"Kinder", "Jung", "Alt"}: w += 1
    if "Hälfte grün/offen" in s["ziele"] and "Gruen" in tags: w += 1
    if "Läuft nach Förderende" in offen and KARTEN[name][1] > 0: w += 1
    if "Kein Chip übrig" in s["ziele"] and KARTEN[name][1] > 0: w += 1.5
    return w

def zug(s, sp, rng):
    optionen = []
    grund = Counter()
    offen = [z for z in s["ziele"] if not ZIELE[z](s)]
    n84 = set(nachbarn(s["pos84"], *s["WH"]))
    for name, anz in s["deck"].items():
        if anz <= 0: continue
        felder = freie_felder(s, KARTEN[name][3])
        if not felder: grund["platz"] += 1; continue
        for p in felder:
            m, k, partner = kosten(s, sp, name, p)
            ok, _, _ = bezahlbar(s, sp, m, k)
            if not ok:
                grund["mittel" if sp["m"] < m else "kuemmer"] += 1; continue
            optionen.append((bewertung(s, sp, name, p, rng, offen, n84), name, p, m, k, partner))
    if not optionen:
        s["log"]["passen"] += 1
        hauptgrund = grund.most_common(1)[0][0] if grund else "deck_leer"
        s["log"]["passen_" + hauptgrund] += 1
        return False
    optionen.sort(key=lambda o: o[0], reverse=True)
    _, name, p, m, k, partner = optionen[0]
    zahlen(s, sp, m, k)
    s["deck"][name] -= 1
    s["belegt"][p] = dict(name=name, tags=set(KARTEN[name][2]), aktiv=True, gebunden=k, gruppe=sp["gruppe"], bestand=False, bonus_gegeben=False, besitzer=id(sp))
    if partner is not None:
        s["belegt"][partner]["bonus_gegeben"] = True
        s["log"]["kombibonus"] += 1
    s["log"]["karte_" + name] += 1
    return True

# ---------------------------------------------------------------- Ereignisse
def besitzer(s, c):
    return next((sp for sp in s["spieler"] if id(sp) == c.get("besitzer")), None)

def ereignis(s, rng):
    namen = ["Förderprogramm endet", "Kümmerin zieht weg", "Dürresommer", "Starkregen", "Zwanzig neue Nachbarn",
             "Spende", "Fläche nur für ein Jahr", "Sommerfest", "Kita braucht Fläche", "Sanierung"]
    e = rng.choice(namen); s["log"]["ev_" + e] += 1
    karten = [(p, c) for p, c in s["belegt"].items() if not c.get("bestand") and c["aktiv"]]
    if e == "Förderprogramm endet":
        for g in GRUPPEN:
            sp = next(x for x in s["spieler"] if x["gruppe"] == g and True)
            sp["m"] = max(0, sp["m"] - 1)
    elif e == "Kümmerin zieht weg":
        sp = rng.choice(s["spieler"])
        if sp["k"] > 0: sp["k"] -= 1
        else: s["log"]["notbetrieb"] += 1
    elif e == "Dürresommer":
        for p, c in karten:
            if "Gruen" in c["tags"]:
                o = besitzer(s, c)
                if o and o["k"] > 0: o["k"] -= 1; c["gebunden"] += 1
                else: c["aktiv"] = False; s["log"]["umgedreht"] += 1
    elif e == "Starkregen":
        if not aktiv(s, "Regenrueckhalt"):
            for p, c in karten:
                if "Weg" in c["tags"]: c["aktiv"] = False; s["log"]["umgedreht"] += 1
    elif e == "Zwanzig neue Nachbarn":
        for p, c in karten:
            if "Wohnen" in c["tags"] and any("Begegnung" in tags_at(s, n) for n in nachbarn(p, *s["WH"])):
                o = besitzer(s, c)
                if o: o["k"] += 1
    elif e == "Spende":
        rng.choice(s["spieler"])["m"] += 3
    elif e == "Fläche nur für ein Jahr":
        if karten:
            p, c = rng.choice(karten); o = besitzer(s, c)
            if o and o["m"] >= 1: o["m"] -= 1
            else:
                if o: o["k"] += c["gebunden"]
                del s["belegt"][p]; s["log"]["geraeumt"] += 1
    elif e == "Sommerfest":
        for p, c in karten:
            if "Begegnung" in c["tags"]:
                o = besitzer(s, c)
                if o: o["m"] += 1
    elif e == "Kita braucht Fläche":
        if karten and not freie_felder(s, ALLE):
            p, c = rng.choice(karten); o = besitzer(s, c)
            if o: o["k"] += c["gebunden"]
            del s["belegt"][p]; s["log"]["geraeumt"] += 1
    elif e == "Sanierung":
        for p, c in karten:
            if "Wohnen" in c["tags"]:
                o = besitzer(s, c)
                if o and o["m"] >= 1: o["m"] -= 1
                else: c["aktiv"] = False; s["log"]["umgedreht"] += 1

# ---------------------------------------------------------------- Partie
def partie(A, rng):
    s = neues_spiel(A, rng)
    k_start = sum(sp["k"] for sp in s["spieler"])
    for r in range(A["runden"]):
        for sp in s["spieler"]:
            sp["m"] += A["mittel_nachschub"]
        reihenfolge = s["spieler"][:]; rng.shuffle(reihenfolge)
        for sp in reihenfolge:
            zug(s, sp, rng)
            if sp["extra_frei"] and r == A["runden"] - 2:
                if zug(s, sp, rng): sp["extra_frei"] = False
        if A["ereignisse"]:
            ereignis(s, rng)
    erg = {}
    for z in s["ziele"]:
        erg[z] = ZIELE[z](s)
    w = [WUENSCHE[sp["wunsch"]][0](s) for sp in s["spieler"]]
    bedarf = sum(WUENSCHE[sp["wunsch"]][1] for sp in s["spieler"])
    return dict(
        ziele=erg,
        gewonnen=all(v is True for v in erg.values()),
        wuensche=sum(w) / len(w),
        k_start=k_start,
        k_frei_ende=sum(sp["k"] for sp in s["spieler"]),
        m_ende=sum(sp["m"] for sp in s["spieler"]),
        karten=sum(1 for c in s["belegt"].values() if not c.get("bestand")),
        felder=len(s["felder"]) - 2,
        bedarf=bedarf,
        log=s["log"],
    )

def szenario(A, n=1500, seed=1):
    rng = random.Random(seed)
    res = [partie(A, rng) for _ in range(n)]
    ziel_ok, ziel_n = Counter(), Counter()
    log = Counter()
    for r in res:
        for z, v in r["ziele"].items():
            if v is None: continue
            ziel_n[z] += 1; ziel_ok[z] += bool(v)
        log.update(r["log"])
    züge = A["runden"] * len(GRUPPEN) * A["personen_pro_gruppe"]
    return dict(
        gewonnen=statistics.mean(r["gewonnen"] for r in res),
        wuensche=statistics.mean(r["wuensche"] for r in res),
        k_gebunden=1 - statistics.mean(r["k_frei_ende"] / max(1, r["k_start"]) for r in res),
        m_ende_pro_person=statistics.mean(r["m_ende"] for r in res) / (len(GRUPPEN) * A["personen_pro_gruppe"]),
        karten=statistics.mean(r["karten"] for r in res),
        felder=res[0]["felder"],
        kuemmer_angebot=res[0]["k_start"],
        ziele={z: ziel_ok[z] / ziel_n[z] for z in ZIELE if ziel_n[z]},
        passen_quote=log["passen"] / (n * züge),
        passen_grund={k[7:]: v / n for k, v in log.items() if k.startswith("passen_")},
        karten_häufigkeit={k[6:]: v / n for k, v in log.most_common() if k.startswith("karte_")},
        gekauft=log["kuemmer_gekauft"] / n, geliehen=log["geliehen"] / n, kombibonus=log["kombibonus"] / n,
        umgedreht=log["umgedreht"] / n,
    )

if __name__ == "__main__":
    szenarien = {
        "Basis (8 Pers., 4x4, Kurs 3)": {},
        "Kein Kauf von Kümmerzeit": dict(kuemmer_kurs=999),
        "Kurs 2": dict(kuemmer_kurs=2),
        "Mehr Fläche (5x4)": dict(raster=(5, 4)),
        "Ohne Ereignisse": dict(ereignisse=False),
        "Plan B (4 Pers.)": dict(personen_pro_gruppe=1),
        "Plan B, 3x4": dict(personen_pro_gruppe=1, raster=(3, 4)),
    }
    out = {}
    for name, delta in szenarien.items():
        A = dict(ANNAHMEN, **delta)
        out[name] = szenario(A)
    json.dump(out, open("lauf1_ergebnisse.json", "w"), ensure_ascii=False, indent=1, default=str)
    for name, r in out.items():
        print(f"\n=== {name}")
        for k in ["gewonnen", "wuensche", "k_gebunden", "m_ende_pro_person", "karten", "felder", "kuemmer_angebot",
                  "passen_quote", "gekauft", "geliehen", "kombibonus", "umgedreht"]:
            v = r[k]; print(f"  {k:20s} {v:.2f}" if isinstance(v, float) else f"  {k:20s} {v}")
        print("  passen_grund ", {k: round(v, 2) for k, v in r["passen_grund"].items()})
        print("  ziele        ", {k: round(v, 2) for k, v in r["ziele"].items()})
    base = out["Basis (8 Pers., 4x4, Kurs 3)"]
    print("\nKartenhäufigkeit Basis:", {k: round(v, 2) for k, v in base["karten_häufigkeit"].items()})
