"""
Regel-Simulation „Wer baut Wolfen-Nord?“ – Lauf 4: Wohngenossenschaft (17.10.2026)

Baut auf Lauf 3 (Wirtschaften und Wohnen) auf, mit den dort empfohlenen Einstellungen
(ein Exemplar je Karte, Wohnkosten 2, Ertrag 1, Zuzug-Chips zählen nicht für
„Kein Chip übrig“). Neu:

- Es gibt genau eine Wohngenossenschaft. Sie muss erst gegründet werden:
  Kümmerzeit aus mindestens zwei Gruppen (zusammen 3) plus 2 Mittel als Anteile.
- Wohnkarten dürfen erst nach der Gründung gelegt werden und gehören der Genossenschaft.
  Miete und Wohnkosten laufen über die Genossenschaftskasse.
- Kümmerzeit aus Zuzug landet bei der Genossenschaft; alle können sie für Bauvorhaben nutzen.
- Wer ein eigenes Tiny House will, wird Mitglied (1 Mittel, 1 Kümmerzeit), belegt eine
  Einheit eines Gemeinschaftswohnprojekts und zahlt selbst Miete.
- Neue Ereignisse: Bank verlangt Eigenkapital, Gründungsprüfung, Mitglied tritt aus.

Nicht modelliert: Verhandlungen, Veto, Teilen, Konfliktrunde, Lage der Flächen zueinander,
Abstimmungen in der Genossenschaft.
"""
import random, statistics, json
from collections import Counter
import lauf3_wirtschaft as L3
from lauf3_wirtschaft import (FLAECHEN, KARTEN, WOHNEN, HAUSHALTE, GRUPPEN, EINNAHMEN, UM_84, ZIELE, WUENSCHE,
                              WUNSCH_KARTEN, aktive, tags_auf, frei, aktiv, wohnkarten, traegt_sich)

ANNAHMEN = dict(L3.ANNAHMEN,
    karten_pro_typ=1,
    wohnkosten_faktor=2 / 3,        # Kosten 3 → 2
    ertrag_max=1,
    zuzug_chips_zaehlen=False,
    genossenschaft=True,
    gruendung_k=3,                  # Kümmerzeit für die Gründung
    gruendung_gruppen=2,            # aus mindestens so vielen Gruppen
    gruendung_m=2,                  # Mittel als erste Anteile (gehen in die Kasse)
    mitglied_m=1, mitglied_k=1,     # Beitritt mit eigenem Tiny House
    neue_ereignisse=True,
    bau_ab_folgerunde=False,
    gegruendet_start=False,        # True: Genossenschaft besteht zu Spielbeginn (Kasse 2, zwei Gruppen)       # True: Wohnkarten erst ab der Runde nach der Gründung
)
UMFELD = {"Kinder", "Alt", "Begegnung", "Handwerk", "Jung", "Weg"}

def neues_spiel(A, rng):
    s = L3.neues_spiel(A, rng)
    for sp in s["spieler"]: sp["mitglied"] = False
    s["geno"] = dict(gruppe="Genossenschaft", m=0, k=0, hh=0, gegruendet=False, runde=None, gruppen=set(),
                     sperre=False, eigenkapital=False)
    if A["gegruendet_start"]:
        s["geno"].update(gegruendet=True, runde=-1, gruppen={"Bleibende", "Kuemmernde"}, m=A["gruendung_m"])
    return s

# --------------------------------------------------- Finanzierung mit Genossenschafts-Pool
def finanzierung(s, sp, m, k, mit_pool=False):
    fehl = max(0, k - sp["k"])
    pool = sum(o["k"] for o in s["spieler"] if o is not sp and o["gruppe"] == "Kuemmernde")
    if mit_pool: pool += s["geno"]["k"]
    leih = min(fehl, pool); kauf = fehl - leih
    return sp["m"] >= m + kauf * s["A"]["kuemmer_kurs"], leih, kauf

def bezahlen(s, sp, m, kk, mit_pool=False):
    ok, leih, kauf = finanzierung(s, sp, m, kk, mit_pool)
    sp["k"] -= kk - leih - kauf
    if mit_pool and leih:
        x = min(s["geno"]["k"], leih); s["geno"]["k"] -= x; leih -= x; s["log"]["geno_k_genutzt"] += x
    for o in s["spieler"]:
        if leih and o is not sp and o["gruppe"] == "Kuemmernde":
            x = min(o["k"], leih); o["k"] -= x; leih -= x; s["log"]["geliehen"] += x
    sp["m"] -= m + kauf * s["A"]["kuemmer_kurs"]
    s["log"]["gekauft"] += kauf

