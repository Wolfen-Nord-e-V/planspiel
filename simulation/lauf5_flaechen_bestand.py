"""
Regel-Simulation „Wer baut Wolfen-Nord?“ – Lauf 5: Flächenkonzepte, Bestand und Verdrängung (18.10.2026)

Baut auf Lauf 4 (Wohnwiesengenossenschaft, Empfehlung M) auf. Neu:

- Statt der Wohnkarte mit festen 6 Plätzen: Wohnwiesen werden erschlossen (einmalige Kosten,
  laufende Erschließungskosten aus der Kasse); darauf entstehen einzelne Häuschen (½ Flächenpunkt).
- Eine Fläche für „Mobiles Wohnen“ (Probewohnen): günstig, ohne Bedingung, aber nach einer Runde
  bleiben die Haushalte nur, wenn sie einen festen Platz finden, sonst ziehen sie weiter.
- Eine zentrale Gemeinschaftsfläche der Genossenschaft, frei gewählt. Gemeinschaftskarten werden
  ab einer Zahl von Haushalten freigeschaltet und wirken für alle Wohnflächen.
- Bestand auf dem Plan: Gemeinschaftsgarten, Pavillon-Treffpunkt, Bienenstand, Trampelpfad,
  Kartoffelacker (auf Probe). Bauen auf belegtem Bestand heißt verlagern oder verdrängen.
- Störungen (Parkplatz, abendlicher Garten, Müll am Pavillon) halten Haushalte fern, bis sie
  behoben sind (Patenschaft mit Kümmerzeit oder Grünkarte als Puffer).
- Ziel „Hälfte grün/offen“ entfällt; neu: „Drei Grünorte gepflegt“, „Kein gewachsener Ort verloren“.

Nicht modelliert: Verhandlungen, Veto, Teilen, Konfliktrunde, Lage der Flächen zueinander.
"""
import random, statistics, json
from collections import Counter
import lauf3_wirtschaft as L3
import lauf4_genossenschaft as L4
from lauf3_wirtschaft import (FLAECHEN, KARTEN, WOHNEN, HAUSHALTE, GRUPPEN, EINNAHMEN, UM_84, WUENSCHE,
                              WUNSCH_KARTEN, aktive, tags_auf, frei, aktiv)
from lauf4_genossenschaft import finanzierung, bezahlen, gruendung_moeglich, gruenden

# ---------------------------------------------------------------- Plan anpassen
FLAECHEN["TG 1.2 Wiese an der Turnhalle"] = ("Bau", 4)        # geschätzt: TG 1.2 ohne Turnhalle
FLAECHEN["Gemeinschaftsgarten"] = ("Gruen", 4)                # Kirchengrund, Platz für mehr
L3.BESTAND = {"Kulturzentrum 84": {"Begegnung", "Jung"}}      # übriger Bestand jetzt als Marker

ANNAHMEN = dict(L4.ANNAHMEN,
    foerderung=(1, 1, 0),
    erschliessung_m=2, erschliessung_k=1, erschliessung_laufend=2,
    haus_platz=0.5, haus_miete=1,
    mobil=True, mobil_m=1,
    schwelle_1=6, schwelle_2=10,
    bestand=True, stoerungen=True,
    verdraengen_strafe=2.0,         # wie ungern die simulierten Spieler verdrängen
    ww_mindestbelegung=0,           # neue Wohnwiese erst, wenn jede bestehende so viele Häuschen hat (0 = aus)
    mobil_bleiben_frei=False,       # True: nach dem Probewohnen bleibt man, wenn irgendwo Platz frei ist
)

BESTAND5 = [  # Name, Fläche, Tags, Platz, Störung auf Flächen, vorläufig
    ("Gemeinschaftsgarten", "Gemeinschaftsgarten", {"Gruen", "Essen", "Begegnung"}, 1, {"TG 1.2 Wiese an der Turnhalle"}, False),
    ("Pavillon-Treffpunkt", "TG 3 Fläche am 84er", {"Begegnung", "Jung"}, 1, {"TG 3 Fläche am 84er", "Kulturzentrum 84"}, False),
    ("Bienenstand", "TG 3 Fläche am 84er", {"Gruen", "Handwerk"}, 1, set(), False),
    ("Trampelpfad", "TG 1.1 Wiese an der Schule", {"Weg"}, 1, set(), False),
    ("Kartoffelacker (auf Probe)", "TG 1.2 Wiese an der Turnhalle", {"Gruen", "Essen"}, 2, set(), True),
]
STOERUNG_EXTERN = [("Parkplatz Jeßnitzer Wende", {"TG 1.2 Wiese an der Turnhalle"})]

