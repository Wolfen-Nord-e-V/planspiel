"""
Regel-Simulation „Wer baut Wolfen-Nord?“ – Lauf 2 (14.10.2026)

Neu gegenüber Lauf 1:
- Statt abstraktem Raster: die freigegebenen Flächen und Gebäude aus der Spielanleitung,
  jede mit einer Kapazität in Flächenpunkten.
- Jede Baukarte hat einen Platzbedarf in Flächenpunkten.
- Kapazitäten grob aus der Flächenbilanz der Begründung zum Bebauungsplan 08-2020
  abgeleitet (ca. 250 m² überbaubare Fläche je Punkt), Grünland und Gebäude geschätzt.
- Nachbarschaft = gleiche Fläche (die echte Lage der Flächen zueinander ist nicht modelliert).

Verhandlungen, Veto und Teilen in der Konfliktrunde sind NICHT modelliert.
Alle Platzhalterwerte stehen in FLAECHEN, PLATZ und ANNAHMEN.
"""
import random, statistics, json
from collections import Counter, defaultdict

ANNAHMEN = dict(
    personen_pro_gruppe=2,   # 8 Personen
    runden=3,
    mittel_nachschub=1,      # pro Person und Runde (Lauf 1: 2)
    kuemmer_kurs=3,          # Mittel je gekaufter Kümmerzeit
    ereignisse=True,
    karten_pro_typ=2,
    kapazitaet_faktor=1.0,   # 1.0 = aus Bebauungsplan abgeleitet
)

# Fläche: (Typ, Kapazität in Flächenpunkten, Herleitung)
FLAECHEN = {
    "TG 1.1 Wiese an der Schule": ("Bau", 6, "1.635 m² überbaubar / 250"),
    "TG 2": ("Bau", 5, "1.316 m² überbaubar / 250"),
    "TG 3 Fläche am 84er": ("Bau", 6, "3.270 m² überbaubar, ca. die Hälfte frei"),
    "TG 4 Garagenhof (frei)": ("Bau", 3, "2.790 m² überbaubar, größtenteils Garagen"),
    "M1 Wiese am Spielplatz": ("Gruen", 4, "geschätzt"),
    "Grünfläche p": ("Gruen", 4, "geschätzt"),
    "Gemeinschaftsgarten": ("Gruen", 2, "geschätzt, Bestand"),
    "Kulturzentrum 84": ("Gebaeude", 2, "geschätzt"),
    "Garagen": ("Gebaeude", 3, "geschätzt"),
    "Christophorushaus links": ("Gebaeude", 2, "geschätzt"),
    "Turnhalle": ("Gebaeude", 3, "geschätzt"),
    "Grünstraße 36": ("Gebaeude", 3, "geschätzt"),
}
BESTAND = {  # bestehende Orte, zählen für Kombibonus und Ziele, belegen keinen Platz
    "Kulturzentrum 84": {"Begegnung", "Jung"},
    "Gemeinschaftsgarten": {"Gruen", "Essen"},
}
UM_84 = {"Kulturzentrum 84", "TG 3 Fläche am 84er"}

FREI = {"Bau", "Gruen"}; INNEN = {"Bau", "Gebaeude"}; ALLE = {"Bau", "Gruen", "Gebaeude"}
KARTEN = {  # Mittel, Kümmer, Tags, Flächentypen, Platzbedarf
    "Kartoffelacker": (1, 1, {"Gruen", "Essen"}, FREI, 2),
    "SoLaWi-Parzelle": (2, 2, {"Gruen", "Essen"}, FREI, 3),
    "Bluehwiese": (1, 0, {"Gruen", "Kinder"}, FREI, 2),
    "Streuobstwiese": (1, 1, {"Gruen", "Alt"}, FREI, 2),
    "Imkerei": (1, 1, {"Gruen", "Handwerk"}, FREI, 1),
    "Regenrueckhalt": (2, 0, {"Gruen"}, FREI, 2),
    "Spielplatz": (2, 0, {"Kinder"}, FREI, 2),
    "Bolzplatz": (1, 0, {"Jung"}, FREI, 3),
    "Werkstatt": (2, 2, {"Handwerk", "Jung", "Alt"}, INNEN, 2),
    "Kleingewerbe-Hof": (2, 1, {"Handwerk"}, INNEN, 2),
    "Jugendtreff": (1, 2, {"Jung", "Begegnung"}, INNEN, 2),
    "MehrGen-Cafe": (2, 2, {"Alt", "Kinder", "Begegnung"}, INNEN, 2),
    "Gemeinschaftskueche": (2, 2, {"Essen", "Begegnung"}, INNEN, 2),
    "Tauschschrank": (0, 1, {"Begegnung"}, ALLE, 1),
    "Freiluftbuehne": (2, 1, {"Begegnung", "Jung"}, FREI, 2),
    "Rufbus": (3, 1, {"Weg"}, ALLE, 1),
    "Wege+Baenke": (2, 0, {"Weg", "Alt"}, ALLE, 1),
    "Umbau Leerstand": (3, 1, {"Wohnen"}, {"Gebaeude"}, 2),
    "Gemeinschaftswohnen": (3, 2, {"Wohnen", "Alt", "Jung"}, {"Bau"}, 3),
}
EINNAHMEN = {"Kleingewerbe-Hof", "SoLaWi-Parzelle", "MehrGen-Cafe"}
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

