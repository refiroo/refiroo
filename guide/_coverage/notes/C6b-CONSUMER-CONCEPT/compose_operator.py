"""Compose the reference operator offline; no HTTP or database calls."""
import json
from pathlib import Path
from app.engine.model.compiler import compile_model
from app.engine.model.consumer_definitions import consumer_api
from app.engine.reads.consumer_objects import ConsumerObjects, _Record

root = Path(__file__).resolve().parents[3]
model = compile_model(json.loads((root / 'samples/model.json').read_text())).model
composer = ConsumerObjects(model, consumer_api(model, 'stops'))
operator = next(x for x in json.loads((root / 'samples/data/reference/operators.json').read_text()) if x['code'] == 'MGB-fo')
record = _Record(operator['id'], 'operator', operator['name'], None, {'operator-code': operator['code'], 'operator-sboid': operator['sboid']})
result = composer._object(record, {p.output: [] for p in composer.projections}, {}, None)
(root / '_coverage/notes/C6b-CONSUMER-CONCEPT/operator.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
print(json.dumps(result, ensure_ascii=False, indent=2))