GEMEIN = {  # Mittel, Kümmer, Tags, Platz, Schwelle (1/2), Ertrag
    "Lastenradstation": (2, 1, {"Weg"}, 1, 1, 0),
    "Gemeinschaftshaus mit Küche": (3, 2, {"Begegnung", "Kinder", "Alt"}, 2, 1, 0),
    "Sauna und Wellness-Oase": (4, 2, {"Begegnung", "Alt"}, 2, 2, 1),
}
UMFELD = {"Kinder", "Alt", "Begegnung", "Handwerk", "Jung", "Weg"}
DUMMY = lambda: dict(gruppe="Bestand", m=99, k=99, hh=0)

def karte(**kw):
    c = dict(name="", f="", tags=set(), platz=0, gebunden=0, aktiv=True, gruppe=None, owner=None, stufe=1,
             ertrag=0, belegt=0, schieflage=0, mitglieder=[], typ="karte")
    c.update(kw); return c

# ---------------------------------------------------------------- Spielaufbau
def neues_spiel(A, rng):
    s = L4.neues_spiel(A, rng)
    s["deck"]["Gemeinschaftswohnen"] = 0
    s["konzept"], s["stoer"], s["mobil"], s["gemein_gebaut"] = {}, [], [], set()
    s["kassen_schieflage"] = 0
    s["ziele"] = rng.sample(list(ZIELE), 3)
    if A["bestand"]:
        s["deck"]["Kartoffelacker"] = 0
        for name, f, tags, platz, stoer, vorl in BESTAND5:
            c = karte(name=name, f=f, tags=set(tags), platz=platz, owner=DUMMY(), typ="bestand",
                      vorlaeufig=vorl, geschuetzt=False, ertrag=1 if vorl else 0)
            s["karten"].append(c)
            if stoer and A["stoerungen"]:
                s["stoer"].append(dict(name=name, flaechen=set(stoer), aktiv=True, quelle=c))
        # Bleibende schützen je einen Ort als „gewachsen“
        for sp in s["spieler"]:
            if sp["gruppe"] == "Bleibende":
                kand = [c for c in s["karten"] if c["typ"] == "bestand" and not c["vorlaeufig"] and not c["geschuetzt"]]
                if kand: rng.choice(kand)["geschuetzt"] = True
    if A["stoerungen"]:
        for name, fl in STOERUNG_EXTERN:
            s["stoer"].append(dict(name=name, flaechen=set(fl), aktiv=True, quelle=None))
    return s

# ---------------------------------------------------------------- Hilfen
def haeuser(s, f=None): return [c for c in aktive(s) if c["typ"] == "haus" and (f is None or c["f"] == f)]
def block(s): return [c for c in aktive(s) if c["name"] == "Umbau Leerstand"]
def haushalte_geno(s): return len(haeuser(s)) + sum(c["belegt"] for c in block(s))
def gemein_tags(s):
    t = set()
    for c in aktive(s):
        if c["typ"] == "gemein": t |= c["tags"]
    return t
def gestoert(s, f):
    return any(st["aktiv"] and f in st["flaechen"] for st in s["stoer"])

def stoerung_pruefen(s):
    """Störung erlischt, wenn die Quelle weg ist oder auf jeder betroffenen Wohnfläche ein Grün-Puffer liegt."""
    for st in s["stoer"]:
        if not st["aktiv"]: continue
        if st["quelle"] is not None and not st["quelle"]["aktiv"]:
            st["aktiv"] = False; continue
        if st.get("pate"): st["aktiv"] = False

def puffer(s, f):
    return any(c["typ"] == "karte" and "Gruen" in c["tags"] for c in aktive(s, f))

def platz_fuer_haus(s, f, A, mit_bedingung=None):
    if s["konzept"].get(f) != "Wohnwiese" or frei(s, f) < A["haus_platz"]: return False
    if gestoert(s, f) and not puffer(s, f): return False
    if mit_bedingung and mit_bedingung not in (tags_auf(s, f) | gemein_tags(s)): return False
    return True