# --------------------------------------------------- Gründung
def gruendung_moeglich(s, sp):
    A, g = s["A"], s["geno"]
    if not A["genossenschaft"] or g["gegruendet"] or sp["m"] < A["gruendung_m"]: return None
    eigen = min(sp["k"], A["gruendung_k"] - (A["gruendung_gruppen"] - 1))  # Platz für andere Gruppen lassen
    gruppen = {sp["gruppe"]} if eigen else set()
    andere = sorted((o for o in s["spieler"] if o["gruppe"] != sp["gruppe"] and o["k"] > 0), key=lambda o: -o["k"])
    beitrag, rest, gegeben = [], A["gruendung_k"] - eigen, Counter()
    # erst je 1 Kümmerzeit aus weiteren Gruppen, dann auffüllen
    for o in andere:
        if rest <= 0 or len(gruppen) >= A["gruendung_gruppen"]: break
        if o["gruppe"] in gruppen: continue
        beitrag.append([o, 1]); gegeben[id(o)] += 1; rest -= 1; gruppen.add(o["gruppe"])
    for o in andere:
        if rest <= 0: break
        x = min(o["k"] - gegeben[id(o)], rest)
        if x > 0: beitrag.append([o, x]); gegeben[id(o)] += x; rest -= x; gruppen.add(o["gruppe"])
    if rest > 0 or len(gruppen) < A["gruendung_gruppen"]: return None
    return eigen, beitrag, gruppen

def gruenden(s, sp, plan, runde):
    eigen, beitrag, gruppen = plan
    g = s["geno"]
    sp["k"] -= eigen; sp["m"] -= s["A"]["gruendung_m"]; g["m"] += s["A"]["gruendung_m"]
    for o, x in beitrag: o["k"] -= x
    g.update(gegruendet=True, runde=runde, gruppen=gruppen)
    s["log"]["gegruendet"] += 1

def wohnbau_erlaubt(s):
    g = s["geno"]
    if not g["gegruendet"] or g["sperre"]: return False
    if s["A"]["bau_ab_folgerunde"] and g["runde"] == s.get("runde"): return False
    if g["eigenkapital"] and g["m"] < 3: return False
    return True

# --------------------------------------------------- Zug
def zug(s, sp, rng, runde):
    A = s["A"]; rest = A["runden"] - runde
    offen = [z for z in s["ziele"] if not ZIELE[z](s)]
    opts = []
    wb = wohnbau_erlaubt(s)
    for name, n in s["deck"].items():
        if n <= 0: continue
        m, k, tags, typen, platz, ertrag = KARTEN[name]
        istwohn = name in WOHNEN
        if istwohn and A["genossenschaft"] and not wb: continue
        for f, v in FLAECHEN.items():
            if v[0] not in typen or frei(s, f) < platz: continue
            kk = k; partner = f if (k > 0 and f not in s["bonus_used"] and tags & tags_auf(s, f)) else None
            if partner: kk -= 1
            if not finanzierung(s, sp, m, kk, mit_pool=True)[0]: continue
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
            if istwohn:
                w += 0.5 * len(tags_auf(s, f) & UMFELD) + 0.5 * rest
            if any(c["name"] in WOHNEN and c["belegt"] < c["einheiten"] for c in aktive(s, f)):
                w += 0.7 * len(tags & UMFELD)
            opts.append((w, "bau", name, f, m, kk, partner))
    if A["ausbau"] and A["ertrag"]:
        for c in aktive(s):
            if c["owner"] is sp and c["name"] in EINNAHMEN and c["stufe"] < 2 and frei(s, c["f"]) >= 1:
                if finanzierung(s, sp, 1, 1)[0]:
                    opts.append((rng.random() + 0.6 * rest + 0.5, "ausbau", c, c["f"], 1, 1, None))
    plan = gruendung_moeglich(s, sp)
    if plan:
        w = rng.random() + 1.5 + 1.0 * rest + (3 if sp["wunsch"] in ("Tiny House / Jurte", "Kein Leerstand") else 0)
        opts.append((w, "gruendung", plan, None, 0, 0, None))
    if A["genossenschaft"] and sp["wunsch"] == "Tiny House / Jurte" and not sp["mitglied"]:
        frei_wohn = [c for c in wohnkarten(s) if c["name"] == "Gemeinschaftswohnen" and c["belegt"] < c["einheiten"]]
        if frei_wohn and finanzierung(s, sp, A["mitglied_m"], A["mitglied_k"])[0]:
            opts.append((rng.random() + 4, "beitritt", frei_wohn[0], None, A["mitglied_m"], A["mitglied_k"], None))
    if not opts:
        s["log"]["passen"] += 1
        return False
    w, art, name, f, m, kk, partner = max(opts, key=lambda o: o[0])
    if art == "gruendung":
        gruenden(s, sp, name, runde); return True
    if art == "beitritt":
        bezahlen(s, sp, m, kk); name["belegt"] += 1; name["mitglieder"].append(sp); sp["mitglied"] = True
        s["geno"]["m"] += m; s["log"]["beitritt"] += 1; return True
    bezahlen(s, sp, m, kk, mit_pool=True)
    if art == "ausbau":
        name["stufe"] += 1; name["platz"] += 1; name["gebunden"] += 1; s["log"]["ausbau"] += 1
        return True
    if partner: s["bonus_used"].add(partner); s["log"]["kombibonus"] += 1
    s["deck"][name] -= 1
    owner = s["geno"] if (name in WOHNEN and A["genossenschaft"]) else sp
    c = dict(name=name, f=f, tags=set(KARTEN[name][2]), platz=KARTEN[name][4], gebunden=kk, aktiv=True,
             gruppe=sp["gruppe"], owner=owner, stufe=1, ertrag=KARTEN[name][5], belegt=0, schieflage=0, mitglieder=[])
    if name in WOHNEN:
        c["einheiten"], kosten = WOHNEN[name]
        c["kosten"] = round(kosten * A["wohnkosten_faktor"])
        s["log"]["wohnprojekt"] += 1
    s["karten"].append(c)
    s["log"]["karte_" + name] += 1
    return True

