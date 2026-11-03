"""Bounded offline checks of the C9 consumer showcase; no database, server or HTTP capture."""
import json,re,warnings,hmac
from pathlib import Path
from jsonschema import Draft202012Validator
with warnings.catch_warnings():
 warnings.simplefilter('ignore',DeprecationWarning)
 from jsonschema import RefResolver
from app.engine.model.compiler import compile_model
from app.engine.model.consumer_definitions import consumer_api
from app.engine.model.consumer_openapi import consumer_openapi
from app.engine.events.delivery import sign
root=Path('guide')
raw=json.loads((root/'samples/model.json').read_text())
compiled=compile_model(raw)
assert compiled.valid,compiled.diagnostics
api=consumer_api(compiled.model,'stops')
doc=consumer_openapi(compiled.model,api,root_path='',resolve_max_items=1000,token_url='/oauth/token')
resolver=RefResolver.from_schema(doc)
text=(root/'src/content/docs/examples/the-consumer-api.md').read_text()
bodies=[json.loads(x) for x in re.findall(r'```json\n(.*?)\n```',text,re.S)]
assert len(bodies)==10
proof=json.loads((root/'_coverage/notes/C9-HOME/composed-examples.json').read_text())
assert bodies[3]==proof['stop']
assert bodies[4]['items']==[proof['firstStop']]
assert bodies[5]['items']==[proof['stop']]
assert bodies[6]=={**proof['stop'],'matchScore':900}
assert bodies[7]['items'][0]['object']==bodies[6]
for body,path,method in [(bodies[3],'/objects/{id}','get'),(bodies[4],'/lists/all-stops','get'),(bodies[5],'/lists/all-stops','get'),(bodies[6],'/xref','get'),(bodies[7],'/resolve','post'),(bodies[9],'/events','get')]:
 schema=doc['paths']['/api/consumer/stops/v1'+path][method]['responses']['200']['content']['application/json']['schema']
 Draft202012Validator(schema,resolver=resolver).validate(body)
request=json.loads(re.search(r'POST /api/consumer/stops/v1/resolve.*?\n\n(.*?)\n```',text,re.S)[1])
schema=doc['paths']['/api/consumer/stops/v1/resolve']['post']['requestBody']['content']['application/json']['schema']
Draft202012Validator(schema,resolver=resolver).validate(request)
raw_api=raw['consumerApis'][0]
for key in ['key','name','contractVersion','exposes','publicNames']:
 assert bodies[2][key]==raw_api[key]
assert bodies[2]['object']['fields']==raw_api['object']['fields']
assert bodies[2]['operations']['events']==raw_api['operations']['events']
assert bodies[8]=={'error':{'code':'LIST_NOT_FOUND','message':"List 'no-such-list' not found"}}
operators={o['id']:o['code'] for o in json.loads((root/'samples/data/reference/operators.json').read_text())}
assert sum(operators.get(s['operator'])=='MGB-fo' for s in json.loads((root/'samples/data/reference/stops.json').read_text()))==13
http=re.search(r'```http\nPOST /refiroo-events HTTP/1.1\n(.*?)\n```',text,re.S)[1]
headers,body=http.split('\n\n',1)
headers=dict(line.split(': ',1) for line in headers.splitlines())
assert int(headers['Content-Length'])==len(body.encode())
assert hmac.compare_digest(headers['RDM-Signature'],sign('guide-example-only',int(headers['RDM-Timestamp']),body.encode()))
assert json.loads(body)['events']==bodies[9]['items']
print('PASS: reference model compiles; six complete response bodies and the batch request validate against generated stops OpenAPI.')
print('PASS: published object values match production composition; declaration fields/event match source; filtered count is 13.')
print('PASS: complete webhook body has correct byte length and production HMAC signature; its event matches the pull example.')
print('LIMIT: offline composition/schema/signature checks only; no live API, database, receiver or browser run.')
