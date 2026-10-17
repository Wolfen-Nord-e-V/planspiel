# Regel-Simulation

Zwei Python-Skripte spielen viele Partien des Planspiels mit einfachen, kooperativen Spielerstrategien durch. Sie prüfen, ob die Zahlen des [Regelwerks](../regelwerk.md) zusammenpassen: Reichen Kümmerzeit, Mittel und Fläche? Welche Quartiersziele sind zu leicht oder zu schwer?

**Was nicht simuliert wird:** Verhandlungen, Veto, Teilen und Konfliktrunde. Die simulierten Spieler handeln rational und zielorientiert, echte Menschen nicht. Die Ergebnisse taugen zum Justieren der Zahlen, nicht als Prognose für den Ablauf am Tisch.

## Ausführen

Benötigt nur Python 3, keine weiteren Pakete.

```
python3 lauf1_raster.py     # ca. 1–2 Minuten
python3 lauf2_flaechen.py   # ca. 1 Minute
```

Alle Platzhalterwerte stehen oben in den Skripten (`ANNAHMEN`, `GRUPPEN`, `KARTEN`, in Lauf 2 zusätzlich `FLAECHEN`). Ergebnisse werden als JSON gespeichert.

## Lauf 1 – abstraktes Raster (14.10.2026)

`lauf1_raster.py`, Ergebnisse in `lauf1_ergebnisse.json`. Annahmen: 8 Personen, 3 Runden, Raster 4 × 4 mit 14 freien Feldern, 2 Mittel Nachschub pro Person und Runde, 2 Exemplare je Baukarte, je 1.500 Partien pro Szenario.

- Die Fläche war nach knapp zwei Runden voll, danach passte jeder zweite Zug.
- Mittel gab es im Überfluss (über 5 übrig pro Person).
- Ein Drittel der Kümmer-Chips blieb ungenutzt; „Kein Chip übrig“ gelang nur in 3 % der Partien.
- Sechs von acht Quartierszielen wurden in 95–100 % der Partien erreicht.

## Lauf 2 – Flächen mit Kapazität (14.10.2026)

`lauf2_flaechen.py`, Ergebnisse in `lauf2_ergebnisse.json`. Statt des Rasters die freigegebenen Flächen und Gebäude mit Kapazität in Flächenpunkten (abgeleitet aus der Flächenbilanz der Begründung zum Bebauungsplan, ca. 250 m² je Punkt), Baukarten mit Platzbedarf. „Benachbart“ heißt „auf derselben Fläche“. Die Garagen waren noch mit 3 statt 5 Punkten angesetzt (Zählung erst am 15.10.2026).

| Szenario | Kapazität | Gewinnquote | Karten pro Person in Runde 3 | Mittel übrig pro Person | Kümmerzeit gebunden |
| --- | --- | --- | --- | --- | --- |
| 8 Personen, Nachschub 1 | 43 | 71 % | 0,5 | 1,2 | 94 % |
| 8 Personen, Nachschub 2 | 43 | 59 % | 0,7 | 2,7 | 94 % |
| 8 Personen, Nachschub 1, Plan verkleinert | 32 | 55 % | 0,2 | 1,8 | 90 % |
| Plan B (4 Personen) | 43 | 75 % | 1,0 | 0,8 | 92 % |
| Plan B, Plan verkleinert | 26 | 62 % | 0,9 | 0,9 | 94 % |

- **Kapazität aus dem Bebauungsplan und 1 Mittel Nachschub ergeben das ausgewogenste Spiel.** Fläche, Mittel und Kümmerzeit werden alle knapp, aber erst in der dritten Runde. „Kein Chip übrig“ gelingt jetzt in 70 % der Partien.
- **Mit 2 Mittel Nachschub wird zu viel gebaut.** „Hälfte grün/offen“ gelingt dann nur noch in 37 % der Partien.
- **Plan B mit vollem Plan spielen.** Bei verkleinertem Plan gelingt „Drei Generationen“ nur noch in 16 % der Partien.
- **Gebäude bleiben eher leer** (ca. 70 % belegt), Bau- und Grünland sind fast voll.
- **Kleine, billige Karten dominieren.** Tauschschrank, Imkerei sowie Wege und Bänke werden fast immer gelegt, Gemeinschaftsküche, Bolzplatz, Kleingewerbe-Hof und Regenrückhaltefläche selten.
- **„Treffpunkt in 5 Minuten“, „Läuft nach Förderende“ und „Jede Gruppe gelegt“ sind geschenkt**; „Drei Generationen“ (ca. 70 %) und „Kein Chip übrig“ sind echte Herausforderungen.
- **Ereignisse:** Im Schnitt werden knapp zwei Karten pro Partie umgedreht – spürbar, aber nicht zerstörerisch.

## Lauf 3 – Wirtschaften und Wohnen (17.10.2026)

