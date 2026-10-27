"""J08 — Create and activate an application-model release (USER_JOURNEYS.md).

J08.9 (a draft's history) is planned (D-5).
"""

import copy

import pytest
from scenario import W1, ok, refused

DISABLED = {"MODEL_ADMIN_MUTATIONS_ENABLED": "false"}


def _active(world):
    return world.workspace_model()


def _model_release(world):
    return world.api.get("/model").headers["X-Model-Release-Id"]


def _draft(world, model, name="Draft", base=None):
    body = {"name": name, "model": model, **({"baseReleaseId": base} if base else {})}
    return ok(world.api.post("/model-drafts", body), 201)


def _compile(world, draft):
    return ok(
        world.api.post(
            f"/model-drafts/{draft['id']}/compile", {"expectedVersion": draft["version"]}
        )
    )


def _install(world, draft):
    return world.api.post(
        f"/model-drafts/{draft['id']}/installation", {"expectedVersion": draft["version"]}
    )


def _broken(world):
    """The configuration's model with an application naming a type the model lacks."""
    model = copy.deepcopy(world.configuration.model)
    model["applications"][0]["objectTypeKeys"].append("no-such-type")
    model["release"]["version"] += "-broken"
    return model


@pytest.mark.journey("J08")
@pytest.mark.structures("R")
def test_draft_compile_install_and_activate_a_release(world):
    """Given M1 active. When a draft with a compatible addition is saved, changed, compiled, installed
    (twice) and activated against the runtime state. Then the draft is versioned and the releases are
    unchanged by saving; compiling is valid with its changes and compatible; installing answers the
    new inactive release, then the same release again, and the model still reads M1; activating
    answers the next runtime state and the model reads the new release. A stale draft, an unknown
    draft, an invalid model and a reused release identity are refused."""
    m1 = _active(world)
    releases = ok(world.api.get("/model-releases", assigned=True))["items"]
    assert [r["id"] for r in releases] == [m1["releaseId"]]
    model, added = world.candidate("compatible")
    draft = _draft(world, world.configuration.model, base=m1["releaseId"])
    patched = ok(
        world.api.patch(
            f"/model-drafts/{draft['id']}", {"expectedVersion": draft["version"], "model": model}
        )
    )
    assert patched["version"] == draft["version"] + 1
    assert (
        ok(world.api.get("/model-releases"))["items"]
        == ok(world.api.get("/model-releases"))["items"]
    )
    assert len(ok(world.api.get("/model-releases"))["items"]) == 1

    compiled = _compile(world, patched)
    assert compiled["valid"] is True and compiled["compatibility"]["classification"] == "compatible"
    assert any(c["kind"] == "added" and added in c["path"] for c in compiled["changes"])
    assert all({"kind", "path"} <= set(c) for c in compiled["changes"])
    release = ok(_install(world, patched), 201)
    assert release["assigned"] is False and _model_release(world) == m1["releaseId"]
    again = ok(_install(world, patched), 200)
    assert again["id"] == release["id"]

    activated = ok(world.activate(release["id"]))
    assert (
        activated["releaseId"] == release["id"] and activated["version"] == m1["version"] + 1
    )
    assert _model_release(world) == release["id"]

    refused(
        world.api.patch(
            f"/model-drafts/{draft['id']}", {"expectedVersion": draft["version"], "name": "Stale"}
        ),
        409,
        "VERSION_CONFLICT",
    )
    refused(
        world.api.get("/model-drafts/00000000-0000-4000-8000-000000000000"),
        404,
        "MODEL_DRAFT_NOT_FOUND",
    )
    error = refused(_install(world, _draft(world, _broken(world))), 422, "INVALID_MODEL")
    assert any(d["path"].startswith("/applications") for d in error["details"])
    reused = copy.deepcopy(model)
    reused["product"]["name"] = "Same identity, other content"
    refused(_install(world, _draft(world, reused)), 409, "RELEASE_IDENTITY_CONFLICT")


def _validate_without_saving(world):
    drafts = (
        ok(world.api.get("/model-drafts"))
        if world.api.get("/model-drafts").status_code == 200
        else None
    )
    releases = ok(world.api.get("/model-releases"))["items"]
    answer = ok(world.api.post("/model-validations", {"model": _broken(world)}))
    assert answer["valid"] is False
    (diagnostic,) = [
        d
        for d in answer["diagnostics"]
        if "no-such-type" in d["message"] or d["path"].startswith("/applications")
    ][:1]
    assert {"severity", "code", "path", "message"} <= set(diagnostic)
    assert diagnostic["path"].startswith("/applications/")
    assert ok(world.api.get("/model-releases"))["items"] == releases
    if drafts is not None:
        assert ok(world.api.get("/model-drafts"))["items"] == drafts["items"]


