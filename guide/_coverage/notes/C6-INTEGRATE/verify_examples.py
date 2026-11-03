"""Validate the published examples without network or a database."""
import json,re,warnings
from pathlib import Path
from jsonschema import Draft202012Validator
with warnings.catch_warnings():
 warnings.simplefilter('ignore',DeprecationWarning)
 from jsonschema import RefResolver
from app.engine.model.compiler import compile_model
from app.engine.model.consumer_definitions import consumer_api
from app.engine.model.consumer_openapi import consumer_openapi
from app.engine.events.delivery import encode,RequestFormat,events_source
from app.models.commands import ConsumerSubscriptionCreate
root=Path(__file__).resolve().parents[3]
model=compile_model(json.loads((root/'samples/model.json').read_text())).model
api=consumer_api(model,'stops')
doc=consumer_openapi(model,api,root_path='',resolve_max_items=1000,token_url='/oauth/token')
resolver=RefResolver.from_schema(doc)
def blocks(name):return [json.loads(s) for s in re.findall(r'```json\n(.*?)\n```',(root/'src/content/docs/integrate'/name).read_text(),re.S)]
def validate(body,path,method='get',status='200',request=False):
 op=doc['paths']['/api/consumer/stops/v1'+path][method]
 schema=(op['requestBody'] if request else op['responses'][status])['content']['application/json']['schema']
 Draft202012Validator(schema,resolver=resolver).validate(body)
read=blocks('reading-business-objects.md')
assert len(read)==4
validate(read[0],'/objects/{id}')
validate(read[1],'/lists/all-stops')
validate(read[2],'/lists/all-stops')
# Shared structured errors are checked against their emitted code/message in the source.
assert read[3]=={'error':{'code':'LIST_NOT_FOUND','message':"List 'no-such-list' not found"}}
look=blocks('looking-up-and-resolving.md')
assert len(look)==5
validate(look[1],'/xref')
validate(look[3],'/xref')
validate(look[4],'/resolve','post')
resolve_text=(root/'src/content/docs/integrate/looking-up-and-resolving.md').read_text()
request_body=json.loads(re.search(r'POST /api/consumer/stops/v1/resolve.*?\n\n(.*?)\n```',resolve_text,re.S)[1])
validate(request_body,'/resolve','post',request=True)
events=blocks('consumer-events-and-webhooks.md')
assert len(events)==3
validate(events[1],'/events')
proof=json.loads((root/'_coverage/notes/C6-INTEGRATE/webhook-example.json').read_text())
text=(root/'src/content/docs/integrate/consumer-events-and-webhooks.md').read_text()
ns={};exec(re.search(r'```python\n(.*?)\n```',text,re.S)[1],ns)
verify=ns['verify_webhook'];args=(proof['secret'],proof['headers'],proof['body'].encode())
assert verify(*args,proof['timestamp'])
assert not verify(proof['secret'],proof['headers'],proof['body'].encode()+b' ',proof['timestamp'])
assert not verify(*args,proof['timestamp']+301)
assert not verify(proof['secret'],{**proof['headers'],'RDM-Signature':'sha256=wrong,'+proof['headers']['RDM-Signature']},proof['body'].encode(),proof['timestamp']+301)
assert verify(proof['secret'],{**proof['headers'],'RDM-Signature':'sha256=wrong,'+proof['headers']['RDM-Signature']},proof['body'].encode(),proof['timestamp'])
assert not verify(proof['secret'],{**proof['headers'],'RDM-Timestamp':'１２３'},b'',proof['timestamp'])
assert not verify(proof['secret'],{**proof['headers'],'RDM-Signature':'sha256=☃'},b'',proof['timestamp'])
assert events[2]['data']=={k:v for k,v in proof['event'].items() if k not in ['object','stateAt']}
http=re.search(r'```http\nPOST /refiroo-events.*?\n\n(.*?)\n```',text,re.S)[1]
assert http==proof['body']
guide=(root/'src/content/docs/guide/integrate/subscribe-a-webhook-and-verify-it.md').read_text()
subscription=json.loads(re.search(r'POST /api/v1/consumer-subscriptions.*?\n\n(.*?)\n```',guide,re.S)[1])
ConsumerSubscriptionCreate.model_validate(subscription)
print('PASS: 8 published response/request examples validate against the generated stops OpenAPI; subscription request validates against its command model.')
print('PASS: published verifier accepts authentic and overlap signatures, rejects tampered bytes, stale timestamps and non-ASCII input; published raw body matches production-signed bytes.')
print('LIMIT: offline schema/composition verification; no live API, database or receiver execution.')
