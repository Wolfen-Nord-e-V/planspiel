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

## Lauf 4 – Wohngenossenschaft (17.10.2026)

`lauf4_genossenschaft.py`, Ergebnisse in `lauf4_ergebnisse.json`. Baut auf Lauf 3 mit dessen Empfehlung auf (ein Exemplar je Karte, Wohnkosten 2, Ertrag 1) und ergänzt die [Erweiterung Wohngenossenschaft](../regelwerk.md#erweiterung-wohngenossenschaft-17102026): Gründung als Voraussetzung für Wohnkarten, gemeinsame Kasse, Kümmer-Pool, Beitritt mit eigenem Tiny House, drei neue Ereignisse. Je 1.500 Partien, 8 Personen, wenn nicht anders angegeben.

| Szenario | Gewinnquote | gegründet | Wohnprojekte | tragen sich | umgedreht je Partie | Haushalte ein / verloren | Tiny-Wunsch erfüllt | Mittel übrig pro Person | „Hälfte grün“ erreicht |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| B: ohne Genossenschaft (= Lauf 3, Empfehlung) | 64 % | – | 2,0 | 88 % | 0,5 | 5,5 / 3,7 | 89 % | 3,0 | 45 % |
| A: Genossenschaft, Förderung 2-1-0 | 73 % | 100 % | 1,9 | 77 % | 0,2 | 4,8 / 4,4 | 69 % | 2,1 | 52 % |
| C: leichtere Gründung (2 Kümmerzeit, 1 Mittel) | 72 % | 100 % | 1,9 | 79 % | 0,4 | 4,7 / 4,4 | 80 % | 2,2 | 50 % |
| D: schwerere Gründung (4 Kümmerzeit aus 3 Gruppen) | 77 % | 100 % | 1,9 | 76 % | 0,2 | 4,7 / 4,4 | 63 % | 2,0 | 57 % |
| F: Förderung 2-0-0 | 78 % | 100 % | 1,8 | 78 % | 0,2 | 4,7 / 4,4 | 60 % | 1,6 | 69 % |
| I: Wohnbau erst ab der Runde nach der Gründung | 74 % | 100 % | 1,6 | 62 % | 0,1 | 3,1 / 6,2 | 45 % | 2,2 | 61 % |
| **M: Empfehlung** (Förderung 1-1-0) | **79 %** | **100 %** | **1,8** | **75 %** | **0,2** | **4,4 / 4,7** | **64 %** | **1,7** | **70 %** |
| H: Plan B, Genossenschaft muss gegründet werden | 80 % | 92 % | 0,6 | 64 % | 0,1 | 1,0 / 5,4 | 13 % | 1,5 | 100 % |
| **N: Empfehlung Plan B** (Genossenschaft besteht schon, 1-1-0, 2 Haushalte) | **82 %** | – | **1,0** | **71 %** | **0,2** | **2,0 / 4,3** | **50 %** | **1,6** | **100 %** |

- **Die Gründung kommt rechnerisch immer in Runde 1 zustande**, selbst mit 4 Kümmerzeit aus 3 Gruppen. Kümmerzeit ist zu Beginn reichlich da. Die eigentliche Hürde am Tisch ist die Einigung, und die bildet die Simulation nicht ab. Die Standard-Hürde (3 aus 2 Gruppen) bleibt, damit das Ereignis „Gründungsprüfung“ Biss hat: Es sperrt in etwa jeder achten Partie eine Runde lang den Wohnbau.
- **Die Genossenschaft stabilisiert die Wohnprojekte.** Die gemeinsame Kasse wirkt als Puffer: Statt 0,5 werden nur noch 0,2 Wohnprojekte je Partie umgedreht. Dafür ziehen etwas weniger Haushalte ein, weil Wohnen an die Gründung gebunden ist.
- **Der Tiny-House-Wunsch wird anspruchsvoller** (89 % → 64 %): Er ist nur noch über die Mitgliedschaft erfüllbar. Das ist gewollt.
- **Förderung 1-1-0 löst das Geldproblem aus Lauf 3.** Am Ende bleiben 1,7 statt 3,0 Mittel pro Person übrig, „Hälfte grün/offen“ gelingt in 70 % statt 45 % der Partien, die Gewinnquote steigt auf 79 %. 2-0-0 wirkt ähnlich.
- **Wohnbau erst ab der Folgerunde kostet zu viel** (Belegung 35 %, Tiny-Wunsch 45 %) und wird nicht übernommen.
- **Plan B braucht eine schon bestehende Genossenschaft.** Muss sie erst gegründet werden, entsteht kaum Wohnen (0,6 Projekte, Tiny-Wunsch 13 %).
- **„Kein Chip übrig“ wird zu leicht** (98–99 %), weil die Gründung Kümmerzeit bindet und Zuzug-Chips im Genossenschafts-Pool landen. Das Ziel muss neu gefasst werden.

## Lauf 5 – Flächenkonzepte, Bestand und Verdrängung (18.10.2026)

`lauf5_flaechen_bestand.py`, Ergebnisse in `lauf5_ergebnisse.json`. Baut auf Lauf 4 (Empfehlung M) auf. Neu: Wohnwiesen mit einzelnen Häuschen statt fester Wohnkarte, eine Fläche für Mobiles Wohnen (Probewohnen), eine frei gewählte Gemeinschaftsfläche mit Gemeinschaftskarten ab Schwellen, Bestand auf dem Plan (Gemeinschaftsgarten, Pavillon, Bienenstand, Trampelpfad, Kartoffelacker auf Probe), Störungen (Parkplatz, Garten, Pavillon) und die neuen Ziele „Drei Grünorte gepflegt“ und „Kein gewachsener Ort verloren“ statt „Hälfte grün/offen“. Neue Fläche: Wiese an der Turnhalle (TG 1.2, 4 Punkte, geschätzt). Je 1.500 Partien, 8 Personen, wenn nicht anders angegeben. Einzelne Szenarien lassen sich mit `python3 lauf5_flaechen_bestand.py L M` rechnen.

| Szenario | Gewinnquote | Haushalte (davon Häuschen) | Wohnwiesen | Schwelle 1 / 2 erreicht | Probewohnen geblieben / weitergezogen | verloren | Bestand verlagert | Acker verloren | Kassen-Schieflage | Tiny-Wunsch |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A: Basis (Schwellen 6/10, Erschließung laufend 2) | 73 % | 3,5 (3,5) | 3,5 | 21 % / 1 % | 0,1 / 3,7 | 2,5 | 0,6 | 73 % | 2,3 | 45 % |
| B: Schwellen 4/8 | 72 % | 3,6 (3,6) | 3,5 | 54 % / 6 % | 0,1 / 3,4 | 2,6 | 0,6 | 73 % | 2,2 | 47 % |
| C: ohne Mobiles Wohnen | 74 % | 3,3 (3,3) | 3,8 | 18 % / 0 % | – | 6,3 | 0,6 | 75 % | 2,6 | 40 % |
| D: Erschließung laufend 1 | 74 % | 3,6 (3,5) | 3,6 | 22 % / 1 % | 0,1 / 3,7 | 2,3 | 0,6 | 74 % | 0,6 | 45 % |
| F: ohne Bestand und Störungen | 83 % | 3,7 (3,7) | 3,9 | 24 % / 1 % | 0,1 / 2,3 | 3,5 | – | – | 2,4 | 37 % |
| H: neue Wohnwiese erst ab 3 Häuschen auf jeder bestehenden | 79 % | 0,7 (0,6) | 1,0 | 1 % / 0 % | 0,0 / 5,7 | 3,2 | 0,6 | 59 % | 0,6 | 23 % |
| I: nach Probewohnen bleiben, wenn irgendwo Platz frei | 72 % | 4,6 (4,5) | 3,6 | 44 % / 4 % | 1,4 / 2,5 | 2,4 | 0,6 | 75 % | 2,1 | 43 % |
| **L: Empfehlung** (I + Schwellen 4/8 + Erschließung laufend 1) | **74 %** | **5,1 (4,4)** | **3,5** | **76 % / 24 %** | **1,7 / 1,9** | **2,6** | **0,6** | **71 %** | **0,5** | **44 %** |
| **M: Empfehlung Plan B** (Genossenschaft besteht, 2 Haushalte) | **54 %** | **2,9 (2,7)** | **2,4** | **43 % / 0 %** | **0,8 / 0,9** | **2,6** | **0,4** | **83 %** | **0,5** | **24 %** |

- **Probewohnen ist ohne Bleibe-Erleichterung eine Drehtür.** Wer nach einer Runde dieselbe Bedingung erfüllen muss wie ein Neuzuzug, zieht fast immer weiter (0,1 von 3,7). Darf man bleiben, sobald irgendwo ein fester Platz frei ist, wird jeder zweite Probehaushalt sesshaft. Ohne Mobiles Wohnen gehen dagegen 6,3 statt 2,5 Haushalte verloren.
- **Die Schwellen 6/10 sind in drei Runden zu hoch.** Mit 4/8 und günstigerer Erschließung erreicht die Genossenschaft in drei Vierteln der Partien die erste Schwelle; Lastenradstation (46 %) und Gemeinschaftshaus (17 %) werden gebaut. Die Sauna kommt nie zustande: zu teuer für drei Runden.
- **Erschließung als Fixkosten wirkt, aber anders als gedacht.** Die simulierten Spieler erschließen fast jede freie Baufläche (3,5 Wohnwiesen für 4–5 Häuschen) und bringen die Kasse bei laufenden Kosten 2 in Schieflage. Eine harte Regel „erst verdichten“ (H) würgt das Wohnen ganz ab. Mit laufenden Kosten 1 bleibt es tragbar; das Zusammenrücken muss am Tisch ausgehandelt werden.
- **Die Wiese an der Turnhalle wird von selbst zum Ort fürs Mobile Wohnen** (in drei Vierteln der Partien), weil die Parkplatz-Störung dauerhaftes Wohnen dort ausbremst. Ohne Bestand und Störungen (F) wird TG 1.2 genauso oft Wohnwiese wie die anderen Flächen.
- **Verdrängt wird in der Simulation nie, verlagert gut einmal in zwei Partien** – meist Pavillon und Bienenstand auf TG 3. Die simulierten Spieler weichen der Verdrängung aus, solange Verlagern möglich ist. Ob Menschen das auch tun, ist eine der spannendsten Fragen für den Testlauf.
- **Der Kartoffelacker auf Probe geht in rund drei Vierteln der Partien verloren**, weil ihn in Runde 1 niemand übernimmt. Deshalb ist „Kein gewachsener Ort verloren“ über alle Partien nur in gut einem Viertel erfüllt. Ist es eines der gezogenen Ziele und arbeiten die Spieler darauf hin, gelingt es in rund zwei Dritteln.
- **Die Störungen am Garten und am Pavillon werden fast immer per Patenschaft behoben** (über 90 %), die am Parkplatz nicht, weil dafür ein Grün-Puffer auf TG 1.2 nötig wäre.
- **Die Gemeinschaftsfläche landet meist in einem Gebäude** (Garagen, Christophorushaus, Grünstraße 36, Turnhalle), fast nie auf TG 3, weil dort der Bestand Platz belegt.
- **Plan B wird schwierig** (54 %): „Kein gewachsener Ort verloren“ und „Jede Gruppe gelegt“ scheitern häufig. Für Plan B sollten diese beiden Ziele nicht im Stapel sein.
