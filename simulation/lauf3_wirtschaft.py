"""
Regel-Simulation „Wer baut Wolfen-Nord?“ – Lauf 3: Wirtschaften und Wohnen (17.10.2026)

Baut auf Lauf 2 auf (Flächen mit Kapazität, Karten mit Platzbedarf) und ergänzt:
- Erträge: wirtschaftende Orte bringen ab der zweiten Runde Mittel ein, aber nur mit
  gebundener Kümmerzeit.
- Ausbau: Ein eigener Ertragsort kann statt einer neuen Karte ausgebaut werden
  (+1 Mittel, +1 Kümmerzeit, +1 Flächenpunkt auf derselben Fläche) und bringt dann +1 Ertrag.
- Fördermittel: Der feste Nachschub kann über die Runden sinken (z. B. 2, 1, 0).
- Wohnen: Wohnkarten haben Wohneinheiten und laufende Kosten. Jede Runde ziehen
  Haushalte mit Bedingungen zu. Belegte Einheiten zahlen Miete. Wer die Kosten nicht
  zahlen kann, gerät in Schieflage; beim zweiten Mal wird die Karte umgedreht.
- Je zwei zugezogene Haushalte bringen 1 neue Kümmerzeit.

Nicht modelliert: Verhandlungen, Veto, Teilen, Konfliktrunde, Lage der Flächen
zueinander („in der Nähe“ = auf derselben Fläche).
Alle Platzhalterwerte stehen in ANNAHMEN, FLAECHEN, KARTEN, WOHNEN und HAUSHALTE.
"""
import random, statistics, json
from collections import Counter, defaultdict

ANNAHMEN = dict(
    personen_pro_gruppe=2,          # 8 Personen
    runden=3,
    foerderung=(2, 1, 0),           # Mittel-Nachschub pro Person je Runde
    kuemmer_kurs=3,
    ereignisse=True,
    karten_pro_typ=2,
    ertrag=True,
    ausbau=True,
    haushalte_pro_runde=3,          # Zuzugsinteressierte je Runde
    miete=1,                        # Mittel je belegter Einheit und Runde
    wohnkosten_faktor=1.0,          # skaliert die laufenden Kosten in WOHNEN
    kuemmer_je_haushalte=2,         # je so viele Haushalte 1 neue Kümmerzeit (0 = aus)
    ertrag_max=None,                # Obergrenze für den Grundertrag je Karte (None = wie auf der Karte)
    zuzug_chips_zaehlen=True,       # False: Kümmerzeit aus Zuzug zählt nicht gegen „Kein Chip übrig“
)

FLAECHEN = {  # Typ, Kapazität in Flächenpunkten
    "TG 1.1 Wiese an der Schule": ("Bau", 6),
    "TG 2": ("Bau", 5),
    "TG 3 Fläche am 84er": ("Bau", 6),
    "TG 4 Garagenhof (frei)": ("Bau", 3),
    "M1 Wiese am Spielplatz": ("Gruen", 4),
    "Grünfläche p": ("Gruen", 4),
    "Gemeinschaftsgarten": ("Gruen", 2),
    "Kulturzentrum 84": ("Gebaeude", 2),
    "Garagen": ("Gebaeude", 5),
    "Christophorushaus links": ("Gebaeude", 2),
    "Turnhalle": ("Gebaeude", 3),
    "Grünstraße 36": ("Gebaeude", 3),
}
BESTAND = {"Kulturzentrum 84": {"Begegnung", "Jung"}, "Gemeinschaftsgarten": {"Gruen", "Essen"}}
UM_84 = {"Kulturzentrum 84", "TG 3 Fläche am 84er"}

