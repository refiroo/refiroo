# Samples

The guide's own sample data: the reference domain, the public transport stops of the canton of
Graubünden, from open data, plus one fictional system and one fictional workbook. Not published. Never
put a private model or a source export here. The sources, licences and attribution lines are in
[`SOURCES.md`](SOURCES.md); the data is a dated snapshot (2026-11-02).

| Path | What it is |
| --- | --- |
| `model.json` | The model release `guide-reference-swiss`: three applications, Network (canton > district > municipality > stop, operators, modes), Systems (code mappings) and Names (translations by language), and the `stops` consumer API |
| `data/docs/` | The docs set, 598 records: the 116 stops a train serves, with their 44 municipalities, 10 districts, the canton, 3 operators, 15 modes, 5 languages, 231 name translations and 170 system codes. The `docs` test group and the tutorials use it |
| `data/reference/` | The reference set, 3,528 records: all 2,443 current stops of Graubünden with 100 municipalities, 71 operators and the rest, plus an open change set. The reference instance uses it |
| `fetch.py` | Downloads a fresh snapshot (into `snapshot/`, git-ignored) and rewrites both sets in `data/` |
| `load.py` | Loads a set through the public API |
| `Haltestellen_Busbetrieb_Nord.xlsx`, `make_workbook.py` | The fictional bus company's messy stop list (not loaded by `load.py`) and its generator |
| `_correspondence/` | The e-mail to the publisher about the dated snapshot (drafted, not sent) |

## Load a set

The instance needs its first administrator (docs/OPERATIONS.md, Deploying) and
`MODEL_ADMIN_MUTATIONS_ENABLED=true`, because the model is installed through the API. Then:

```bash
python3 guide/samples/load.py --set docs --base http://<your-instance> --env path/to/env-file
```

`--set` is `docs` or `reference`. The env file holds `GUIDE_ADMIN_USERNAME` and `GUIDE_ADMIN_PASSWORD`
(or set them in the environment). The script signs in as that administrator, installs the model release,
makes the workspace `graubuenden` (the default one), and loads the set in background batches. It
changes nothing on a second run. The reference set takes about 20 seconds. `--skip-changeset` leaves out
the open change set; `--client NAME` also makes an API client holding the `stops` consumer API.

`guide/reference/reference.sh up` starts the reference instance in Docker and runs this command.
The `docs` test group loads the docs set the same way (`load_set` in `load.py`) into its seed.
