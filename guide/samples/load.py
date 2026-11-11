"""Load a Graubuenden data set of the guide through the engine's public API only, as an integrator would.

    python3 load.py --set docs|reference [--base http://localhost:8480] [--env FILE]
                    [--skip-changeset] [--client NAME]

The first administrator must exist (docs/OPERATIONS.md, Deploying; guide/reference/README.md). The
engine must allow model changes through the API (MODEL_ADMIN_MUTATIONS_ENABLED=true). This script:
  1. signs the administrator in (authorization code flow with PKCE, as the browser does);
  2. installs the model release from model.json and runs it in a new workspace "Graubuenden"
     (made the default, so the application opens on it);
  3. loads the set with background batches (upserts with stable IDs, so a second run changes
     nothing): canton, districts, municipalities, operators, modes, languages, systems, stops, their
     relationships, system codes and mappings, name translations;
  4. when the set has one: opens the change set "December 2026 timetable change" and leaves it
     unpublished (--skip-changeset leaves it out);
  5. with --client NAME: makes a client holding the `stops` consumer API in the workspace and keeps
     its credentials in the env file (GUIDE_CONSUMER_CLIENT_ID / _SECRET).
The administrator's name and password come from the env file (GUIDE_ADMIN_EMAIL,
GUIDE_ADMIN_PASSWORD) or the environment. The set is `docs` (about 600 records, what the guide's
examples run on) or `reference` (about 3,500 records, the reference instance).
Standard library only. Another program, such as the docs test group, can use `Api` with its own
`send` and call `load_set`.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import secrets
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
WORKSPACE = "graubuenden"
LABEL = "Graubünden"
RELEASE_KEY = "guide-reference-swiss"
APP_NETWORK, APP_SYSTEMS, APP_NAMES = "network", "systems", "names"
CHANGE_SET_NAME = "December 2026 timetable change"

# send(method, path, body, headers, form) -> (status, parsed body)
Send = Callable[..., tuple[int, object]]


def read_env(path: Path) -> dict[str, str]:
    out = {}
    for line in path.read_text().splitlines():
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip()
    return out


def urllib_send(base: str) -> Send:
    """Send requests to a running instance over HTTP."""
    base = base.rstrip("/")

    def send(method, path, body=None, headers=None, form=None):
        data, hdrs = None, {"Accept": "application/json", "Origin": base}
        if body is not None:
            data, hdrs["Content-Type"] = json.dumps(body).encode(), "application/json"
        if form is not None:
            data, hdrs["Content-Type"] = (
                urllib.parse.urlencode(form).encode(),
                "application/x-www-form-urlencoded",
            )
        hdrs.update(headers or {})
        req = urllib.request.Request(base + path, data=data, method=method, headers=hdrs)
        try:
            with urllib.request.urlopen(req, timeout=600) as r:
                text = r.read().decode()
                return r.status, (json.loads(text) if text else None)
        except urllib.error.HTTPError as e:
            text = e.read().decode()
            try:
                return e.code, json.loads(text)
            except ValueError:
                return e.code, {"raw": text}

    return send


class Api:
    """The management API. `send` carries the requests (HTTP by default); without an e-mail address the
    caller has its own credentials (the docs test group's client) and no sign-in happens."""

    def __init__(
        self,
        send: Send,
        base: str = "",
        email: str = "",
        password: str = "",
        log: Callable[[str], None] = lambda text: print(text, flush=True),
    ):
        self.send, self.base = send, base.rstrip("/")
        self.email, self.password = email, password
        self.token = ""
        self.requests = 0
        self.log = log

    def raw(self, method, path, body=None, headers=None, form=None, auth=True):
        self.requests += 1
        hdrs = dict(headers or {})
        if auth and self.token:
            hdrs["Authorization"] = "Bearer " + self.token
        return self.send(method, path, body, hdrs, form)

    def call(self, method, path, body=None, ok=(200, 201, 202, 204), headers=None):
        status, out = self.raw(method, path, body, headers)
        if status == 401 and self.email:  # the one-hour token ran out: sign in again
            self.login()
            status, out = self.raw(method, path, body, headers)
        if status not in ok:
            raise SystemExit(f"{method} {path} -> {status}: {json.dumps(out)[:1500]}")
        return out

    def login(self):
        verifier = secrets.token_urlsafe(48)
        challenge = (
            base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest())
            .rstrip(b"=")
            .decode()
        )
        redirect = self.base + "/signed-in"
        request = {
            "response_type": "code",
            "client_id": "browser",
            "redirect_uri": redirect,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
            "state": secrets.token_urlsafe(16),
        }
        status, out = self.raw(
            "POST",
            "/oauth/sign-in/password",
            {"request": request, "email": self.email, "password": self.password},
            auth=False,
        )
        if status != 200 or out.get("status") != "signed_in":
            raise SystemExit(f"sign-in failed: {status} {out}")
        code = urllib.parse.parse_qs(urllib.parse.urlparse(out["redirect"]).query)["code"][0]
        status, tok = self.raw(
            "POST",
            "/oauth/token",
            form={
                "grant_type": "authorization_code",
                "client_id": "browser",
                "code": code,
                "code_verifier": verifier,
                "redirect_uri": redirect,
            },
            auth=False,
        )
        if status != 200:
            raise SystemExit(f"token exchange failed: {status} {tok}")
        self.token = tok["access_token"]

    # -- helpers
    def wait_job(self, job_id, label):
        last = -1
        while True:
            job = self.call("GET", f"/api/v1/jobs/{job_id}")
            if job["state"] in ("completed", "failed", "cancelled"):
                return job
            done = job["progress"]["processed"]
            if done != last:
                self.log(f"    {label}: {done}/{job['progress']['total']}")
                last = done
            time.sleep(1)

    def batch(self, label, items, context, key=None, on_existing="reject"):
        """Run items as one background batch (independent policy) and stop on the first rejection."""
        body = {
            **context,
            "policy": "independent",
            "run": "background",
            "onExisting": on_existing,
            "items": items,
        }
        headers = {"Idempotency-Key": key} if key else None
        job = self.call("POST", "/api/v1/batches", body, headers=headers)
        job = (
            self.wait_job(job["id"], label) if job["state"] not in ("completed", "failed") else job
        )
        counts = job.get("counts", {})
        if job["state"] != "completed" or counts.get("rejected") or counts.get("unprocessed"):
            bad = self.call("GET", f"/api/v1/jobs/{job['id']}/items?status=rejected&pageSize=5")
            raise SystemExit(
                f"{label}: job {job['state']} counts={counts} error={job.get('error')} "
                f"first rejections={json.dumps(bad.get('items'))[:2000]}"
            )
        self.log(
            f"  {label}: {counts.get('created', 0)} created, {counts.get('updated', 0)} updated, "
            f"{counts.get('unchanged', 0)} unchanged"
        )
        return job