FREI = {"Bau", "Gruen"}; INNEN = {"Bau", "Gebaeude"}; ALLE = {"Bau", "Gruen", "Gebaeude"}
# Mittel, Kümmer, Tags, Flächentypen, Platz, Ertrag je Runde
KARTEN = {
    "Kartoffelacker": (1, 1, {"Gruen", "Essen"}, FREI, 2, 1),
    "SoLaWi-Parzelle": (2, 2, {"Gruen", "Essen"}, FREI, 3, 2),
    "Bluehwiese": (1, 0, {"Gruen", "Kinder"}, FREI, 2, 0),
    "Streuobstwiese": (1, 1, {"Gruen", "Alt"}, FREI, 2, 0),
    "Imkerei": (1, 1, {"Gruen", "Handwerk"}, FREI, 1, 1),
    "Regenrueckhalt": (2, 0, {"Gruen"}, FREI, 2, 0),
    "Spielplatz": (2, 0, {"Kinder"}, FREI, 2, 0),
    "Bolzplatz": (1, 0, {"Jung"}, FREI, 3, 0),
    "Werkstatt": (2, 2, {"Handwerk", "Jung", "Alt"}, INNEN, 2, 0),
    "Kleingewerbe-Hof": (2, 1, {"Handwerk"}, INNEN, 2, 2),
    "Jugendtreff": (1, 2, {"Jung", "Begegnung"}, INNEN, 2, 0),
    "MehrGen-Cafe": (2, 2, {"Alt", "Kinder", "Begegnung"}, INNEN, 2, 1),
    "Gemeinschaftskueche": (2, 2, {"Essen", "Begegnung"}, INNEN, 2, 0),
    "Tauschschrank": (0, 1, {"Begegnung"}, ALLE, 1, 0),
    "Freiluftbuehne": (2, 1, {"Begegnung", "Jung"}, FREI, 2, 0),
    "Rufbus": (3, 1, {"Weg"}, ALLE, 1, 0),
    "Wege+Baenke": (2, 0, {"Weg", "Alt"}, ALLE, 1, 0),
    "Umbau Leerstand": (3, 1, {"Wohnen"}, {"Gebaeude"}, 2, 0),
    "Gemeinschaftswohnen": (3, 2, {"Wohnen", "Alt", "Jung"}, {"Bau"}, 3, 0),
}
WOHNEN = {  # Wohneinheiten, laufende Kosten je Runde
    "Umbau Leerstand": (8, 3),
    "Gemeinschaftswohnen": (6, 3),
}
HAUSHALTE = {  # Haushalt: (benötigter Tag in der Nähe, Anzahl im Stapel)
    "Familie mit Kindern": ("Kinder", 4),
    "Rentnerpaar": ("Alt", 4),
    "Homeoffice-Paar": ("Begegnung", 4),
    "Handwerkerin": ("Handwerk", 2),
    "Jugendliche WG": ("Jung", 2),
    "Wegepaar ohne Auto": ("Weg", 2),
}
EINNAHMEN = {k for k, v in KARTEN.items() if v[5] > 0}
GRUPPEN = {"Bleibende": (2, 2), "Ankommende": (2, 1), "Rahmengebende": (5, 1), "Kuemmernde": (1, 4)}

# ---------------------------------------------------------------- Hilfen
def aktive(s, f=None):
    return [c for c in s["karten"] if c["aktiv"] and (f is None or c["f"] == f)]

def tags_auf(s, f):
    t = set(BESTAND.get(f, set()))
    for c in aktive(s, f): t |= c["tags"]
    return t

def frei(s, f):
    return s["kap"][f] - sum(c["platz"] for c in s["karten"] if c["f"] == f)

def aktiv(s, name): return any(c["name"] == name for c in aktive(s))
def aktiv_tag(s, tag): return any(tag in c["tags"] for c in aktive(s))
def wohnkarten(s): return [c for c in aktive(s) if c["name"] in WOHNEN]

def traegt_sich(s, c):
    return c["belegt"] * s["A"]["miete"] >= c["kosten"]