# ---------------------------------------------------------------- Ziele und Wünsche
def nicht_bestand(s): return [c for c in aktive(s) if c["typ"] == "karte"]
ZIELE = {
    "Drei Generationen": lambda s: any({"Kinder", "Jung", "Alt"} <= (tags_auf(s, f) | (gemein_tags(s) if s["konzept"].get(f) == "Wohnwiese" else set())) for f in FLAECHEN),
    "Treffpunkt 5 Min": lambda s: True,
    "Läuft nach Förderende": lambda s: any(c["gebunden"] > 0 for c in nicht_bestand(s)),
    "Kein Chip übrig": lambda s: sum(sp["k"] for sp in s["spieler"]) == 0,
    "Einnahmen": lambda s: any(c["name"] in EINNAHMEN for c in nicht_bestand(s)),
    "84er verbunden": lambda s: sum(1 for c in nicht_bestand(s) if c["f"] in UM_84) >= 2,
    "Drei Grünorte gepflegt": lambda s: sum(1 for c in aktive(s) if "Gruen" in c["tags"] and c["gebunden"] > 0
                                             and (c["typ"] == "karte" or c.get("vorlaeufig"))) >= 3,
    "Kein gewachsener Ort verloren": lambda s: s["log"]["verdraengt"] + s["log"]["acker_beendet"] == 0,
    "Jede Gruppe gelegt": lambda s: set(GRUPPEN) <= {c["gruppe"] for c in s["karten"] if c["typ"] != "bestand"},
}
def wunsch_ok(s, sp):
    w = sp["wunsch"]
    if w == "Tiny House / Jurte": return sp["mitglied"]
    if w == "Trampelpfad bleibt": return any(c["name"] == "Trampelpfad" for c in aktive(s))
    if w == "Weg zum Kaufmarkt": return any("Weg" in c["tags"] for c in nicht_bestand(s))
    if w == "Verein sichtbar": return any(c["f"] in UM_84 and "Begegnung" in c["tags"] for c in nicht_bestand(s))
    return WUENSCHE[w](s)

# ---------------------------------------------------------------- Zug
def bestand_ausweichen(s, f, bedarf):
    """Liefert (bestandskarte, ziel) für Verlagern oder (bestandskarte, None) für Verdrängen, sonst None."""
    opts = []
    for b in aktive(s, f):
        if b["typ"] != "bestand" or b["geschuetzt"]: continue
        if frei(s, f) + b["platz"] < bedarf: continue
        typ_b = "Gruen" if "Gruen" in b["tags"] else None
        ziele = [g for g, v in FLAECHEN.items() if g != f and frei(s, g) >= b["platz"] and (typ_b is None or v[0] in ("Gruen", "Bau"))]
        opts.append((b, ziele[0] if ziele else None))
    return opts