@pytest.mark.journey("J08.1")
@pytest.mark.structures("R")
def test_validate_a_model_without_saving_it(world):
    """When a model with a reference to a missing type is validated. Then it is invalid with a
    diagnostic naming its severity, code, JSON pointer and message, and nothing is saved."""
    _validate_without_saving(world)


@pytest.mark.journey("J08.1", "J08.7")
@pytest.mark.structures("R")
@pytest.mark.settings(**DISABLED)
def test_with_model_administration_disabled(world):
    """Given model administration disabled. When a model is validated and a release read. Then both
    answer as on any instance; every draft, install and activation route is absent, and the
    capabilities say so with the setting's name."""
    _validate_without_saving(world)
    release = _active(world)["releaseId"]
    assert "model" not in ok(world.api.get(f"/model-releases/{release}"))
    assert ok(world.api.get(f"/model-releases/{release}", includeModel=True))["model"]
    capabilities = ok(world.api.get("/capabilities"))["modelAdmin"]
    assert (capabilities["manageDrafts"], capabilities["install"], capabilities["activate"]) == (
        False,
        False,
        False,
    )
    assert capabilities["setting"] == "MODEL_ADMIN_MUTATIONS_ENABLED"
    body = {"releaseId": release, "expectedVersion": 1, "expectedReleaseId": release}
    for response in (
        world.api.get("/model-drafts"),
        world.api.post("/model-drafts", {"name": "x", "model": {}}),
        world.api.post(
            "/model-drafts/00000000-0000-4000-8000-000000000000/installation",
            {"expectedVersion": 1},
        ),
        world.api.post(f"/workspaces/{W1}/model/activation", body),
    ):
        assert response.status_code == 404, response.text


@pytest.mark.journey("J08.2")
@pytest.mark.structures("R", "R.u", "R.b", "K", "B1n")
def test_compare_two_installed_releases(world):
    """Given M1 (with a consumer API) active and M2 installed, which adds an attribute, renames a view
    and removes a consumer field. When M2 is compared with M1. Then the changes list the added path
    and the changed name with both sides; compatibility names the active release; the consumer
    contracts report the removal. An unknown release to compare with is refused."""
    base = world.with_consumer_api(copy.deepcopy(world.configuration.model))
    base["release"]["version"] += "-api"
    m1 = world.install(base)["id"]
    ok(world.activate(m1))
    model, added = world.candidate("compatible")
    model = world.with_consumer_api(model, drop_flag=True)
    m2 = world.install(model)["id"]

    diff = ok(world.api.get(f"/model-releases/{m2}/diff", againstReleaseId=m1))
    additions = [c for c in diff["changes"] if c["kind"] == "added" and added in c["path"]]
    assert additions and all(c.get("before") is None for c in additions)
    renamed = [
        c
        for c in diff["changes"]
        if c["kind"] == "changed" and c["path"].endswith("/name") and c["after"] == "Renamed view"
    ]
    assert renamed and renamed[0]["before"]
    assert diff["compatibility"]["activeReleaseId"] == m1
    assert diff["consumerContracts"]["classification"] == "version_required"
    refused(
        world.api.get(
            f"/model-releases/{m2}/diff", againstReleaseId="00000000-0000-4000-8000-000000000000"
        ),
        404,
        "MODEL_RELEASE_NOT_FOUND",
    )


@pytest.mark.journey("J08.3", "J08.8")
@pytest.mark.structures("R")
def test_reactivate_an_older_release_and_read_the_activation_history(world):
    """Given M1 selected at bootstrap and M2 activated. When M1 is activated again. Then the model
    reads M1; M1's history lists only that activation, coming from M2, and M2's its own, coming from
    M1, oldest first; an unknown release's history is refused."""
    m1 = _active(world)["releaseId"]
    model, _key = world.candidate("compatible")
    m2 = world.install(model)["id"]
    ok(world.activate(m2))
    ok(world.activate(m1))
    assert _model_release(world) == m1

    first = ok(world.api.get(f"/model-releases/{m1}/activations"))["items"]
    assert [(i["kind"], i["previousReleaseId"]) for i in first] == [("activated", m2)]
    second = ok(world.api.get(f"/model-releases/{m2}/activations"))["items"]
    assert [(i["kind"], i["previousReleaseId"]) for i in second] == [("activated", m1)]
    refused(
        world.api.get("/model-releases/00000000-0000-4000-8000-000000000000/activations"),
        404,
        "MODEL_RELEASE_NOT_FOUND",
    )