# ---------------------------------------------------------------- Ziele
ZIELE = {
    "Drei Generationen": lambda s: any({"Kinder", "Jung", "Alt"} <= tags_auf(s, f) for f in FLAECHEN),
    "Treffpunkt 5 Min": lambda s: True,
    "Läuft nach Förderende": lambda s: any(c["gebunden"] > 0 for c in aktive(s)),
    "Kein Chip übrig": lambda s: sum(sp["k"] for sp in s["spieler"]) <= (0 if s["A"]["zuzug_chips_zaehlen"] else s["log"]["kuemmer_durch_zuzug"]),
    "Einnahmen": lambda s: any(c["name"] in EINNAHMEN for c in aktive(s)),
    "84er verbunden": lambda s: sum(1 for c in aktive(s) if c["f"] in UM_84) >= 2,
    "Hälfte grün/offen": lambda s: sum(c["platz"] for c in aktive(s) if "Gruen" not in c["tags"]) <= sum(s["kap"].values()) / 2,
    "Jede Gruppe gelegt": lambda s: set(GRUPPEN) <= {c["gruppe"] for c in s["karten"]},
}
# Kandidaten für neue Ziele – werden nur ausgewertet, nicht gezogen
ZIEL_KANDIDATEN = {
    "Wohnprojekt trägt sich": lambda s: any(traegt_sich(s, c) for c in wohnkarten(s)),
    "Kein Haushalt verloren": lambda s: s["log"]["haushalt_verloren"] == 0,
    "Zehn neue Haushalte": lambda s: sum(c["belegt"] for c in wohnkarten(s)) >= 10,
}

WUENSCHE = {
    "Weg zum Kaufmarkt": lambda s: aktiv_tag(s, "Weg"),
    "Kein Gewerbehof": lambda s: not aktiv(s, "Kleingewerbe-Hof"),
    "Trampelpfad bleibt": lambda s: any(frei(s, f) >= 2 for f, v in FLAECHEN.items() if v[0] == "Gruen"),
    "Abends was los": lambda s: any(aktiv(s, n) for n in ["Jugendtreff", "MehrGen-Cafe", "Freiluftbuehne", "Gemeinschaftskueche"]),
    "Ort für Kinder": lambda s: aktiv(s, "Spielplatz") or aktiv(s, "Bluehwiese"),
    "Tiny House / Jurte": lambda s: aktiv(s, "Gemeinschaftswohnen"),
    "Kein Leerstand": lambda s: aktiv(s, "Umbau Leerstand"),
    "Keine Dauerlast": lambda s: all(c["aktiv"] for c in s["karten"]),
    "Verein sichtbar": lambda s: sum(1 for c in aktive(s) if c["f"] in UM_84 and "Begegnung" in c["tags"]) >= 1,
}
WUNSCH_KARTEN = {
    "Weg zum Kaufmarkt": ["Wege+Baenke", "Rufbus"], "Abends was los": ["Freiluftbuehne", "Jugendtreff", "MehrGen-Cafe"],
    "Ort für Kinder": ["Spielplatz", "Bluehwiese"], "Tiny House / Jurte": ["Gemeinschaftswohnen"],
    "Kein Leerstand": ["Umbau Leerstand"], "Verein sichtbar": ["Freiluftbuehne", "Tauschschrank", "Jugendtreff"],
}

# ---------------------------------------------------------------- Spiel
def neues_spiel(A, rng):
    s = dict(A=A, kap={f: v[1] for f, v in FLAECHEN.items()}, karten=[], log=Counter(), bonus_used=set(),
             zufluss=Counter())
    s["spieler"] = [dict(gruppe=g, m=m, k=k, wunsch=rng.choice(list(WUENSCHE)), extra=(g == "Ankommende"), hh=0)
                    for g, (m, k) in GRUPPEN.items() for _ in range(A["personen_pro_gruppe"])]
    s["deck"] = Counter({k: A["karten_pro_typ"] for k in KARTEN})
    stapel = [h for h, (_, n) in HAUSHALTE.items() for _ in range(n)]
    rng.shuffle(stapel)
    s["haushalte"] = stapel
    s["ziele"] = rng.sample(list(ZIELE), 3)
    return s