def zug(s, sp, rng, runde):
    A = s["A"]; rest = A["runden"] - runde; g = s["geno"]
    offen = [z for z in s["ziele"] if not ZIELE[z](s)]
    opts = []
    wb = L4.wohnbau_erlaubt(s)
    def gewicht_basis(name, f, tags, kk, partner, ertrag):
        w = rng.random()
        if name in WUNSCH_KARTEN.get(sp["wunsch"], []): w += 3
        if sp["wunsch"] == "Kein Gewerbehof" and name == "Kleingewerbe-Hof": w -= 10
        if "Einnahmen" in offen and name in EINNAHMEN: w += 2
        if "84er verbunden" in offen and f in UM_84: w += 2
        if "Drei Generationen" in offen and tags & {"Kinder", "Jung", "Alt"}: w += 1
        if "Drei Grünorte gepflegt" in offen and "Gruen" in tags and kk > 0: w += 1.5
        if "Kein Chip übrig" in s["ziele"] and kk > 0: w += 1.5
        if partner: w += 0.5
        if ertrag: w += 0.6 * min(ertrag, A["ertrag_max"]) * rest
        if s["konzept"].get(f) == "Wohnwiese": w += 0.7 * len(tags & UMFELD)
        if gestoert(s, f) and "Gruen" in tags and s["konzept"].get(f) in ("Wohnwiese", "Mobil"): w += 2
        return w
    # 1. normale Baukarten, ggf. mit Verlagern oder Verdrängen von Bestand
    for name, n in s["deck"].items():
        if n <= 0: continue
        m, k, tags, typen, platz, ertrag = KARTEN[name]
        if name in WOHNEN and not wb: continue
        for f, v in FLAECHEN.items():
            if v[0] not in typen: continue
            if s["konzept"].get(f) == "Mobil" and name not in ("Tauschschrank", "Wege+Baenke"): continue
            varianten = []
            if frei(s, f) >= platz: varianten.append((None, None))
            elif A["bestand"]:
                for b, ziel in bestand_ausweichen(s, f, platz):
                    varianten.append((b, ziel))
            for b, ziel in varianten:
                kk = k; partner = f if (k > 0 and f not in s["bonus_used"] and tags & tags_auf(s, f)) else None
                if partner: kk -= 1
                extra_k = 1 if (b is not None and ziel is not None) else 0
                if not finanzierung(s, sp, m, kk + extra_k, mit_pool=True)[0]: continue
                w = gewicht_basis(name, f, tags, kk, partner, ertrag)
                if b is not None:
                    w -= 0.5 if ziel is not None else A["verdraengen_strafe"]
                    if "Kein gewachsener Ort verloren" in s["ziele"] and ziel is None: w -= 3
                opts.append((w, "bau", dict(name=name, f=f, m=m, kk=kk, partner=partner, b=b, ziel=ziel, extra_k=extra_k)))
    # 2. Ausbau
    if A["ausbau"]:
        for c in aktive(s):
            if c["owner"] is sp and c["typ"] == "karte" and c["name"] in EINNAHMEN and c["stufe"] < 2 and frei(s, c["f"]) >= 1:
                if finanzierung(s, sp, 1, 1)[0]:
                    opts.append((rng.random() + 0.6 * rest + 0.5, "ausbau", dict(c=c)))
    # 3. Gründung
    plan = gruendung_moeglich(s, sp)
    if plan:
        opts.append((rng.random() + 1.5 + rest + (3 if sp["wunsch"] in ("Tiny House / Jurte", "Kein Leerstand") else 0), "gruendung", dict(plan=plan)))
    if g["gegruendet"]:
        bauflaechen = [f for f, v in FLAECHEN.items() if v[0] == "Bau" and f not in s["konzept"]]
        # 4. Wohnwiese erschließen
        voll_genug = all(len(haeuser(s, f)) >= A["ww_mindestbelegung"] for f, v in s["konzept"].items() if v == "Wohnwiese")
        if wb and voll_genug:
            for f in bauflaechen:
                if frei(s, f) < 1: continue
                if not finanzierung(s, sp, A["erschliessung_m"], A["erschliessung_k"], mit_pool=True)[0]: continue
                w = rng.random() + 1.5 + 0.5 * rest + 0.5 * len(tags_auf(s, f) & UMFELD)
                if sp["wunsch"] == "Tiny House / Jurte" and not sp["mitglied"]: w += 2
                if gestoert(s, f): w -= 1
                if not any(v == "Wohnwiese" for v in s["konzept"].values()): w += 1
                opts.append((w, "erschliessen", dict(f=f)))
        # 5. Mobiles Wohnen
        if A["mobil"] and "Mobil" not in s["konzept"].values():
            for f in bauflaechen:
                if frei(s, f) >= 1 and sp["m"] >= A["mobil_m"]:
                    opts.append((rng.random() + 1.0 + 0.4 * rest - (0.5 if not gestoert(s, f) else 0), "mobil", dict(f=f)))
        # 6. Gemeinschaftsfläche festlegen
        if "Gemeinschaft" not in s["konzept"].values():
            for f, v in FLAECHEN.items():
                if v[0] in ("Bau", "Gebaeude") and f not in s["konzept"] and frei(s, f) >= 2:
                    opts.append((rng.random() + 0.8 + (1.5 if haushalte_geno(s) >= A["schwelle_1"] - 2 else 0), "gemeinflaeche", dict(f=f)))
        # 7. Gemeinschaftskarte
        gf = next((f for f, v in s["konzept"].items() if v == "Gemeinschaft"), None)
        if gf:
            hh = haushalte_geno(s)
            for name, (m, k, tags, platz, stufe, ertrag) in GEMEIN.items():
                if name in s["gemein_gebaut"] or frei(s, gf) < platz: continue
                if hh < (A["schwelle_1"] if stufe == 1 else A["schwelle_2"]): continue
                aus_kasse = min(g["m"], m)
                if not finanzierung(s, sp, m - aus_kasse, k, mit_pool=True)[0]: continue
                opts.append((rng.random() + 3, "gemein", dict(name=name, f=gf, aus_kasse=aus_kasse)))
        # 8. Beitritt mit eigenem Häuschen
        if sp["wunsch"] == "Tiny House / Jurte" and not sp["mitglied"]:
            fl = [f for f in FLAECHEN if s["konzept"].get(f) == "Wohnwiese" and frei(s, f) >= A["haus_platz"]]
            if fl and finanzierung(s, sp, A["mitglied_m"], A["mitglied_k"])[0]:
                opts.append((rng.random() + 4, "beitritt", dict(f=fl[0])))
    # 9. Kartoffelacker in Pflege nehmen
    for c in aktive(s):
        if c.get("vorlaeufig") and c["gebunden"] == 0 and sp["k"] >= 1:
            opts.append((rng.random() + 1.5 + (2 if "Kein gewachsener Ort verloren" in s["ziele"] else 0)
                         + (1 if "Drei Grünorte gepflegt" in s["ziele"] else 0), "pflege", dict(c=c)))
    # 10. Störung per Patenschaft beheben
    for st in s["stoer"]:
        if st["aktiv"] and st["quelle"] is not None and finanzierung(s, sp, 0, 1, mit_pool=True)[0]:
            betrifft = any(s["konzept"].get(f) in ("Wohnwiese", "Mobil", "Gemeinschaft") for f in st["flaechen"])
            opts.append((rng.random() + (2 if betrifft else 0.2), "pate", dict(st=st)))
    if not opts:
        s["log"]["passen"] += 1; return False
    w, art, d = max(opts, key=lambda o: o[0])
    return ausfuehren(s, sp, art, d, runde)