@pytest.mark.journey("J08.4")
@pytest.mark.structures("R")
def test_data_the_candidate_does_not_fit_blocks_activation(world):
    """Given a release that makes an attribute required, and records lacking it in the default
    workspace and in the other workspaces running its model. When it is compiled, compared and
    activated into the default workspace. Then compiling and comparing need a migration, with a
    diagnostic at the type's path counting the default workspace's records, and one entry for each
    active workspace running the model counting its own (a retired one is not listed, 0.11 M3 D37);
    activation is refused naming the data, and the runtime state and model are unchanged."""
    for name in ("Lacking one", "Lacking two"):
        world.made("R", name)
    model, key = world.candidate("incompatible")
    lacking = {}
    for workspace in (W1, "second-site"):
        page = ok(
            world.api.get(
                f"/objects/{world.key('R')}",
                workspaceKey=workspace,
                pageSize=1,
                includeTotal=True,
                **{f"filter.{key}.isUnset": "true"},
            )
        )
        lacking[workspace] = page["totalCount"]
    state = _active(world)

    def counted(compatibility):
        (diagnostic,) = [d for d in compatibility["diagnostics"] if world.key("R") in d["path"]]
        return diagnostic["count"]

    compiled = _compile(world, _draft(world, model))
    release = world.install(model)["id"]
    diff = ok(
        world.api.get(f"/model-releases/{release}/diff", againstReleaseId=state["releaseId"])
    )
    for answer in (compiled, diff):
        compatibility = answer["compatibility"]
        assert compatibility["classification"] == "migration_required"
        assert counted(compatibility) == lacking[W1]
        by_workspace = {item["workspaceKey"]: item for item in compatibility["workspaces"]}
        assert "closed-site" not in by_workspace
        for workspace, count in lacking.items():
            if count:
                assert by_workspace[workspace]["classification"] == "migration_required"
                assert counted(by_workspace[workspace]) == count
    refused(world.activate(release), 409, "MODEL_MIGRATION_REQUIRED")
    assert _active(world) == state and _model_release(world) == state["releaseId"]


@pytest.mark.journey("J08.5")
@pytest.mark.structures("R")
def test_two_activations_from_the_same_runtime_state(world):
    """Given administrators A and B who read the runtime state at version v, and two compatible
    releases installed. When A activates one with v, then B the other with v. Then B is refused and
    A's release stays active at v+1."""
    state = _active(world)
    model, _key = world.candidate("compatible")
    m2 = world.install(model)["id"]
    model["release"]["version"] += "-other"
    m3 = world.install(model)["id"]
    body = {"expectedVersion": state["version"], "expectedReleaseId": state["releaseId"]}
    path = f"/workspaces/{W1}/model/activation"
    ok(world.api.post(path, {"releaseId": m2, **body}))
    refused(world.api.post(path, {"releaseId": m3, **body}), 409, "ACTIVATION_CONFLICT")
    now = _active(world)
    assert (now["releaseId"], now["version"]) == (m2, state["version"] + 1)


@pytest.mark.journey("J08.6")
@pytest.mark.structures("R")
def test_activation_beside_a_live_write(world):
    """Given actor A's live write resolved under M1 and waiting for its workspace, and actor B
    activating M2. Then B's activation completes while A still waits; A is then refused because the
    release changed, naming both releases, and nothing of A is saved."""
    m1 = _active(world)["releaseId"]
    model, _key = world.candidate("compatible")
    m2 = world.install(model)["id"]
    record = world.made("R", "Before activation")

    with world.holding(W1, as_write=True) as held:
        write = held.start(lambda: world.update("R", record["id"], record["version"], name="Late"))
        held.waiting(1)
        ok(world.activate(m2))
        assert not write.done()
    error = refused(write.result(timeout=30), 409, "MODEL_RELEASE_CHANGED")
    assert (error["details"]["resolvedReleaseId"], error["details"]["currentReleaseId"]) == (m1, m2)
    assert world.record("R", record["id"])["name"] == "Before activation"