# --------------------------------------------------- Wirtschaften
def wirtschaften(s):
    A = s["A"]
    for c in aktive(s):
        if A["ertrag"] and c["ertrag"] and c["gebunden"] > 0:
            x = min(c["ertrag"], A["ertrag_max"]) + (c["stufe"] - 1)
            c["owner"]["m"] += x; s["zufluss"]["ertrag"] += x
        if c["name"] in WOHNEN:
            fremd = c["belegt"] - len(c["mitglieder"])
            miete = fremd * A["miete"]
            for sp in c["mitglieder"]:          # Mitglieder zahlen ihre Miete selbst
                if sp["m"] >= A["miete"]: sp["m"] -= A["miete"]; miete += A["miete"]
                else: s["log"]["miete_offen"] += 1
            c["owner"]["m"] += miete; s["zufluss"]["miete"] += miete
            if c["owner"]["m"] >= c["kosten"]:
                c["owner"]["m"] -= c["kosten"]
            else:
                c["schieflage"] += 1; s["log"]["schieflage"] += 1; c["owner"]["m"] = 0
                if c["schieflage"] >= 2:
                    c["aktiv"] = False; s["log"]["wohn_umgedreht"] += 1; s["log"]["umgedreht"] += 1

# --------------------------------------------------- Ereignisse
ALT = ["Förderprogramm endet", "Kümmerin zieht weg", "Dürresommer", "Starkregen", "Zwanzig neue Nachbarn",
       "Spende", "Fläche nur für ein Jahr", "Sommerfest", "Kita braucht Fläche", "Sanierung"]
NEU = ["Bank verlangt Eigenkapital", "Gründungsprüfung", "Mitglied tritt aus"]

