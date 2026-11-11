"""Check the new catalogue declaration without a database; run from the repository root."""
import json
import re
from pathlib import Path
from app.engine.model.compiler import compile_model
from app.engine.model.consumer_definitions import consumer_api
from app.engine.model.consumer_openapi import consumer_openapi
from app.engine.reads.consumer_request import included

root = Path("guide/src/content/docs")
blocks = re.findall(r"```json\n(.*?)\n```", (root / "integrate/consumer-apis.md").read_text(), re.S)
api = next(json.loads(block) for block in blocks if json.loads(block).get("key") == "catalog")
model = {
    "schemaVersion": "0.10",
    "release": {"key": "catalogue", "name": "Catalogue", "version": "1.0.0"},
    "product": {"name": "Catalogue"},
    "attributeTypes": [
        {"key": "approved", "name": "Approved", "valueType": "boolean"},
        {"key": "external-code", "name": "External code", "valueType": "text"},
    ],
    "objectTypes": [
        {"key": "category", "name": "Category", "pluralName": "Categories",
         "attributes": [{"attributeTypeKey": "approved"}]},
        {"key": "item", "name": "Item", "pluralName": "Items",
         "behavior": {"parentRelationTypeKeys": ["category-contains-item"]}},
        {"key": "code", "name": "Code", "pluralName": "Codes",
         "attributes": [{"attributeTypeKey": "external-code"}]},
    ],
    "relationTypes": [
        {"key": "category-contains-item", "reverseKey": "item-in-category",
         "name": "Contains item", "reverseName": "In category", "features": {"parentOf": True}},
        {"key": "category-has-code", "reverseKey": "code-of-category",
         "name": "Has code", "reverseName": "Of category"},
        {"key": "item-has-code", "reverseKey": "code-of-item",
         "name": "Has code", "reverseName": "Of item"},
    ],
    "objectTypeRelations": [
        {"relationTypeKey": key, "fromObjectTypeKey": owner, "toObjectTypeKey": target,
         "cardinality": "one-to-many"}
        for key, owner, target in [
            ("category-contains-item", "category", "item"),
            ("category-has-code", "category", "code"),
            ("item-has-code", "item", "code"),
        ]
    ],
    "applications": [],
    "consumerApis": [api],
}
compiled = compile_model(model)
assert compiled.valid, compiled.diagnostics
api = consumer_api(compiled.model, "catalog")
assert api.on_request() == ("codes", "parent.codes")
assert included(api, ["codes", "parent.codes"], "/query/include") == {"codes", "parent.codes"}
document = consumer_openapi(compiled.model, api, root_path="", resolve_max_items=1000, token_url="/token")
schemas = document["components"]["schemas"]
assert "codes" not in schemas["Object"]["required"]
parent = schemas["Object"]["properties"]["parent"]
assert "codes" not in parent["required"]
assert parent["properties"]["isApproved"]["type"] == ["boolean", "null"]
for path, operations in document["paths"].items():
    if "get" not in operations or not any(part in path for part in ("/objects/", "/lists/", "/xref")):
        continue
    include = next(p for p in operations["get"]["parameters"] if p["name"] == "include")
    assert include["schema"]["items"]["enum"] == ["codes", "parent.codes"]
print("Declaration compiles; include enums and optional object/parent blocks checked.")
print("Generated parent schema:", json.dumps(parent, sort_keys=True))
Path("guide/_coverage/notes/CA1-GUIDE/catalogue-openapi.json").write_text(json.dumps(document, indent=2) + "\n")
