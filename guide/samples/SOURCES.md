# Sources of the sample data

The guide's reference domain is the public transport stops of the canton of Graubünden (Switzerland).
Every copy of this data (the files in `data/`, the pages that quote it, a screenshot, a loaded
instance) carries the attribution lines below. The data is a dated snapshot, **2026-11-02**, not kept
current; `fetch.py` downloads the current data again.

## Real data

| Data | Source | Licence and attribution |
| --- | --- | --- |
| Stops (Didok service points), operators, means of transport, canton, districts and municipalities (names and FSO numbers) | opentransportdata.swiss, Service Points (Didok), Federal Office of Transport / SBB. Read through https://data.sbb.ch (Explore API, dataset `dienststellen-gemass-opentransportdataswiss`); original at https://opentransportdata.swiss | Terms of use: https://opentransportdata.swiss/en/terms-of-use/ (name the source; processing and publishing allowed). Attribution line: **Source: opentransportdata.swiss, Service Points (Didok), Federal Office of Transport / SBB, snapshot 2026-11-02** |
| Names of the municipalities and the canton in German, French, Italian, Romansh and English; the item numbers (Q-ids) of the municipalities and of the stations | Wikidata, https://www.wikidata.org (municipalities by property P771, stations by P722) | CC0, https://www.wikidata.org/wiki/Wikidata:Licensing . Attribution line: **Wikidata, CC0** |

The publisher's terms ask that data be updated at the same frequency as the raw data. Whether a dated
snapshot used only as example data meets that clause is asked in
`_correspondence/email-opentransportdata-en.md` (German: `-de.md`). The e-mail is drafted, not sent. Until the
publisher answers, the repository ships the snapshot's two derived data sets and the script that downloads current
data; the downloaded raw files are not kept in the repository (`snapshot/` is git-ignored).

## Fictional data

Labelled fictional wherever it appears. Real stop names and numbers are used so a result can be checked;
nothing else is real.

- The ticketing system **"Regional ticketing (FICTIONAL)"** and all its codes (`T-0412` and the others
  in `fetch.py`). One code is left unmapped on purpose (`T-9999`) and one points at two stops
  (`T-0300`), to show unmapped and ambiguous codes.
- The workbook `Haltestellen_Busbetrieb_Nord.xlsx` of a fictional bus company (lines, platforms, local
  codes, fare zones), written by `make_workbook.py`.

## What was left out

GTFS route types: their licence statement was not verified, so no GTFS system, code or mapping is in
the model or the data.

## Conversions

Didok's `validto` is the last valid day and `9999-12-31` means open; refiroo's period end is exclusive
and may be empty, so the load writes no end for `9999-12-31` and adds one day to real ends. Many
`validfrom` values of 2021-04-01 are the register's re-versioning, not an opening.
