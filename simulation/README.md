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