# ---------------------------------------------------------------- Ziele
ZIELE = {
    "Drei Generationen": lambda s: any({"Kinder", "Jung", "Alt"} <= tags_auf(s, f) for f in FLAECHEN),
    # Plangebiet ca. 4,8 ha – jeder Ort liegt in 5 Gehminuten; der 84er ist schon Treffpunkt
    "Treffpunkt 5 Min": lambda s: True,
    "Läuft nach Förderende": lambda s: any(c["gebunden"] > 0 for c in aktive(s)),
    "Kein Chip übrig": lambda s: sum(sp["k"] for sp in s["spieler"]) == 0,
    "Einnahmen": lambda s: any(c["name"] in EINNAHMEN for c in aktive(s)),
    "84er verbunden": lambda s: sum(1 for c in aktive(s) if c["f"] in UM_84) >= 2,
    "Hälfte grün/offen": lambda s: sum(c["platz"] for c in aktive(s) if "Gruen" not in c["tags"]) <= sum(s["kap"].values()) / 2,
    "Jede Gruppe gelegt": lambda s: set(GRUPPEN) <= {c["gruppe"] for c in s["karten"]},
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
    kap = {f: max(1, round(v[1] * A["kapazitaet_faktor"])) for f, v in FLAECHEN.items()}
    s = dict(A=A, kap=kap, karten=[], log=Counter(), bonus_used=set())
    s["spieler"] = [dict(gruppe=g, m=m, k=k, wunsch=rng.choice(list(WUENSCHE)), extra=(g == "Ankommende"))
                    for g, (m, k) in GRUPPEN.items() for _ in range(A["personen_pro_gruppe"])]
    s["deck"] = Counter({k: A["karten_pro_typ"] for k in KARTEN})
    s["ziele"] = rng.sample(list(ZIELE), 3)
    return s

def bonus_partner(s, f, tags):
    if f not in s["bonus_used"] and tags & tags_auf(s, f):
        return f
    return None

def finanzierung(s, sp, m, k):
    fehl = max(0, k - sp["k"])
    pool = sum(o["k"] for o in s["spieler"] if o is not sp and o["gruppe"] == "Kuemmernde")
    leih = min(fehl, pool); kauf = fehl - leih
    return sp["m"] >= m + kauf * s["A"]["kuemmer_kurs"], leih, kauf

def zug(s, sp, rng):
    offen = [z for z in s["ziele"] if not ZIELE[z](s)]
    opts, grund = [], Counter()
    for name, n in s["deck"].items():
        if n <= 0: continue
        m, k, tags, typen, platz = KARTEN[name]
        flaechen = [f for f, v in FLAECHEN.items() if v[0] in typen and frei(s, f) >= platz]
        if not flaechen: grund["platz"] += 1; continue
        for f in flaechen:
            kk = k; partner = bonus_partner(s, f, tags) if k > 0 else None
            if partner: kk -= 1
            ok, _, _ = finanzierung(s, sp, m, kk)
            if not ok: grund["mittel"] += 1; continue
            w = rng.random()
            if name in WUNSCH_KARTEN.get(sp["wunsch"], []): w += 3
            if sp["wunsch"] == "Kein Gewerbehof" and name == "Kleingewerbe-Hof": w -= 10
            if "Einnahmen" in offen and name in EINNAHMEN: w += 2
            if "84er verbunden" in offen and f in UM_84: w += 2
            if "Drei Generationen" in offen and tags & {"Kinder", "Jung", "Alt"}: w += 1
            if "Hälfte grün/offen" in s["ziele"] and "Gruen" in tags: w += 1
            if "Kein Chip übrig" in s["ziele"] and kk > 0: w += 1.5
            if partner: w += 0.5
            opts.append((w, name, f, m, kk, partner))
    if not opts:
        s["log"]["passen"] += 1
        s["log"]["passen_" + (grund.most_common(1)[0][0] if grund else "deck")] += 1
        return False
    _, name, f, m, kk, partner = max(opts)
    ok, leih, kauf = finanzierung(s, sp, m, kk)
    sp["k"] -= kk - leih - kauf
    for o in s["spieler"]:
        if leih and o is not sp and o["gruppe"] == "Kuemmernde":
            x = min(o["k"], leih); o["k"] -= x; leih -= x; s["log"]["geliehen"] += x
    sp["m"] -= m + kauf * s["A"]["kuemmer_kurs"]
    s["log"]["gekauft"] += kauf
    if partner: s["bonus_used"].add(partner); s["log"]["kombibonus"] += 1
    s["deck"][name] -= 1
    s["karten"].append(dict(name=name, f=f, tags=set(KARTEN[name][2]), platz=KARTEN[name][4],
                            gebunden=kk, aktiv=True, gruppe=sp["gruppe"], owner=sp))
    s["log"]["karte_" + name] += 1
    return True

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
        for c in ks:
            if "Wohnen" in c["tags"] and "Begegnung" in tags_auf(s, c["f"]): c["owner"]["k"] += 1
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
                else: c["aktiv"] = False; s["log"]["umgedreht"] += 1

def partie(A, rng):
    s = neues_spiel(A, rng)
    k0 = sum(sp["k"] for sp in s["spieler"])
    leer_runde = Counter()
    for r in range(A["runden"]):
        for sp in s["spieler"]: sp["m"] += A["mittel_nachschub"]
        order = s["spieler"][:]; rng.shuffle(order)
        gelegt = 0
        for sp in order:
            gelegt += zug(s, sp, rng)
            if sp["extra"] and r == 1 and zug(s, sp, rng): sp["extra"] = False; gelegt += 1
        leer_runde[r] = gelegt
        if A["ereignisse"]: ereignis(s, rng)
    belegt = {f: (s["kap"][f] - frei(s, f)) / s["kap"][f] for f in FLAECHEN}
    return dict(
        ziele={z: ZIELE[z](s) for z in s["ziele"]},
        wuensche=statistics.mean(WUENSCHE[sp["wunsch"]](s) for sp in s["spieler"]),
        k_gebunden=1 - sum(sp["k"] for sp in s["spieler"]) / k0,
        m_ende=statistics.mean(sp["m"] for sp in s["spieler"]),
        karten=len(s["karten"]), gelegt_runde=leer_runde, belegt=belegt,
        kap=sum(s["kap"].values()), log=s["log"])

def szenario(A, n=1500, seed=2):
    rng = random.Random(seed)
    res = [partie(A, rng) for _ in range(n)]
    ok, cnt, log, belegt, runde = Counter(), Counter(), Counter(), defaultdict(list), defaultdict(list)
    for r in res:
        for z, v in r["ziele"].items(): cnt[z] += 1; ok[z] += v
        log.update(r["log"])
        for f, v in r["belegt"].items(): belegt[f].append(v)
        for k, v in r["gelegt_runde"].items(): runde[k].append(v)
    pers = len(GRUPPEN) * A["personen_pro_gruppe"]
    return dict(
        gewonnen=statistics.mean(all(r["ziele"].values()) for r in res),
        wuensche=statistics.mean(r["wuensche"] for r in res),
        kuemmer_gebunden=statistics.mean(r["k_gebunden"] for r in res),
        mittel_rest_pro_person=statistics.mean(r["m_ende"] for r in res),
        karten=statistics.mean(r["karten"] for r in res),
        kapazitaet=res[0]["kap"],
        karten_pro_runde=[round(statistics.mean(runde[k]) / pers, 2) for k in sorted(runde)],
        passen_grund={k[7:]: round(v / n, 2) for k, v in log.items() if k.startswith("passen_")},
        gekauft=log["gekauft"] / n, geliehen=log["geliehen"] / n, kombibonus=log["kombibonus"] / n,
        umgedreht=log["umgedreht"] / n,
        ziele={z: round(ok[z] / cnt[z], 2) for z in ZIELE if cnt[z]},
        belegung={f: round(statistics.mean(v), 2) for f, v in belegt.items()},
        kartenhaeufigkeit={k[6:]: round(v / n, 2) for k, v in log.most_common() if k.startswith("karte_")},
    )

if __name__ == "__main__":
    S = {
        "A: Bebauungsplan-Kapazität, Nachschub 1": {},
        "B: Bebauungsplan-Kapazität, Nachschub 2": dict(mittel_nachschub=2),
        "C: Kapazität x0,75, Nachschub 1": dict(kapazitaet_faktor=0.75),
        "D: Plan B (4 Pers.), Kapazität x0,6": dict(personen_pro_gruppe=1, kapazitaet_faktor=0.6),
        "E: Plan B (4 Pers.), volle Kapazität": dict(personen_pro_gruppe=1),
    }
    out = {name: szenario(dict(ANNAHMEN, **d)) for name, d in S.items()}
    json.dump(out, open("lauf2_ergebnisse.json", "w"), ensure_ascii=False, indent=1)
    for name, r in out.items():
        print(f"\n=== {name}")
        for k, v in r.items():
            if k in ("kartenhaeufigkeit",): continue
            print(f"  {k:24s} {round(v, 2) if isinstance(v, float) else v}")
    print("\nKartenhäufigkeit A:", out["A: Bebauungsplan-Kapazität, Nachschub 1"]["kartenhaeufigkeit"])