`lauf3_wirtschaft.py`, Ergebnisse in `lauf3_ergebnisse.json`. Baut auf Lauf 2 auf (Garagen jetzt mit 5 Punkten) und ergänzt Erträge, Ausbau, auslaufende Fördermittel (2, 1, 0 Mittel pro Person), Wohnprojekte mit Wohneinheiten und laufenden Kosten sowie Zuzug über Haushaltskarten. Je zwei Haushalte bringen 1 neue Kümmerzeit. Die Regeln stehen im [Regelwerk](../regelwerk.md#erweiterung-wirtschaften-und-wohnen-entwurf-17102026). Je 1.500 Partien, 8 Personen, wenn nicht anders angegeben.

| Szenario | Gewinnquote | Wohnprojekte tragen sich | Belegung | Wohnprojekte umgedreht je Partie | Haushalte eingezogen / verloren | eigene Einnahmen | Mittel übrig pro Person |
| --- | --- | --- | --- | --- | --- | --- | --- |
| A: Basis (Kosten 3, Erträge bis 2, 2 Exemplare je Karte) | 51 % | 48 % | 39 % | 1,1 | 5,2 / 4,0 | 62 % | 2,8 |
| B: Förderung konstant 1 | 50 % | 42 % | 35 % | 0,9 | 4,8 / 4,4 | 61 % | 2,9 |
| C: ohne Erträge | 52 % | 67 % | 52 % | 2,0 | 5,9 / 3,2 | 31 % | 1,0 |
| D: Wohnkosten 2 | 47 % | 62 % | 35 % | 0,7 | 5,4 / 3,9 | 62 % | 3,0 |
| E: 2 Haushalte je Runde | 53 % | 34 % | 28 % | 1,4 | 3,5 / 2,8 | 60 % | 2,6 |
| F: 5 Haushalte je Runde | 42 % | 66 % | 54 % | 0,8 | 8,4 / 6,5 | 66 % | 3,2 |
| G: ohne Kümmerzeit durch Zuzug | 66 % | 50 % | 40 % | 1,1 | 5,2 / 3,9 | 62 % | 2,7 |
| H: 1 Exemplar je Karte | 45 % | 80 % | 63 % | 0,9 | 5,2 / 4,0 | 55 % | 3,2 |
| I: Plan B (4 Personen) | 67 % | 59 % | 46 % | 0,5 | 2,6 / 6,7 | 66 % | 3,3 |
| **J: Empfehlung** (1 Exemplar, Kosten 2, Ertrag 1, Zuzug-Chips zählen nicht für „Kein Chip übrig“) | **63 %** | **88 %** | **56 %** | **0,5** | **5,6 / 3,7** | **51 %** | **3,0** |
| **K: Empfehlung Plan B** (4 Personen, 2 Haushalte je Runde) | **82 %** | **66 %** | **37 %** | **0,3** | **2,3 / 4,1** | **54 %** | **2,1** |

„Wohnprojekte tragen sich“ und „Belegung“ beziehen sich auf die am Ende noch aktiven Wohnprojekte.

- **Der Kreislauf trägt, kippt aber nicht.** Auch in guten Partien ziehen selten mehr als 8 Haushalte ein (90-%-Wert), der Haushaltsstapel begrenzt das Wachstum. Ein Davonlaufen einzelner Gruppen zeigt sich nicht.
- **Ohne Begrenzung entsteht zu viel Wohnraum für zu wenig Nachfrage.** Mit zwei Exemplaren je Karte werden fast drei Wohnprojekte je Partie gebaut, bei etwa neun Zuzugsinteressierten. Die Hälfte der Projekte trägt sich dann nicht – realistisch für Wolfen-Nord, aber frustrierend am Tisch. Mit einem Exemplar je Karte und Kosten 2 tragen sich 88 %.
- **Familien gehen am häufigsten verloren**, im Schnitt 1,3–1,5 je Partie: Sie finden keinen Ort mit „Kinder“ neben einer freien Wohnung. Das ist die gewünschte Erkenntnis: Wohnen braucht das Quartier drumherum.
- **Erträge bis 2 Mittel sind zu stark.** Ertragskarten (SoLaWi, Imkerei, Kleingewerbe-Hof) werden dann fast immer gebaut und verdrängen soziale Orte wie Spielplatz und Gemeinschaftsküche. Mit 1 Mittel Ertrag je Karte stammt etwa die Hälfte der Einnahmen aus eigenem Wirtschaften.
- **Zuzug-Chips und „Kein Chip übrig“ beißen sich.** Neue Kümmer-Chips machen das Ziel fast unerreichbar (21 %). Zählen sie nicht mit, gelingt es in 83 % der Partien.
- **Der Ausbau wird genutzt** (gut einmal je Partie), ohne zu dominieren.
- **Weiterhin zu viel Geld:** Am Ende bleiben rund 3 Mittel pro Person übrig, und „Hälfte grün/offen“ gelingt in der Empfehlung nur noch in 44 % der Partien. Als Nächstes testen: Förderung 1-1-0 oder 2-0-0.
- **Plan B:** Mit 2 Haushalten je Runde bleibt die Belegung niedrig (37 %). In jeder zehnten Partie wird gar kein Wohnprojekt gebaut.