def ausfuehren(s, sp, art, d, runde):
    A, g = s["A"], s["geno"]
    if art == "gruendung":
        gruenden(s, sp, d["plan"], runde); return True
    if art == "ausbau":
        bezahlen(s, sp, 1, 1); c = d["c"]; c["stufe"] += 1; c["platz"] += 1; c["gebunden"] += 1; s["log"]["ausbau"] += 1; return True
    if art == "erschliessen":
        bezahlen(s, sp, A["erschliessung_m"], A["erschliessung_k"], mit_pool=True)
        s["konzept"][d["f"]] = "Wohnwiese"; s["log"]["wohnwiese"] += 1; s["log"]["ww_" + d["f"]] += 1; return True
    if art == "mobil":
        sp["m"] -= A["mobil_m"]; s["konzept"][d["f"]] = "Mobil"; s["log"]["mobil_" + d["f"]] += 1; return True
    if art == "gemeinflaeche":
        s["konzept"][d["f"]] = "Gemeinschaft"; s["log"]["gf_" + d["f"]] += 1; return True
    if art == "gemein":
        m, k, tags, platz, stufe, ertrag = GEMEIN[d["name"]]
        g["m"] -= d["aus_kasse"]; bezahlen(s, sp, m - d["aus_kasse"], k, mit_pool=True)
        s["karten"].append(karte(name=d["name"], f=d["f"], tags=set(tags), platz=platz, gebunden=k, owner=g,
                                 gruppe=sp["gruppe"], ertrag=ertrag, typ="gemein"))
        s["gemein_gebaut"].add(d["name"]); s["log"]["gemein_" + d["name"]] += 1; return True
    if art == "beitritt":
        bezahlen(s, sp, A["mitglied_m"], A["mitglied_k"]); g["m"] += A["mitglied_m"]
        s["karten"].append(karte(name="Häuschen", f=d["f"], platz=A["haus_platz"], owner=g, gruppe=sp["gruppe"],
                                 typ="haus", mitglied=sp))
        sp["mitglied"] = True; s["log"]["beitritt"] += 1; return True
    if art == "pflege":
        sp["k"] -= 1; c = d["c"]; c["gebunden"] = 1; c["owner"] = sp; s["log"]["acker_pflege"] += 1; return True
    if art == "pate":
        bezahlen(s, sp, 0, 1, mit_pool=True); d["st"]["pate"] = True; stoerung_pruefen(s)
        s["log"]["pate_" + d["st"]["name"]] += 1; return True
    # Bau
    b, ziel = d["b"], d["ziel"]
    bezahlen(s, sp, d["m"], d["kk"] + d["extra_k"], mit_pool=True)
    if b is not None:
        if ziel is not None:
            b["f"] = ziel; s["log"]["verlagert"] += 1; s["log"]["verlagert_" + b["name"]] += 1
        else:
            b["aktiv"] = False; s["karten"].remove(b); s["log"]["verdraengt"] += 1; s["log"]["verdraengt_" + b["name"]] += 1
            for o in s["spieler"]:
                if o["gruppe"] == "Bleibende" and o["k"] > 0: o["k"] -= 1; break
            if b.get("vorlaeufig"): s["deck"]["Kartoffelacker"] += 1
            stoerung_pruefen(s)
    if d["partner"]: s["bonus_used"].add(d["partner"]); s["log"]["kombibonus"] += 1
    name = d["name"]; s["deck"][name] -= 1
    owner = g if name in WOHNEN else sp
    c = karte(name=name, f=d["f"], tags=set(KARTEN[name][2]), platz=KARTEN[name][4], gebunden=d["kk"], owner=owner,
              gruppe=sp["gruppe"], ertrag=KARTEN[name][5])
    if name in WOHNEN:
        c["einheiten"], kosten = WOHNEN[name]; c["kosten"] = round(kosten * A["wohnkosten_faktor"]); s["log"]["block"] += 1
    s["karten"].append(c); s["log"]["karte_" + name] += 1
    return True