def finanzierung(s, sp, m, k):
    fehl = max(0, k - sp["k"])
    pool = sum(o["k"] for o in s["spieler"] if o is not sp and o["gruppe"] == "Kuemmernde")
    leih = min(fehl, pool); kauf = fehl - leih
    return sp["m"] >= m + kauf * s["A"]["kuemmer_kurs"], leih, kauf

def bezahlen(s, sp, m, kk):
    ok, leih, kauf = finanzierung(s, sp, m, kk)
    sp["k"] -= kk - leih - kauf
    for o in s["spieler"]:
        if leih and o is not sp and o["gruppe"] == "Kuemmernde":
            x = min(o["k"], leih); o["k"] -= x; leih -= x; s["log"]["geliehen"] += x
    sp["m"] -= m + kauf * s["A"]["kuemmer_kurs"]
    s["log"]["gekauft"] += kauf

def zug(s, sp, rng, runde):
    A = s["A"]; rest = A["runden"] - runde
    offen = [z for z in s["ziele"] if not ZIELE[z](s)]
    opts = []
    for name, n in s["deck"].items():
        if n <= 0: continue
        m, k, tags, typen, platz, ertrag = KARTEN[name]
        for f, v in FLAECHEN.items():
            if v[0] not in typen or frei(s, f) < platz: continue
            kk = k; partner = f if (k > 0 and f not in s["bonus_used"] and tags & tags_auf(s, f)) else None
            if partner: kk -= 1
            if not finanzierung(s, sp, m, kk)[0]: continue
            w = rng.random()
            if name in WUNSCH_KARTEN.get(sp["wunsch"], []): w += 3
            if sp["wunsch"] == "Kein Gewerbehof" and name == "Kleingewerbe-Hof": w -= 10
            if "Einnahmen" in offen and name in EINNAHMEN: w += 2
            if "84er verbunden" in offen and f in UM_84: w += 2
            if "Drei Generationen" in offen and tags & {"Kinder", "Jung", "Alt"}: w += 1
            if "Hälfte grün/offen" in s["ziele"] and "Gruen" in tags: w += 1
            if "Kein Chip übrig" in s["ziele"] and kk > 0: w += 1.5
            if partner: w += 0.5
            if A["ertrag"] and ertrag: w += 0.6 * ertrag * rest
            if name in WOHNEN:
                umfeld = tags_auf(s, f) & {"Kinder", "Alt", "Begegnung", "Handwerk", "Jung", "Weg"}
                w += 0.5 * len(umfeld) + (0.5 * rest)
            # Orte, die Haushalte anziehen, neben Wohnungen mit freien Einheiten
            if any(c["name"] in WOHNEN and c["belegt"] < c["einheiten"] for c in aktive(s, f)):
                w += 0.7 * len(tags & {"Kinder", "Alt", "Begegnung", "Handwerk", "Jung", "Weg"})
            opts.append((w, "bau", name, f, m, kk, partner))
    # Ausbau eigener Ertragsorte
    if A["ausbau"] and A["ertrag"]:
        for c in aktive(s):
            if c["owner"] is sp and c["name"] in EINNAHMEN and c["stufe"] < 2 and frei(s, c["f"]) >= 1:
                if finanzierung(s, sp, 1, 1)[0]:
                    w = rng.random() + 0.6 * rest + 0.5
                    opts.append((w, "ausbau", c, c["f"], 1, 1, None))
    if not opts:
        s["log"]["passen"] += 1
        return False
    w, art, name, f, m, kk, partner = max(opts, key=lambda o: o[0])
    bezahlen(s, sp, m, kk)
    if art == "ausbau":
        name["stufe"] += 1; name["platz"] += 1; name["gebunden"] += 1
        s["log"]["ausbau"] += 1
        return True
    if partner: s["bonus_used"].add(partner); s["log"]["kombibonus"] += 1
    s["deck"][name] -= 1
    c = dict(name=name, f=f, tags=set(KARTEN[name][2]), platz=KARTEN[name][4], gebunden=kk, aktiv=True,
             gruppe=sp["gruppe"], owner=sp, stufe=1, ertrag=KARTEN[name][5], belegt=0, schieflage=0)
    if name in WOHNEN:
        c["einheiten"], kosten = WOHNEN[name]
        c["kosten"] = round(kosten * A["wohnkosten_faktor"])
        s["log"]["wohnprojekt"] += 1
    s["karten"].append(c)
    s["log"]["karte_" + name] += 1
    return True