def ereignis(s, rng):
    g = s["geno"]
    namen = ALT + (NEU if s["A"]["neue_ereignisse"] else [])
    for _ in range(10):  # passt eine Genossenschaftskarte nicht, wird neu gezogen
        e = rng.choice(namen)
        if e in NEU and not g["gegruendet"]: continue
        if e == "Mitglied tritt aus" and not any(c["belegt"] > len(c["mitglieder"]) for c in wohnkarten(s)): continue
        break
    s["log"]["ev_" + e] += 1
    if e not in NEU:
        orig = rng.choice
        rng.choice = lambda seq, _e=e: _e if seq is not None and _e in seq else orig(seq)
        try: L3.ereignis(s, rng)
        finally: rng.choice = orig
        return
    if e == "Bank verlangt Eigenkapital":
        g["eigenkapital"] = True
    elif e == "Gründungsprüfung":
        if len(g["gruppen"]) < 3:
            dritte = [o for o in s["spieler"] if o["gruppe"] not in g["gruppen"] and o["k"] > 0]
            if dritte:
                o = max(dritte, key=lambda o: o["k"]); o["k"] -= 1; g["gruppen"].add(o["gruppe"])
                s["log"]["pruefung_bestanden"] += 1
            else:
                g["sperre"] = True; s["log"]["pruefung_sperre"] += 1
    elif e == "Mitglied tritt aus":
        c = rng.choice([c for c in wohnkarten(s) if c["belegt"] > len(c["mitglieder"])])
        c["belegt"] -= 1
        if g["m"] >= 1: g["m"] -= 1
        s["log"]["austritt"] += 1

# --------------------------------------------------- Partie
def partie(A, rng):
    s = neues_spiel(A, rng)
    k0 = sum(sp["k"] for sp in s["spieler"])
    for r in range(A["runden"]):
        s["runde"] = r
        if r > 0: wirtschaften(s)
        s["geno"]["sperre"] = s["geno"].get("sperre_naechste", False); s["geno"]["sperre_naechste"] = False
        nach = A["foerderung"][min(r, len(A["foerderung"]) - 1)]
        for sp in s["spieler"]: sp["m"] += nach
        s["zufluss"]["foerderung"] += nach * len(s["spieler"])
        order = s["spieler"][:]; rng.shuffle(order)
        for sp in order:
            zug(s, sp, rng, r)
            if sp["extra"] and r == 1 and zug(s, sp, rng, r): sp["extra"] = False
        L3.zuzug(s, rng)
        if A["ereignisse"]:
            sperre_vorher = s["geno"]["sperre"]; s["geno"]["sperre"] = False
            ereignis(s, rng)
            s["geno"]["sperre_naechste"] = s["geno"]["sperre"]; s["geno"]["sperre"] = sperre_vorher
    wirtschaften(s)
    wk = [c for c in s["karten"] if c["name"] in WOHNEN]
    def wunsch_ok(sp):
        if sp["wunsch"] == "Tiny House / Jurte" and A["genossenschaft"]: return sp["mitglied"]
        return WUENSCHE[sp["wunsch"]](s)
    tiny = [wunsch_ok(sp) for sp in s["spieler"] if sp["wunsch"] == "Tiny House / Jurte"]
    return dict(
        ziele={z: ZIELE[z](s) for z in s["ziele"]},
        wuensche=statistics.mean(wunsch_ok(sp) for sp in s["spieler"]),
        tiny=tiny,
        gruen=sum(c["platz"] for c in aktive(s) if "Gruen" not in c["tags"]) <= sum(s["kap"].values()) / 2,
        gegruendet=s["geno"]["gegruendet"], gruendungsrunde=s["geno"]["runde"],
        gruendung_gruppen=len(s["geno"]["gruppen"]) if s["geno"]["gegruendet"] else 0,
        kasse=s["geno"]["m"],
        m_ende=statistics.mean(sp["m"] for sp in s["spieler"]),
        wohnprojekte=len(wk),
        belegung=[c["belegt"] / c["einheiten"] for c in wk if c["aktiv"]],
        traegt=[traegt_sich(s, c) for c in wk if c["aktiv"]],
        haushalte=sum(c["belegt"] - len(c["mitglieder"]) for c in wk),
        log=s["log"], zufluss=s["zufluss"],
    )