# ---------------------------------------------------------------- Zuzug, Fluktuation, Wirtschaften
def fester_platz(s, tag):
    A = s["A"]
    wiesen = [f for f in FLAECHEN if platz_fuer_haus(s, f, A, tag)]
    bl = [c for c in block(s) if c["belegt"] < c["einheiten"] and (tag is None or tag in (tags_auf(s, c["f"]) | gemein_tags(s)))
          and not (gestoert(s, c["f"]) and not puffer(s, c["f"]))]
    return wiesen, bl

def einziehen(s, rng, h, wiesen, bl):
    g = s["geno"]
    ziel = rng.choice([("w", f) for f in wiesen] + [("b", c) for c in bl])
    if ziel[0] == "w":
        s["karten"].append(karte(name="Häuschen", f=ziel[1], platz=s["A"]["haus_platz"], owner=g, typ="haus", haushalt=h))
    else:
        ziel[1]["belegt"] += 1
    g["hh"] += 1; s["log"]["haushalt_eingezogen"] += 1
    n = s["A"]["kuemmer_je_haushalte"]
    if n and g["hh"] % n == 0: g["k"] += 1; s["log"]["kuemmer_durch_zuzug"] += 1

def zuzug(s, rng):
    A = s["A"]
    for _ in range(A["haushalte_pro_runde"]):
        if not s["haushalte"]: break
        h = s["haushalte"].pop(); tag = HAUSHALTE[h][0]
        wiesen, bl = fester_platz(s, tag)
        if wiesen or bl:
            einziehen(s, rng, h, wiesen, bl); continue
        mf = next((f for f, v in s["konzept"].items() if v == "Mobil"), None)
        if mf and frei(s, mf) >= A["haus_platz"]:
            s["karten"].append(karte(name="Wagen", f=mf, platz=A["haus_platz"], owner=s["geno"], typ="wagen", haushalt=h))
            s["log"]["probewohnen"] += 1; continue
        s["log"]["haushalt_verloren"] += 1; s["log"]["verloren_" + h] += 1
L3.zuzug = zuzug   # damit auch „Zwanzig neue Nachbarn“ diese Regeln nutzt

def fluktuation(s, rng):
    for c in [c for c in aktive(s) if c["typ"] == "wagen"]:
        s["karten"].remove(c)
        tag = None if s["A"]["mobil_bleiben_frei"] else HAUSHALTE[c["haushalt"]][0]
        wiesen, bl = fester_platz(s, tag)
        if wiesen or bl:
            einziehen(s, rng, c["haushalt"], wiesen, bl); s["log"]["probewohnen_geblieben"] += 1
            s["log"]["haushalt_eingezogen"] -= 1  # zählt als geblieben, nicht als neu
            s["log"]["haushalt_eingezogen_dauerhaft"] += 1
        else:
            s["log"]["weitergezogen"] += 1

def wirtschaften(s, rng):
    A, g = s["A"], s["geno"]
    for c in aktive(s):
        if A["ertrag"] and c["ertrag"] and c["gebunden"] > 0 and c["typ"] in ("karte", "bestand", "gemein"):
            x = min(c["ertrag"], A["ertrag_max"]) + (c["stufe"] - 1)
            c["owner"]["m"] += x; s["zufluss"]["ertrag"] += x
    einnahmen = 0
    for c in haeuser(s):
        if c.get("mitglied"):
            sp = c["mitglied"]
            if sp["m"] >= A["haus_miete"]: sp["m"] -= A["haus_miete"]; einnahmen += A["haus_miete"]
        else: einnahmen += A["haus_miete"]
    einnahmen += sum(A["haus_miete"] for c in aktive(s) if c["typ"] == "wagen")
    for c in block(s): einnahmen += c["belegt"] * A["miete"]
    kosten = A["erschliessung_laufend"] * sum(1 for v in s["konzept"].values() if v == "Wohnwiese")
    kosten += sum(c["kosten"] for c in block(s))
    g["m"] += einnahmen; s["zufluss"]["miete"] += einnahmen
    if g["m"] >= kosten: g["m"] -= kosten
    else:
        g["m"] = 0; s["kassen_schieflage"] += 1; s["log"]["schieflage"] += 1
        if s["kassen_schieflage"] >= 2:
            for c in block(s): c["aktiv"] = False; s["log"]["block_umgedreht"] += 1
    fluktuation(s, rng)

def acker_probezeit(s):
    for c in [c for c in aktive(s) if c.get("vorlaeufig")]:
        if c["gebunden"] == 0:
            s["karten"].remove(c); s["log"]["acker_beendet"] += 1; s["deck"]["Kartoffelacker"] += 1
        else:
            c["vorlaeufig"] = False; c["typ"] = "karte"; c["name"] = "Kartoffelacker"; s["log"]["acker_verstetigt"] += 1