@pytest.mark.journey("J08.7")
@pytest.mark.structures("R")
def test_export_a_release_and_reuse_it(world):
    """When a release is read with and without its model, and the exported model saved as a draft and
    compiled. Then the model is present only when asked for, and the draft compiles valid with the
    release's model hash."""
    model, _key = world.candidate("compatible")
    release = world.install(model)
    plain = ok(world.api.get(f"/model-releases/{release['id']}"))
    assert "model" not in plain
    exported = ok(world.api.get(f"/model-releases/{release['id']}", includeModel=True))["model"]
    compiled = _compile(world, _draft(world, exported))
    assert compiled["valid"] is True and compiled["modelHash"] == release["modelHash"]


@pytest.mark.journey("J08.10")
@pytest.mark.structures("R", "R.u")
def test_a_release_dropping_and_restoring_unique(world):
    """Given a release in which R's unique attribute is no longer unique, activated. When two
    records take one value, the release restoring uniqueness is activated, one record changes and
    it is activated again. Then the records may share the value meanwhile; restoring it is refused
    while they do; once it is active, a create and a batch item with the value are refused."""
    restoring = _active(world)["releaseId"]
    model = copy.deepcopy(world.configuration.model)
    u = world.key("R.u")
    attribute = next(a for a in model["attributeTypes"] if a["key"] == u)
    del attribute["features"]["unique"]
    model["release"]["version"] += "-not-unique"
    ok(world.activate(world.install(model)["id"]))

    first = world.made("R", "Sharing one", values={"R.u": "SHARED"})
    world.made("R", "Sharing two", values={"R.u": "SHARED"})
    refused(world.activate(restoring), 409, "MODEL_MIGRATION_REQUIRED")
    ok(world.update("R", first["id"], first["version"], values={"R.u": "NO-LONGER-SHARED"}))
    ok(world.activate(restoring))

    refused(world.create("R", "Third", values={"R.u": "SHARED"}), 409, "DUPLICATE_ATTRIBUTE_VALUE")
    item = {
        "op": "create",
        "applicationKey": world.app("R"),
        "objectTypeKey": world.key("R"),
        "name": "Batch third",
        "attributes": [
            {"attributeTypeKey": k, "value": v}
            for k, v in {**world.required_values("R"), u: "SHARED"}.items()
        ],
    }
    result = ok(
        world.api.post(
            "/batches",
            {"policy": "independent", "run": "inline", "workspaceKey": W1, "items": [item]},
        )
    )
    assert result["items"][0]["error"]["code"] == "DUPLICATE_ATTRIBUTE_VALUE"


@pytest.mark.journey("J08.11")
@pytest.mark.structures("L1", "K", "Ll1k")
def test_a_binding_tightened_to_many_to_one_waits_for_its_data(world):
    """Given an L1 record related to two K records by a many-to-many binding. When a release makes
    the binding many-to-one. Then comparing needs a migration, counting one record at the binding's
    cardinality, and activation is refused. When one of the two relationships is removed. Then the
    release activates."""
    holder = world.made("L1", "Holds two")["id"]
    first = ok(world.relate("Ll1k", holder, world.ids["k01"]), 201)
    ok(world.relate("Ll1k", holder, world.ids["k02"]), 201)
    identity = (world.key("Ll1k"), world.key("L1"), world.key("K"))
    model = copy.deepcopy(world.configuration.model)
    for binding in model["objectTypeRelations"]:
        if (binding["relationTypeKey"], binding["fromObjectTypeKey"]) == identity[:2]:
            binding["cardinality"] = "many-to-one"
    model["release"]["version"] += "-one"
    state = _active(world)

    release = world.install(model)["id"]
    diff = ok(
        world.api.get(f"/model-releases/{release}/diff", againstReleaseId=state["releaseId"])
    )
    assert diff["compatibility"]["classification"] == "migration_required"
    (diagnostic,) = diff["compatibility"]["diagnostics"]
    assert diagnostic["path"] == "/objectTypeRelations/" + "/".join(identity) + "/cardinality"
    assert diagnostic["count"] == 1
    refused(world.activate(release), 409, "MODEL_MIGRATION_REQUIRED")

    ok(world.api.delete(f"/relations/{first['id']}", expectedVersion=first["version"]), 204)
    ok(world.activate(release))
    assert _model_release(world) == release