def attrs(**kv):
    return [
        {"attributeTypeKey": k.replace("_", "-"), "value": v}
        for k, v in kv.items()
        if v is not None
    ]


def ref(i):
    return {"id": i}


def upsert(app, otype, rec, name, attributes, parent=None):
    item = {
        "op": "upsert",
        "applicationKey": app,
        "objectTypeKey": otype,
        "key": {"id": rec},
        "name": name,
        "attributes": attributes,
    }
    if parent:
        item["parent"] = ref(parent)
    return item


def ensure_rel(rtype, a, b):
    return {
        "op": "ensureRelation",
        "relationTypeKey": rtype,
        "from": ref(a),
        "to": ref(b),
    }


def load_set(
    api: Api,
    set_name: str,
    *,
    changeset: bool = True,
    client_name: str | None = None,
    env_file: Path | None = None,
) -> None:
    """Install the model, make the workspace and load the set, through `api`."""
    print = api.log  # progress lines go where the caller wants them
    t0 = time.time()
    d = {p.stem: json.loads(p.read_text()) for p in (DATA / set_name).glob("*.json")}

    if api.email:
        print("1. sign in")
        api.login()

    print("2. model release")
    model = json.loads((HERE / "model.json").read_text())
    existing = api.call("GET", f"/api/v1/model-releases?releaseKey={RELEASE_KEY}&pageSize=50")[
        "items"
    ]
    release = next((r for r in existing if r["version"] == model["release"]["version"]), None)
    if not release:
        draft = api.call(
            "POST",
            "/api/v1/model-drafts",
            {"name": model["release"]["name"], "model": model},
        )
        release = api.call(
            "POST",
            f"/api/v1/model-drafts/{draft['id']}/installation",
            {"expectedVersion": draft["version"]},
        )
    print(f"  release {release['key']} {release['version']} ({release['id']})")

    print("3. workspace")
    status, ws = api.raw("GET", f"/api/v1/workspaces/{WORKSPACE}")
    if status == 404:
        ws = api.call(
            "POST",
            "/api/v1/workspaces",
            {"key": WORKSPACE, "label": LABEL, "modelReleaseId": release["id"]},
        )
    if ws["model"]["releaseId"] != release["id"]:  # an earlier release of this model: move on
        ws["model"] = api.call(
            "POST",
            f"/api/v1/workspaces/{WORKSPACE}/model/activation",
            {
                "releaseId": release["id"],
                "expectedVersion": ws["model"]["version"],
                "expectedReleaseId": ws["model"]["releaseId"],
            },
        )
    print(
        f"  workspace {ws['key']} runs {ws['model']['releaseKey']} {ws['model']['releaseVersion']}"
    )
    state = api.call("GET", "/api/v1/workspace-runtime-state")
    if state.get("defaultWorkspaceKey") != WORKSPACE:
        api.call(
            "PATCH",
            "/api/v1/workspace-runtime-state",
            {"defaultWorkspaceKey": WORKSPACE, "expectedVersion": state["version"]},
        )
    ctx = {"workspaceKey": WORKSPACE}

    print(f"4. {set_name} set")
    c = d["canton"]
    items = [
        upsert(
            APP_NETWORK,
            "canton",
            c["id"],
            c["name"],
            attrs(canton_abbreviation=c["abbreviation"], fso_number=c["fso"]),
        )
    ]
    items += [
        upsert(
            APP_NETWORK,
            "district",
            x["id"],
            x["name"],
            attrs(fso_number=x["fso"]),
            x["parent"],
        )
        for x in d["districts"]
    ]
    items += [
        upsert(
            APP_NETWORK,
            "municipality",
            x["id"],
            x["name"],
            attrs(fso_number=x["fso"]),
            x["parent"],
        )
        for x in d["municipalities"]
    ]
    items += [
        upsert(
            APP_NETWORK,
            "operator",
            x["id"],
            x["name"],
            attrs(operator_code=x["code"], operator_sboid=x["sboid"]),
        )
        for x in d["operators"]
    ]
    # groups first, then their members (a child needs its parent)
    for m in sorted(d["modes"], key=lambda m: m["parent"] is not None):
        items.append(
            upsert(
                APP_NETWORK,
                "mode",
                m["id"],
                m["name"],
                attrs(mode_code=m["code"]),
                m["parent"],
            )
        )
    items += [
        upsert(
            APP_NAMES,
            "language",
            x["id"],
            x["name"],
            attrs(language_code=x["code"], active=True),
        )
        for x in d["languages"]
    ]
    items += [
        upsert(
            APP_SYSTEMS,
            "system",
            x["id"],
            x["name"],
            attrs(system_key=x["key"], description=x["description"]),
        )
        for x in d["systems"]
    ]
    api.batch(
        "geography, operators, modes, languages, systems", items, ctx, f"gr-{set_name}-1-base"
    )

    items = [
        upsert(
            APP_NETWORK,
            "stop",
            s["id"],
            s["name"],
            attrs(
                designation=s["name"],
                stop_number=s["number"],
                sloid=s["sloid"],
                abbreviation=s["abbreviation"],
                latitude=s["lat"],
                longitude=s["lon"],
                height=s["height"],
                valid_from=s["validFrom"],
                valid_to=s["validTo"],
            ),
            s["parent"],
        )
        for s in d["stops"]
    ]
    api.batch("stops", items, ctx, f"gr-{set_name}-2-stops")

    items = []
    for s in d["stops"]:
        if s["operator"]:
            items.append(ensure_rel("stop-operated-by-operator", s["id"], s["operator"]))
        items += [ensure_rel("stop-served-by-mode", s["id"], m) for m in s["modes"]]
    api.batch("stop operators and modes", items, ctx, f"gr-{set_name}-3-stop-rels")

    items = [
        upsert(
            APP_SYSTEMS,
            "system-code",
            x["id"],
            x["name"],
            attrs(external_id=x["code"]),
            x["system"],
        )
        for x in d["codes"]
    ]
    api.batch("system codes", items, ctx, f"gr-{set_name}-4-codes")
    items = [
        ensure_rel("system-code-maps-to", x["id"], t) for x in d["codes"] for t in x["targets"]
    ]
    api.batch("code mappings", items, ctx, f"gr-{set_name}-5-mappings")

    # Values of the relationships (0.13 RV): the set may carry some; overwrite makes a rerun safe.
    values = d.get("relation-values", {})
    items = [
        {
            **ensure_rel("stop-operated-by-operator", x["stop"], x["operator"]),
            "attributes": x["values"],
        }
        for x in values.get("operatorLinks", [])
    ] + [
        {
            **ensure_rel("system-code-maps-to", x["code"], x["municipality"]),
            "attributes": x["values"],
        }
        for x in values.get("codeLinks", [])
    ]
    if items:
        # The key follows the values, so an edited file is applied, not replayed.
        digest = hashlib.sha1(json.dumps(items, sort_keys=True).encode()).hexdigest()[:8]
        api.batch(
            "relationship values",
            items,
            ctx,
            f"gr-{set_name}-5b-values-{digest}",
            on_existing="overwrite",
        )

    items = [
        {
            "op": "upsert",
            "applicationKey": APP_NAMES,
            "objectTypeKey": "name-translation",
            "key": {"id": t["id"]},
            "name": t["name"],
            "parent": ref(t["language"]),
            "attributes": attrs(translated_name=t["text"], active=True),
            "initialRelations": [
                {
                    "relationTypeKey": "object-has-translation",
                    "direction": "incoming",
                    "object": ref(t["object"]),
                }
            ],
        }
        for t in d["translations"]
    ]
    api.batch("name translations", items, ctx, f"gr-{set_name}-6-translations")
    print(f"  {set_name} set loaded in {time.time() - t0:.0f} s")

    cs_def = d["changeSet"]
    if changeset and cs_def["ends"]:
        print("5. open change set")
        sets = api.call("GET", f"/api/v1/workspaces/{WORKSPACE}/change-sets?pageSize=100")["items"]
        cs = next((x for x in sets if x["name"] == cs_def["name"]), None)
        if cs:
            print(
                f"  change set already exists ({cs['id']}); its content is applied again (unchanged items stay)"
            )
        else:
            cs = api.call(
                "POST",
                f"/api/v1/workspaces/{WORKSPACE}/change-sets",
                {"name": cs_def["name"], "source": "currentLive"},
            )
        if not cs_def["addIfMissing"]["present"]:
            raise SystemExit(
                "Chur West is missing from the stops: the change set would add it (not expected in this snapshot)"
            )
        items = [
            upsert(APP_NETWORK, "stop", e["stop"], e["name"], attrs(valid_to=e["validTo"]))
            for e in cs_def["ends"]
        ]
        api.batch(
            "change set: stops ended by the December timetable change",
            items,
            {"changeSetId": cs["id"], "expectedChangeSetVersion": cs["version"]},
            None,
            "overwrite",
        )
        print(
            f"  change set {cs['id']} left open; Chur West ({cs_def['addIfMissing']['number']}) is already in the register, not added"
        )

    if client_name:
        print("6. consumer client")
        env = read_env(env_file) if env_file else {}
        if "GUIDE_CONSUMER_CLIENT_ID" in env:
            print("  client already made (credentials in the env file)")
        else:
            found = [
                c
                for c in api.call("GET", "/api/v1/clients?q=" + urllib.parse.quote(client_name))[
                    "items"
                ]
                if c["name"] == client_name
            ]
            if (
                found
            ):  # made by an earlier run that stopped before keeping the secret: ask for a new one
                client = api.call(
                    "POST",
                    f"/api/v1/clients/{found[0]['id']}/secrets",
                    {"expectedVersion": found[0]["version"], "overlapHours": 0},
                )
            else:
                client = api.call("POST", "/api/v1/clients", {"name": client_name})
                api.call(
                    "POST",
                    "/api/v1/grants",
                    {
                        "principal": {"kind": "client", "id": client["id"]},
                        "consumerApi": "stops",
                        "scope": {"workspaceKey": WORKSPACE},
                    },
                )
            with open(env_file, "a") as f:
                f.write(
                    f"GUIDE_CONSUMER_CLIENT_ID={client['id']}\n"
                    f"GUIDE_CONSUMER_CLIENT_SECRET={client['secret']}\n"
                )
            print(
                f"  client {client['id']} holds the stops API in {WORKSPACE}; credentials appended to the env file"
            )

    print(f"done in {time.time() - t0:.0f} s, {api.requests} requests")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--set", required=True, choices=["docs", "reference"], dest="set_name")
    ap.add_argument("--base", default="http://localhost:8480")
    ap.add_argument("--env", type=Path, help="the env file with GUIDE_ADMIN_EMAIL and _PASSWORD")
    ap.add_argument("--skip-changeset", action="store_true")
    ap.add_argument(
        "--client", metavar="NAME", help="also make a client of this name holding the stops API"
    )
    a = ap.parse_args()
    env = (
        {**read_env(a.env), **{k: v for k, v in os.environ.items() if k.startswith("GUIDE_")}}
        if a.env
        else dict(os.environ)
    )
    try:
        email, password = env["GUIDE_ADMIN_EMAIL"], env["GUIDE_ADMIN_PASSWORD"]
    except KeyError as missing:
        raise SystemExit(f"{missing} is not set: give --env FILE or set it in the environment")
    if a.client and not a.env:
        raise SystemExit("--client keeps the client's credentials in the env file: give --env FILE")
    api = Api(urllib_send(a.base), a.base, email, password)
    load_set(api, a.set_name, changeset=not a.skip_changeset, client_name=a.client, env_file=a.env)
    return 0


if __name__ == "__main__":
    sys.exit(main())