def zuzug(s, rng):
    A = s["A"]
    for _ in range(A["haushalte_pro_runde"]):
        if not s["haushalte"]: break
        h = s["haushalte"].pop()
        tag = HAUSHALTE[h][0]
        ziele = [c for c in wohnkarten(s) if c["belegt"] < c["einheiten"] and tag in tags_auf(s, c["f"])]
        if not ziele:
            s["log"]["haushalt_verloren"] += 1
            s["log"]["verloren_" + h] += 1
            continue
        c = rng.choice(ziele)
        c["belegt"] += 1
        s["log"]["haushalt_eingezogen"] += 1
        o = c["owner"]; o["hh"] += 1
        n = A["kuemmer_je_haushalte"]
        if n and o["hh"] % n == 0:
            o["k"] += 1; s["log"]["kuemmer_durch_zuzug"] += 1

def wirtschaften(s):
    """Erträge und Wohnkosten zu Beginn einer Runde (ab Runde 2)."""
    A = s["A"]
    for c in aktive(s):
        if A["ertrag"] and c["ertrag"] and c["gebunden"] > 0:
            basis = c["ertrag"] if A["ertrag_max"] is None else min(c["ertrag"], A["ertrag_max"])
            x = basis + (c["stufe"] - 1)
            c["owner"]["m"] += x; s["zufluss"]["ertrag"] += x
        if c["name"] in WOHNEN:
            miete = c["belegt"] * A["miete"]
            c["owner"]["m"] += miete; s["zufluss"]["miete"] += miete
            if c["owner"]["m"] >= c["kosten"]:
                c["owner"]["m"] -= c["kosten"]; s["zufluss"]["wohnkosten"] -= c["kosten"]
            else:
                c["schieflage"] += 1; s["log"]["schieflage"] += 1
                c["owner"]["m"] = 0
                if c["schieflage"] >= 2:
                    c["aktiv"] = False; s["log"]["wohn_umgedreht"] += 1; s["log"]["umgedreht"] += 1

def ereignis(s, rng):
    e = rng.choice(["Förderprogramm endet", "Kümmerin zieht weg", "Dürresommer", "Starkregen", "Zwanzig neue Nachbarn",
                    "Spende", "Fläche nur für ein Jahr", "Sommerfest", "Kita braucht Fläche", "Sanierung"])
    ks = aktive(s)
    if e == "Förderprogramm endet":
        for g in GRUPPEN:
            sp = next(x for x in s["spieler"] if x["gruppe"] == g); sp["m"] = max(0, sp["m"] - 1)
    elif e == "Kümmerin zieht weg":
        sp = rng.choice(s["spieler"])
        if sp["k"]: sp["k"] -= 1
    elif e == "Dürresommer":
        for c in ks:
            if "Gruen" in c["tags"]:
                if c["owner"]["k"]: c["owner"]["k"] -= 1; c["gebunden"] += 1
                else: c["aktiv"] = False; s["log"]["umgedreht"] += 1
    elif e == "Starkregen" and not aktiv(s, "Regenrueckhalt"):
        for c in ks:
            if "Weg" in c["tags"]: c["aktiv"] = False; s["log"]["umgedreht"] += 1
    elif e == "Zwanzig neue Nachbarn":
        # zwei zusätzliche Haushalte ziehen zu
        alt = s["A"]["haushalte_pro_runde"]; s["A"] = dict(s["A"], haushalte_pro_runde=2); zuzug(s, rng); s["A"] = dict(s["A"], haushalte_pro_runde=alt)
    elif e == "Spende":
        rng.choice(s["spieler"])["m"] += 3
    elif e == "Fläche nur für ein Jahr" and ks:
        c = rng.choice(ks)
        if c["owner"]["m"]: c["owner"]["m"] -= 1
        else: c["owner"]["k"] += c["gebunden"]; s["karten"].remove(c); s["log"]["geraeumt"] += 1
    elif e == "Sommerfest":
        for c in ks:
            if "Begegnung" in c["tags"]: c["owner"]["m"] += 1
    elif e == "Kita braucht Fläche" and ks:
        if not any(frei(s, f) >= 2 for f in FLAECHEN):
            c = rng.choice(ks); c["owner"]["k"] += c["gebunden"]; s["karten"].remove(c); s["log"]["geraeumt"] += 1
    elif e == "Sanierung":
        for c in ks:
            if "Wohnen" in c["tags"]:
                if c["owner"]["m"]: c["owner"]["m"] -= 1
                else:
                    c["belegt"] = max(0, c["belegt"] - 2); s["log"]["auszug_sanierung"] += 1