def _validation(world, model):
    return ok(world.api.post("/model-validations", {"model": model}))


@pytest.mark.journey("J08.12")
@pytest.mark.structures("H", "K", "Bnn", "Bn1", "B1n", "Vnn")
def test_a_relation_column_where_the_model_allows_it(world):
    """Given the configuration's model. When H's table view shows the many-to-many and the
    many-to-one relationship, sorts by the many-to-one, K's view shows the many-to-many read
    backwards and a detail's table panel shows one. Then it validates. When a relation column is
    put where it is not offered (a relations panel, a mapping grid, a field form in filter fields, a
    many-valued sort),
    names an unknown relationship or one H is at neither end of, or the model is schema 0.8. Then
    each is refused at its pointer."""
    h, k = world.key("H"), world.key("K")
    bnn, bn1, b1n = world.key("Bnn"), world.key("Bn1"), world.key("B1n")
    reverse = next(
        r["reverseKey"] for r in world.configuration.model["relationTypes"] if r["key"] == bnn
    )

    def view_of(model, type_key):
        for a, application in enumerate(model["applications"]):
            for v, view in enumerate(application["views"]):
                if view["type"] == "table" and view["objectTypeKey"] == type_key:
                    return view, f"/applications/{application['key']}/views/{view['key']}", a
        raise AssertionError(type_key)

    def allowed():
        model = copy.deepcopy(world.configuration.model)
        view, _path, a = view_of(model, h)
        view["config"]["columns"] += [f"related:{bnn}", f"related:{bn1}"]
        view["config"]["sortFields"] += [f"related:{bn1}"]
        view["config"]["defaultSort"] = f"-related:{bn1}"
        view_of(model, k)[0]["config"]["columns"].append(f"related:{reverse}")
        model["applications"][a].setdefault("details", []).append(
            {
                "objectTypeKey": h,
                "panels": [
                    {
                        "key": "listed",
                        "title": "Listed",
                        "type": "table",
                        "config": {"objectTypeKey": h, "columns": ["name", f"related:{bn1}"]},
                    }
                ],
            }
        )
        return model

    assert _validation(world, allowed())["valid"] is True

    def refused_at(change, pointer):
        model = allowed()
        change(model)
        result = _validation(world, model)
        assert result["valid"] is False, pointer
        assert result["diagnostics"][0]["path"] == pointer, result["diagnostics"]

    _view, h_path, a = view_of(world.configuration.model, h)
    application = world.configuration.model["applications"][a]["key"]
    detail_path = f"/applications/{application}/details/{h}/panels"

    def relations_panel(model):
        details = model["applications"][a]["details"]
        details[-1]["panels"].append(
            {
                "key": "related",
                "title": "Related",
                "type": "relations",
                "config": {
                    "relationTypeKeys": [bnn],
                    "direction": "outgoing",
                    "columns": ["name", f"related:{reverse}"],
                },
            }
        )

    def mapping_grid(model):
        for view in model["applications"][a]["views"]:
            if view["key"] == world.key("Vnn"):
                view["config"]["sourceColumns"].append(f"related:{bn1}")

    def h_config(model):
        return view_of(model, h)[0]["config"]

    refused_at(relations_panel, f"{detail_path}/related")
    refused_at(mapping_grid, f"/applications/{application}/views/{world.key('Vnn')}/config/sourceColumns")
    # Since 0.9 K6 (D154) a filter may name the relationship; a field of its records stays refused.
    refused_at(lambda m: h_config(m)["filterFields"].append(f"related:{bn1}.name"), f"{h_path}/config/filterFields")
    refused_at(lambda m: h_config(m)["sortFields"].append(f"related:{bnn}"), f"{h_path}/config/sortFields")
    refused_at(lambda m: h_config(m)["columns"].append("related:no-such"), f"{h_path}/config/columns")
    refused_at(lambda m: h_config(m)["columns"].append(f"related:{b1n}"), f"{h_path}/config/columns")