def ereignis(s, rng):
    g = s["geno"]
    namen = L4.ALT + (L4.NEU if s["A"]["neue_ereignisse"] else [])
    for _ in range(10):
        e = rng.choice(namen)
        if e in L4.NEU and not g["gegruendet"]: continue
        if e == "Mitglied tritt aus" and not ([c for c in haeuser(s) if not c.get("mitglied")] or any(c["belegt"] for c in block(s))): continue
        break
    if e not in L4.NEU:
        orig = rng.choice
        rng.choice = lambda seq, _e=e: _e if seq is not None and _e in seq else orig(seq)
        try: L3.ereignis(s, rng)
        finally: rng.choice = orig
        stoerung_pruefen(s); return
    if e == "Bank verlangt Eigenkapital": g["eigenkapital"] = True
    elif e == "Gründungsprüfung":
        if len(g["gruppen"]) < 3:
            dritte = [o for o in s["spieler"] if o["gruppe"] not in g["gruppen"] and o["k"] > 0]
            if dritte:
                o = max(dritte, key=lambda o: o["k"]); o["k"] -= 1; g["gruppen"].add(o["gruppe"])
            else: g["sperre"] = True
    elif e == "Mitglied tritt aus":
        hs = [c for c in haeuser(s) if not c.get("mitglied")]
        if hs: s["karten"].remove(rng.choice(hs))
        else: next(c for c in block(s) if c["belegt"])["belegt"] -= 1
        if g["m"] >= 1: g["m"] -= 1
        s["log"]["austritt"] += 1

# ---------------------------------------------------------------- Partie
def partie(A, rng):
    s = neues_spiel(A, rng)
    for r in range(A["runden"]):
        s["runde"] = r
        if r > 0: wirtschaften(s, rng)
        if r == 1: acker_probezeit(s)
        s["geno"]["sperre"] = s["geno"].get("sperre_naechste", False); s["geno"]["sperre_naechste"] = False
        nach = A["foerderung"][min(r, len(A["foerderung"]) - 1)]
        for sp in s["spieler"]: sp["m"] += nach
        s["zufluss"]["foerderung"] += nach * len(s["spieler"])
        order = s["spieler"][:]; rng.shuffle(order)
        for sp in order:
            zug(s, sp, rng, r)
            if sp["extra"] and r == 1 and zug(s, sp, rng, r): sp["extra"] = False
        zuzug(s, rng)
        if A["ereignisse"]:
            vorher = s["geno"]["sperre"]; s["geno"]["sperre"] = False
            ereignis(s, rng)
            s["geno"]["sperre_naechste"] = s["geno"]["sperre"]; s["geno"]["sperre"] = vorher
    wirtschaften(s, rng)
    hh = haushalte_geno(s)
    return dict(
        ziele={z: ZIELE[z](s) for z in s["ziele"]},
        alle_ziele={z: f(s) for z, f in ZIELE.items()},
        tiny=[wunsch_ok(s, sp) for sp in s["spieler"] if sp["wunsch"] == "Tiny House / Jurte"],
        wuensche=statistics.mean(wunsch_ok(s, sp) for sp in s["spieler"]),
        gegruendet=s["geno"]["gegruendet"], haushalte=hh, haeuschen=len(haeuser(s)),
        wohnwiesen=sum(1 for v in s["konzept"].values() if v == "Wohnwiese"),
        mobil="Mobil" in s["konzept"].values(), gemeinflaeche="Gemeinschaft" in s["konzept"].values(),
        schwelle1=hh >= A["schwelle_1"], schwelle2=hh >= A["schwelle_2"],
        kasse=s["geno"]["m"], m_ende=statistics.mean(sp["m"] for sp in s["spieler"]),
        stoer_aktiv=sum(1 for st in s["stoer"] if st["aktiv"]), log=s["log"],
    )