def partie(A, rng):
    s = neues_spiel(A, rng)
    k0 = sum(sp["k"] for sp in s["spieler"])
    for r in range(A["runden"]):
        if r > 0: wirtschaften(s)
        nach = A["foerderung"][min(r, len(A["foerderung"]) - 1)]
        for sp in s["spieler"]: sp["m"] += nach
        s["zufluss"]["foerderung"] += nach * len(s["spieler"])
        order = s["spieler"][:]; rng.shuffle(order)
        for sp in order:
            zug(s, sp, rng, r)
            if sp["extra"] and r == 1 and zug(s, sp, rng, r): sp["extra"] = False
        zuzug(s, rng)
        if A["ereignisse"]: ereignis(s, rng)
    wirtschaften(s)  # Schlussabrechnung: trägt sich das Quartier am Ende?
    wk = [c for c in s["karten"] if c["name"] in WOHNEN]
    return dict(
        ziele={z: ZIELE[z](s) for z in s["ziele"]},
        kandidaten={z: f(s) for z, f in ZIEL_KANDIDATEN.items()},
        wuensche=statistics.mean(WUENSCHE[sp["wunsch"]](s) for sp in s["spieler"]),
        k_gebunden=1 - sum(sp["k"] for sp in s["spieler"]) / k0,
        m_ende=statistics.mean(sp["m"] for sp in s["spieler"]),
        wohnprojekte=len(wk),
        wohn_aktiv=sum(c["aktiv"] for c in wk),
        belegung=[c["belegt"] / c["einheiten"] for c in wk if c["aktiv"]],
        traegt=[traegt_sich(s, c) for c in wk if c["aktiv"]],
        haushalte=sum(c["belegt"] for c in wk),
        zufluss=s["zufluss"], log=s["log"],
    )