@pytest.mark.journey("J08.12")
@pytest.mark.structures("R", "G", "D", "K", "Bscope", "K.code")
def test_a_relation_column_naming_a_field(world):
    """Given the configuration's model. When R's table view shows the scoped relationship by its
    records' G ancestor's code. Then it validates. When the field names an ancestor D cannot sit
    under, an attribute no D binds, or the column is put in sortFields. Then each is refused at its
    pointer."""
    r, g, k = world.key("R"), world.key("G"), world.key("K")
    column = f"related:{world.key('Bscope')}.ancestor:{g}.{world.key('K.code')}"

    def with_column(change):
        model = copy.deepcopy(world.configuration.model)
        for application in model["applications"]:
            for view in application["views"]:
                if view["type"] == "table" and view["objectTypeKey"] == r:
                    view["config"]["columns"].append(change(column))
                    path = f"/applications/{application['key']}/views/{view['key']}/config"
                    return model, view, path
        raise AssertionError(r)

    model, view, _path = with_column(lambda c: c)
    assert _validation(world, model)["valid"] is True

    for bad in (column.replace(f"ancestor:{g}.", f"ancestor:{k}."), f"related:{world.key('Bscope')}.no-such-field"):
        model, _view, path = with_column(lambda _c, bad=bad: bad)
        result = _validation(world, model)
        assert result["valid"] is False and result["diagnostics"][0]["path"] == f"{path}/columns", bad

    model, view, path = with_column(lambda c: c)
    view["config"]["sortFields"].append(column)
    result = _validation(world, model)
    assert result["valid"] is False and result["diagnostics"][0]["path"] == f"{path}/sortFields"


@pytest.mark.journey("J08.12")
@pytest.mark.structures("H", "K", "Bnn")
def test_a_relationship_in_a_views_filter_fields(world):
    """Given the configuration's model. When H's table view offers its many-to-many as a filter. Then
    it validates. When it offers a field of the related records or an unknown relationship as a
    filter. Then each is refused at the view's filterFields."""
    h, bnn = world.key("H"), world.key("Bnn")

    def with_filter(field):
        model = copy.deepcopy(world.configuration.model)
        for application in model["applications"]:
            for view in application["views"]:
                if view["type"] == "table" and view["objectTypeKey"] == h:
                    view["config"]["filterFields"].append(field)
                    return model, f"/applications/{application['key']}/views/{view['key']}/config/filterFields"
        raise AssertionError(h)

    model, _path = with_filter(f"related:{bnn}")
    assert _validation(world, model)["valid"] is True
    for field in (f"related:{bnn}.name", "related:no-such"):
        model, path = with_filter(field)
        result = _validation(world, model)
        assert result["valid"] is False and result["diagnostics"][0]["path"] == path, field



@pytest.mark.journey("J08.1")
@pytest.mark.structures("H", "K", "K.code", "Bcand", "R", "G", "D")
def test_a_bindings_candidates_are_checked_and_change_compatibly(world):
    """Given the model's Bcand binding, whose K end takes codes starting "OK". When it is validated
    with a criterion on an unknown field, an ancestor type K cannot sit under, an
    operator its field lacks and a value of the wrong type, and compiled with its criterion changed.
    Then each is invalid at the criterion's field, operator or value; the changed one is compatible
    (0.9 K7, D170, D176)."""
    bcand = world.key("Bcand")

    def with_criteria(criterion):
        model = copy.deepcopy(world.configuration.model)
        binding = next(b for b in model["objectTypeRelations"] if b["relationTypeKey"] == bcand)
        binding["candidates"] = {"to": [criterion]}
        model["release"]["version"] += "-candidates"
        return model

    code = world.key("K.code")
    cases = [
        ({"field": "no-such-field", "op": "eq", "value": "x"}, "field"),
        ({"field": f"ancestor:{world.key('G')}.name", "op": "eq", "value": "x"}, "field"),
        ({"field": code, "op": "lt", "value": "x"}, "op"),
        ({"field": code, "op": "eq", "value": 3}, "value"),
    ]
    prefix = f"/objectTypeRelations/{bcand}/{world.key('H')}/{world.key('K')}/candidates/to/0/"
    for criterion, part in cases:
        answer = ok(world.api.post("/model-validations", {"model": with_criteria(criterion)}))
        assert answer["valid"] is False
        assert [d["path"] for d in answer["diagnostics"]] == [prefix + part]
    changed = with_criteria({"field": code, "op": "contains", "value": "K"})
    compiled = _compile(world, _draft(world, changed, name="Candidates changed"))
    assert compiled["valid"] is True and compiled["compatibility"]["classification"] == "compatible"
