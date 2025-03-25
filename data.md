# Håndboldhændelser Database - Dokumentation

Denne dokumentation giver en detaljeret gennemgang af databasestrukturen, hændelsestyper og spillertilknytninger i håndboldhændelserne-projektet.

## Indholdsfortegnelse
1. [Database Struktur](#database-struktur)
2. [Hændelsestyper](#hændelsestyper)
3. [Positionsangivelser](#positionsangivelser)
4. [Spillertilknytning](#spillertilknytning)
5. [Holdkoder og Holdnavne](#holdkoder-og-holdnavne)
6. [Særlige Værdier og Kanttilfælde](#særlige-værdier-og-kanttilfælde)
7. [Tips til Databehandling](#tips-til-databehandling)

## Database Struktur

Hver .db-fil repræsenterer én håndboldkamp og indeholder to primære tabeller: `match_info` og `match_events`.

Kvindeligaens db filer ligger her: "C:\Users\jonas\Desktop\Handball-ML\Kvindeliga-database\2024-2025"
Herreligaens db filer ligger her: "C:\Users\jonas\Desktop\Handball-ML\Herreliga-database\2024-2025"

### match_info Tabel

Indeholder overordnet information om kampen:

| Felt | Type | Beskrivelse |
|------|------|-------------|
| kamp_id | TEXT | Kampens unikke ID-nummer (f.eks. "748182") |
| hold_hjemme | TEXT | Navnet på hjemmeholdet (f.eks. "Ringkøbing Håndbold") |
| hold_ude | TEXT | Navnet på udeholdet (f.eks. "Nykøbing F. Håndbold") |
| resultat | TEXT | Slutresultatet (f.eks. "30-32") |
| halvleg_resultat | TEXT | Resultatet ved halvleg (f.eks. "17-16") |
| dato | TEXT | Kampens dato (f.eks. "4-9-2024") |
| sted | TEXT | Spillestedet (f.eks. "Green Sports Arena - Hal 1") |
| turnering | TEXT | Turneringens navn (f.eks. "Kvindeligaen", "Herreligaen") |

### match_events Tabel

Indeholder detaljerede hændelser fra kampen:

| Felt | Type | Beskrivelse |
|------|------|-------------|
| id | INTEGER | Unik hændelses-ID (autoincrement) |
| kamp_id | TEXT | Fremmednøgle til match_info |
| tid | TEXT | Tidspunktet i kampen (f.eks. "0.39", "21.12") |
| maal | TEXT | Målstillingen, hvis der scores (f.eks. "1-0", "13-12") - ellers null |
| hold | TEXT | Holdkoden for holdet involveret i hændelsen (f.eks. "RIN", "NFH") |
| haendelse_1 | TEXT | Den primære hændelse (f.eks. "Mål", "Skud reddet") |
| pos | TEXT | Positionen hvorfra hændelsen skete (f.eks. "ST", "VF", "Gbr") |
| nr_1 | INTEGER | Spillernummeret for spilleren involveret i den primære hændelse |
| navn_1 | TEXT | Navnet på spilleren involveret i den primære hændelse |
| haendelse_2 | TEXT | Den sekundære hændelse, hvis relevant (f.eks. "Assist", "Bold erobret") |
| nr_2 | INTEGER | Spillernummeret for spilleren involveret i den sekundære hændelse |
| navn_2 | TEXT | Navnet på spilleren involveret i den sekundære hændelse |
| nr_mv | INTEGER | Målvogterens spillernummer, hvis en målvogter er involveret |
| mv | TEXT | Målvogterens navn, hvis en målvogter er involveret |

## Hændelsestyper

### Primære Hændelser (haendelse_1)

Her er de mest almindelige primære hændelser og deres betydning:

| Hændelse | Beskrivelse | Typisk involverer målvogter? |
|----------|-------------|------------------------------|
| Mål | En spiller har scoret et mål | Ja |
| Skud reddet | Et skudforsøg er blevet reddet af målvogteren | Ja |
| Fejlaflevering | En spiller har lavet en forkert aflevering | Nej |
| Tilkendt straffe | Et hold er blevet tildelt et straffekast | Nej |
| Regelfejl | En spiller har begået en teknisk fejl | Nej |
| Mål på straffe | Et straffekast er blevet scoret | Ja |
| Skud forbi | Et skud er gået forbi målet | Ja |
| Time out | Et hold har taget timeout | Nej |
| Udvisning | En spiller er blevet udvist i 2 minutter | Nej |
| Skud på stolpe | Et skud har ramt stolpen | Ja |
| Skud blokeret | Et skud er blevet blokeret af en modstander | Nej |
| Tabt bold | En spiller har tabt bolden | Nej |
| Advarsel | En spiller har fået en advarsel (gult kort) | Nej |
| Straffekast reddet | Et straffekast er blevet reddet | Ja |
| Start 2:e halvleg | Anden halvleg begynder | Nej |
| Halvleg | Første halvleg slutter | Nej |
| Start 1:e halvleg | Første halvleg begynder | Nej |
| Passivt spil | Et hold er blevet dømt for passivt spil | Nej |
| Straffekast på stolpe | Et straffekast har ramt stolpen | Ja |
| Fuld tid | Kampen er slut | Nej |
| Kamp slut | Kampen er slut (alternativ betegnelse) | Nej |
| Straffekast forbi | Et straffekast er gået forbi | Ja |
| Video Proof | Video gennemgang begynder | Nej |
| Video Proof slut | Video gennemgang slutter | Nej |
| Rødt kort, direkte | En spiller har fået direkte rødt kort | Nej |
| Rødt kort | En spiller har fået rødt kort | Nej |
| Blåt kort | En spiller har fået blåt kort | Nej |
| Protest | En officiel protest er registreret | Nej |
| Start | Kampstart (sjældent brugt) | Nej |
| Udvisning (2x) | En spiller har fået dobbelt udvisning | Nej |

### Sekundære Hændelser (haendelse_2)

De mest almindelige sekundære hændelser:

| Hændelse | Beskrivelse | Spillertilknytning |
|----------|-------------|-------------------|
| Assist | En spiller har assisteret et mål | Samme hold som primær hændelse |
| Forårs. str. | En spiller har forårsaget et straffekast | Modstanderholdet |
| Bold erobret | En spiller har erobret bolden | Typisk modstanderholdet |
| Retur | En spiller får returen efter et skud | Varierer |
| Blok af (ret) | En spiller har blokeret et skud | Modstanderholdet |
| Blokeret af | Et skud er blevet blokeret af en spiller | Modstanderholdet |

## Positionsangivelser

Forskellige positioner (pos) som spillerne agerer fra:

| Position | Beskrivelse |
|----------|-------------|
| Gbr | Gennembrud |
| PL | Playmaker |
| 2:e | Anden bølge kontra |
| ST | Streg |
| 1:e | Første bølge kontra |
| HF | Højre fløj |
| VF | Venstre fløj |
| VB | Venstre back |
| HB | Højre back |

## Spillertilknytning

At bestemme hvilket hold en spiller tilhører er komplekst og kræver forståelse af håndboldreglerne:

### Primære Hændelser (haendelse_1, nr_1, navn_1)

For primære hændelser tilhører spilleren det hold, der er angivet i "hold"-feltet.

```
Eksempel:
TID: 2.29, HOLD: EHA, HAENDELSE_1: Mål, NR_1: 10, NAVN_1: Sofie LASSEN
```
Her tilhører Sofie LASSEN holdet EHA.

### Sekundære Hændelser (haendelse_2, nr_2, navn_2)

For sekundære hændelser afhænger det af hændelsestypen:

1. **Samme Hold (SAME_TEAM_EVENTS)**: 
   - For "Assist" tilhører spilleren samme hold som angivet i "hold"-feltet.
   
   ```
   Eksempel:
   TID: 7.19, HOLD: RIN, HAENDELSE_1: Mål, HAENDELSE_2: Assist, NR_2: 3, NAVN_2: Maria Berger WIERZBA
   ```
   Her er Maria Berger WIERZBA på samme hold som den primære spiller (RIN).

2. **Modstanderhold (OPPOSITE_TEAM_EVENTS)**:
   - For "Bold erobret", "Forårs. str.", "Blokeret af", "Blok af (ret)" tilhører spilleren det modsatte hold af det angivet i "hold"-feltet.
   
   ```
   Eksempel:
   TID: 12.36, HOLD: NFH, HAENDELSE_1: Fejlaflevering, NR_1: 7, NAVN_1: Amalie WULFF, HAENDELSE_2: Bold erobret, NR_2: 3, NAVN_2: Maria Berger WIERZBA
   ```
   Her er Maria Berger WIERZBA IKKE på NFH-holdet, men på modstanderholdet.

### Målvogtere (nr_mv, mv)

For målvogtere gælder:

- Målvogteren tilhører ALTID det modsatte hold af det, der er angivet i "hold"-feltet ved mål-relaterede hændelser som "Mål", "Skud reddet", osv.
- Dette fordi "hold"-feltet refererer til det skydende hold, ikke målvogterens hold.

```
Eksempel:
TID: 0.39, HOLD: RIN, HAENDELSE_1: Mål, NR_MV: 1, MV: Sofie BÖRJESSON
```
Her er Sofie BÖRJESSON IKKE på RIN-holdet, men på modstanderholdet.

## Holdkoder og Holdnavne

Hver holdkode repræsenterer et bestemt hold. Her er de mest almindelige holdkoder:

### Kvindeligaen
- AHB: Aarhus Håndbold Kvinder
- BFH: Bjerringbro FH
- EHA: EH Aalborg
- HHE: Horsens Håndbold Elite
- IKA: Ikast Håndbold
- KBH: København Håndbold
- NFH: Nykøbing F. Håndbold
- ODE: Odense Håndbold
- RIN: Ringkøbing Håndbold
- SVK: Silkeborg-Voel KFUM
- SKB: Skanderborg Håndbold
- SJE: SønderjyskE Kvindehåndbold
- TES: Team Esbjerg
- VHK: Viborg HK
- TMS: TMS Ringsted

### Herreligaen
- AAH: Aalborg Håndbold
- BSH: Bjerringbro-Silkeborg
- FHK: Fredericia Håndbold Klub
- GIF: Grindsted GIF Håndbold
- GOG: GOG
- KIF: KIF Kolding
- MTH: Mors-Thy Håndbold
- NSH: Nordsjælland Håndbold
- REH: Ribe-Esbjerg HH
- SAH: SAH - Skanderborg AGF
- SKH: Skjern Håndbold
- SJE: SønderjyskE Herrehåndbold
- TTH: TTH Holstebro

## Særlige Værdier og Kanttilfælde

Under databehandlingen bør man være opmærksom på følgende:

1. **Ikke-spillernavne**: Værdier som "Retur", "Bold erobret", "Assist" osv. er ikke spillernavne, selvom de kan optræde i navn-felter.

2. **Start/slut værdier**: "Start 1:e halvleg", "Halvleg", "Start 2:e halvleg", "Fuld tid", "Kamp slut", "Video Proof", "Video Proof slut" er administrative hændelser og ikke direkte spil-relaterede.

3. **Tomme felter**: Ikke alle felter er altid udfyldt. F.eks. kan "hold" være null for administrative hændelser.

4. **Numeriske værdier som strenge**: Nogle numeriske værdier (som "nr_1", "nr_2", "nr_mv") kan være gemt som strenge, og værdien "0" skal tolkes som null.

5. **Målvogteridentifikation**: Ved hændelser som "Mål", "Skud reddet" osv. er de sidste to felter (nr_mv, mv) typisk målvogteren, som tilhører det modsatte hold.

6. **Spillere med samme nummer**: Der kan være flere spillere med samme nummer på samme hold, især hvis databasen dækker flere kampe/sæsoner.

7. **Sjældne hændelser**: Hændelser som "Blåt kort", "Rødt kort", "Protest" er relativt sjældne og forekommer kun i få kampe.

## Tips til Databehandling

1. **Hold-identifikation**: Ved analyse af spillerdata, vær opmærksom på de forskellige regler for at bestemme hvilken spiller der tilhører hvilket hold.

2. **Målvogtere**: Husk at målvogtere (nr_mv, mv) altid tilhører det modsatte hold af det angivet i "hold"-feltet.

3. **Håndtering af sekundære hændelser**: Vær opmærksom på om secondary events (haendelse_2) indikerer en spiller fra samme hold eller modstanderholdet.

4. **Kronologisk rækkefølge**: Hændelser er gemt i kronologisk rækkefølge baseret på "tid"-feltet, hvilket gør det muligt at rekonstruere kampforløbet.

5. **Scoreudvikling**: "maal"-feltet viser målstillingen ved hændelsen, hvilket gør det muligt at følge scoreudviklingen gennem kampen.

6. **Validering**: Ved databehandling bør man validere at hold-koder (i "hold"-feltet) stemmer overens med de faktiske holdnavne i "match_info"-tabellen.

7. **Filtrering**: For at fokusere på spillerstatistik, kan det være nyttigt at filtrere administrative hændelser væk, f.eks. "Halvleg", "Start 1:e halvleg" osv.

Ved at følge disse retningslinjer kan man effektivt analysere håndboldhændelserne og udtrække værdifuld statistik om kampe, hold og spillere.