def szenario(A, n=1500, seed=3):
    rng = random.Random(seed)
    res = [partie(dict(A), rng) for _ in range(n)]
    ok, cnt, log, zu, kand = Counter(), Counter(), Counter(), Counter(), Counter()
    for r in res:
        for z, v in r["ziele"].items(): cnt[z] += 1; ok[z] += v
        for z, v in r["kandidaten"].items(): kand[z] += v
        log.update(r["log"]); zu.update(r["zufluss"])
    bel = [b for r in res for b in r["belegung"]]
    tr = [t for r in res for t in r["traegt"]]
    hh = [r["haushalte"] for r in res]
    einnahmen = zu["foerderung"] + zu["ertrag"] + zu["miete"]
    return dict(
        gewonnen=statistics.mean(all(r["ziele"].values()) for r in res),
        wuensche=statistics.mean(r["wuensche"] for r in res),
        kuemmer_gebunden=statistics.mean(r["k_gebunden"] for r in res),
        mittel_rest_pro_person=statistics.mean(r["m_ende"] for r in res),
        wohnprojekte_pro_partie=statistics.mean(r["wohnprojekte"] for r in res),
        partien_ohne_wohnen=statistics.mean(r["wohnprojekte"] == 0 for r in res),
        belegung_wohnprojekte=statistics.mean(bel) if bel else 0,
        anteil_traegt_sich=statistics.mean(tr) if tr else 0,
        wohn_umgedreht_pro_partie=log["wohn_umgedreht"] / n,
        haushalte_mittel=statistics.mean(hh),
        haushalte_p90=sorted(hh)[int(0.9 * n)],
        haushalte_verloren=log["haushalt_verloren"] / n,
        kuemmer_durch_zuzug=log["kuemmer_durch_zuzug"] / n,
        anteil_eigene_einnahmen=(zu["ertrag"] + zu["miete"]) / einnahmen if einnahmen else 0,
        ertrag_pro_partie=zu["ertrag"] / n, miete_pro_partie=zu["miete"] / n,
        ausbau_pro_partie=log["ausbau"] / n,
        ziele={z: round(ok[z] / cnt[z], 2) for z in ZIELE if cnt[z]},
        ziel_kandidaten={z: round(v / n, 2) for z, v in kand.items()},
        verloren_nach_typ={k[9:]: round(v / n, 2) for k, v in log.items() if k.startswith("verloren_")},
        kartenhaeufigkeit={k[6:]: round(v / n, 2) for k, v in log.most_common() if k.startswith("karte_")},
    )

if __name__ == "__main__":
    S = {
        "A: Basis (Förderung 2-1-0, Kosten 3, 3 Haushalte/Runde)": {},
        "B: Förderung konstant 1": dict(foerderung=(1, 1, 1)),
        "C: ohne Erträge (wie Lauf 2 plus Wohnen)": dict(ertrag=False, foerderung=(1, 1, 1)),
        "D: Wohnkosten 2": dict(wohnkosten_faktor=2 / 3),
        "E: 2 Haushalte/Runde": dict(haushalte_pro_runde=2),
        "F: 5 Haushalte/Runde": dict(haushalte_pro_runde=5),
        "G: ohne Kümmerzeit durch Zuzug": dict(kuemmer_je_haushalte=0),
        "H: 1 Exemplar je Karte": dict(karten_pro_typ=1),
        "I: Plan B (4 Pers.)": dict(personen_pro_gruppe=1),
        "J: Empfehlung (8 Pers.)": dict(karten_pro_typ=1, wohnkosten_faktor=2 / 3, ertrag_max=1, zuzug_chips_zaehlen=False),
        "K: Empfehlung Plan B (4 Pers., 2 Haushalte)": dict(karten_pro_typ=1, wohnkosten_faktor=2 / 3, ertrag_max=1,
                                                          zuzug_chips_zaehlen=False, personen_pro_gruppe=1, haushalte_pro_runde=2),
    }
    out = {name: szenario(dict(ANNAHMEN, **d)) for name, d in S.items()}
    json.dump(out, open("lauf3_ergebnisse.json", "w"), ensure_ascii=False, indent=1)
    keys = ["gewonnen", "mittel_rest_pro_person", "wohnprojekte_pro_partie", "partien_ohne_wohnen",
            "belegung_wohnprojekte", "anteil_traegt_sich", "wohn_umgedreht_pro_partie", "haushalte_mittel",
            "haushalte_p90", "haushalte_verloren", "kuemmer_durch_zuzug", "anteil_eigene_einnahmen",
            "ertrag_pro_partie", "miete_pro_partie", "ausbau_pro_partie", "kuemmer_gebunden"]
    for name, r in out.items():
        print(f"\n=== {name}")
        print("  " + "  ".join(f"{k}={round(r[k], 2)}" for k in keys))
        print("  ziele", r["ziele"])
        print("  kandidaten", r["ziel_kandidaten"], " verloren", r["verloren_nach_typ"])
    print("\nKarten A:", out[next(iter(out))]["kartenhaeufigkeit"])