def szenario(A, n=1500, seed=4):
    rng = random.Random(seed)
    res = [partie(dict(A), rng) for _ in range(n)]
    ok, cnt, log = Counter(), Counter(), Counter()
    for r in res:
        for z, v in r["ziele"].items(): cnt[z] += 1; ok[z] += v
        log.update(r["log"])
    gr = [r for r in res if r["gegruendet"]]
    bel = [b for r in res for b in r["belegung"]]; tr = [t for r in res for t in r["traegt"]]
    tiny = [t for r in res for t in r["tiny"]]
    runden = Counter(max(0, r["gruendungsrunde"] + 1) for r in gr)
    return dict(
        gewonnen=statistics.mean(all(r["ziele"].values()) for r in res),
        gegruendet=len(gr) / n,
        gruendung_in_runde={k: round(v / n, 2) for k, v in sorted(runden.items())},
        gruendung_drei_gruppen=statistics.mean(r["gruendung_gruppen"] >= 3 for r in gr) if gr else 0,
        wohnprojekte_pro_partie=statistics.mean(r["wohnprojekte"] for r in res),
        belegung_wohnprojekte=statistics.mean(bel) if bel else 0,
        anteil_traegt_sich=statistics.mean(tr) if tr else 0,
        wohn_umgedreht_pro_partie=log["wohn_umgedreht"] / n,
        haushalte_mittel=statistics.mean(r["haushalte"] for r in res),
        haushalte_verloren=log["haushalt_verloren"] / n,
        tiny_wunsch_erfuellt=statistics.mean(tiny) if tiny else 0,
        beitritte_pro_partie=log["beitritt"] / n,
        kasse_ende=statistics.mean(r["kasse"] for r in gr) if gr else 0,
        mittel_rest_pro_person=statistics.mean(r["m_ende"] for r in res),
        haelfte_gruen=statistics.mean(r["gruen"] for r in res),
        wuensche=statistics.mean(r["wuensche"] for r in res),
        pruefung_sperre=log["pruefung_sperre"] / n, austritte=log["austritt"] / n,
        ziele={z: round(ok[z] / cnt[z], 2) for z in ZIELE if cnt[z]},
        kartenhaeufigkeit={k[6:]: round(v / n, 2) for k, v in log.most_common() if k.startswith("karte_")},
    )

if __name__ == "__main__":
    S = {
        "A: Genossenschaft, Standard (3 Kümmerzeit aus 2 Gruppen, 2 Mittel)": {},
        "B: ohne Genossenschaft (= Lauf 3, Empfehlung)": dict(genossenschaft=False, neue_ereignisse=False),
        "C: leichtere Gründung (2 Kümmerzeit, 1 Mittel)": dict(gruendung_k=2, gruendung_m=1),
        "D: schwerere Gründung (4 Kümmerzeit aus 3 Gruppen)": dict(gruendung_k=4, gruendung_gruppen=3),
        "E: Förderung 1-1-0": dict(foerderung=(1, 1, 0)),
        "F: Förderung 2-0-0": dict(foerderung=(2, 0, 0)),
        "G: ohne neue Ereignisse": dict(neue_ereignisse=False),
        "H: Plan B (4 Pers., 2 Haushalte)": dict(personen_pro_gruppe=1, haushalte_pro_runde=2),
        "M: Empfehlung (Standard + Förderung 1-1-0)": dict(foerderung=(1, 1, 0)),
        "N: Empfehlung Plan B (Genossenschaft besteht schon, 1-1-0, 2 Haushalte)": dict(
            foerderung=(1, 1, 0), personen_pro_gruppe=1, haushalte_pro_runde=2, gegruendet_start=True),
        "I: Wohnbau erst ab Folgerunde": dict(bau_ab_folgerunde=True),
        "J: 3 Kümmerzeit aus 3 Gruppen": dict(gruendung_gruppen=3),
        "K: 3 aus 3 Gruppen, Förderung 1-1-0": dict(gruendung_gruppen=3, foerderung=(1, 1, 0)),
        "L: Plan B, 3 aus 3 Gruppen, 1-1-0, 2 Haushalte": dict(gruendung_gruppen=3, foerderung=(1, 1, 0),
                                                                      personen_pro_gruppe=1, haushalte_pro_runde=2),
    }
    out = {name: szenario(dict(ANNAHMEN, **d)) for name, d in S.items()}
    json.dump(out, open("lauf4_ergebnisse.json", "w"), ensure_ascii=False, indent=1)
    keys = ["gewonnen", "gegruendet", "gruendung_drei_gruppen", "wohnprojekte_pro_partie", "belegung_wohnprojekte",
            "anteil_traegt_sich", "wohn_umgedreht_pro_partie", "haushalte_mittel", "haushalte_verloren",
            "tiny_wunsch_erfuellt", "beitritte_pro_partie", "kasse_ende", "mittel_rest_pro_person", "haelfte_gruen",
            "pruefung_sperre", "austritte"]
    for name, r in out.items():
        print(f"\n=== {name}")
        print("  " + "  ".join(f"{k}={round(r[k], 2)}" for k in keys))
        print("  gründung in runde", r["gruendung_in_runde"], " ziele", r["ziele"])
    print("\nKarten A:", out[next(iter(out))]["kartenhaeufigkeit"])