def szenario(A, n=1500, seed=5):
    rng = random.Random(seed)
    res = [partie(dict(A), rng) for _ in range(n)]
    log = Counter(); ok, cnt = Counter(), Counter(); alle = Counter()
    for r in res:
        log.update(r["log"])
        for z, v in r["ziele"].items(): cnt[z] += 1; ok[z] += v
        for z, v in r["alle_ziele"].items(): alle[z] += v
    tiny = [t for r in res for t in r["tiny"]]
    pick = lambda pre: {k[len(pre):]: round(v / n, 2) for k, v in log.most_common() if k.startswith(pre)}
    return dict(
        gewonnen=statistics.mean(all(r["ziele"].values()) for r in res),
        gegruendet=statistics.mean(r["gegruendet"] for r in res),
        haushalte=statistics.mean(r["haushalte"] for r in res),
        haeuschen=statistics.mean(r["haeuschen"] for r in res),
        wohnwiesen=statistics.mean(r["wohnwiesen"] for r in res),
        schwelle1=statistics.mean(r["schwelle1"] for r in res),
        schwelle2=statistics.mean(r["schwelle2"] for r in res),
        gemeinflaeche=statistics.mean(r["gemeinflaeche"] for r in res),
        mobil=statistics.mean(r["mobil"] for r in res),
        probewohnen=log["probewohnen"] / n, geblieben=log["probewohnen_geblieben"] / n, weitergezogen=log["weitergezogen"] / n,
        verloren=log["haushalt_verloren"] / n,
        verdraengt=log["verdraengt"] / n, verlagert=log["verlagert"] / n,
        acker_verstetigt=log["acker_verstetigt"] / n, acker_beendet=log["acker_beendet"] / n,
        stoerungen_offen=statistics.mean(r["stoer_aktiv"] for r in res),
        schieflage=log["schieflage"] / n,
        tiny=statistics.mean(tiny) if tiny else 0,
        wuensche=statistics.mean(r["wuensche"] for r in res),
        kasse=statistics.mean(r["kasse"] for r in res),
        mittel_rest=statistics.mean(r["m_ende"] for r in res),
        ziele={z: round(ok[z] / cnt[z], 2) for z in ZIELE if cnt[z]},
        ziele_erreicht_unabhaengig={z: round(v / n, 2) for z, v in alle.items()},
        wohnwiese_auf=pick("ww_"), mobil_auf=pick("mobil_"), gemeinflaeche_auf=pick("gf_"),
        gemeinschaftskarten=pick("gemein_"), verdraengt_was=pick("verdraengt_"), verlagert_was=pick("verlagert_"),
        paten=pick("pate_"), karten=pick("karte_"),
    )

if __name__ == "__main__":
    import sys
    S = {
        "A: Basis (Schwellen 6/10, Erschließung 2+1, laufend 2)": {},
        "B: Schwellen 4/8": dict(schwelle_1=4, schwelle_2=8),
        "C: ohne Mobiles Wohnen": dict(mobil=False),
        "D: Erschließung laufend 1": dict(erschliessung_laufend=1),
        "E: 4 Haushalte je Runde": dict(haushalte_pro_runde=4),
        "F: ohne Bestand und Störungen": dict(bestand=False, stoerungen=False),
        "G: Plan B (Genossenschaft besteht, 2 Haushalte)": dict(personen_pro_gruppe=1, haushalte_pro_runde=2, gegruendet_start=True),
        "H: neue Wohnwiese erst ab 3 Häuschen auf jeder bestehenden": dict(ww_mindestbelegung=3),
        "I: nach Probewohnen bleiben, wenn Platz frei": dict(mobil_bleiben_frei=True),
        "J: H + I + Schwellen 4/8": dict(ww_mindestbelegung=3, mobil_bleiben_frei=True, schwelle_1=4, schwelle_2=8),
        "L: Empfehlung (I + Schwellen 4/8 + Erschließung laufend 1)": dict(mobil_bleiben_frei=True, schwelle_1=4, schwelle_2=8,
                                                                       erschliessung_laufend=1),
        "M: Empfehlung Plan B": dict(mobil_bleiben_frei=True, schwelle_1=4, schwelle_2=8, erschliessung_laufend=1,
                                     personen_pro_gruppe=1, haushalte_pro_runde=2, gegruendet_start=True),
    }
    nur = sys.argv[1:]  # optional: nur Szenarien mit diesen Anfangsbuchstaben
    out = {name: szenario(dict(ANNAHMEN, **d)) for name, d in S.items() if not nur or name[0] in nur}
    json.dump(out, open("lauf5_ergebnisse.json", "w"), ensure_ascii=False, indent=1)
    keys = ["gewonnen", "haushalte", "haeuschen", "wohnwiesen", "schwelle1", "schwelle2", "gemeinflaeche", "mobil",
            "probewohnen", "geblieben", "weitergezogen", "verloren", "verdraengt", "verlagert", "acker_verstetigt",
            "acker_beendet", "stoerungen_offen", "schieflage", "tiny", "kasse", "mittel_rest"]
    for name, r in out.items():
        print(f"\n=== {name}")
        print("  " + "  ".join(f"{k}={round(r[k], 2)}" for k in keys))
        for k in ["ziele", "ziele_erreicht_unabhaengig", "wohnwiese_auf", "mobil_auf", "gemeinflaeche_auf", "gemeinschaftskarten", "verdraengt_was", "verlagert_was", "paten"]:
            print(f"  {k}: {r[k]}")
