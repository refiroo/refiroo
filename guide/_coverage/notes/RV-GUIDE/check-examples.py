import json,re,runpy
from pathlib import Path
from copy import deepcopy
from app.engine.model.compiler import compile_model
from app.models.commands import RelationGridChange
root=Path('guide'); runpy.run_path(str(root/'_coverage/notes/RV-GUIDE/consumer-example.py'))
pages=[root/'src/content/docs'/n for n in [
 'guide/model/add-a-relationships-table.md','use/relationship-tables.md',
 'guide/use/change-relationship-values-in-bulk.md','integrate/relationships-and-their-values.md',
 'integrate/consumer-apis.md','guide/integrate/submit-a-bulk-change.md']]
count=0
for page in pages:
 for body in re.findall(r'```json\n(.*?)\n```',page.read_text(),re.S):
  json.loads(body);count+=1
bulk=(root/'src/content/docs/guide/integrate/submit-a-bulk-change.md').read_text()
http=next(b for b in re.findall(r'```http\n(.*?)\n```',bulk,re.S) if '/relations/grid-change' in b)
body=json.loads(http.split('\n\n',1)[1]);RelationGridChange.model_validate(body)
selection=json.loads(re.findall(r'```json\n(.*?)\n```',bulk,re.S)[1])
body.pop('fromObjectIds');body.update(selection);RelationGridChange.model_validate(body)
print(f'{count} JSON fences parse; grid request and all-matching selection pass API input validation.')
# Check the editor-generated configuration's JSON attribute edge, without changing source/model data.
model=json.loads((root/'samples/model.json').read_text())
model['attributeTypes'].append({'key':'relationship-detail','name':'Relationship detail','valueType':'json'})
next(b for b in model['objectTypeRelations'] if b['relationTypeKey']=='stop-operated-by-operator')['attributeTypeKeys']=['relationship-detail']
config={'relationTypeKey':'stop-operated-by-operator','fromObjectTypeKey':'stop','toObjectTypeKey':'operator','fromColumns':['name'],'toColumns':['name'],'attributeColumns':['relationship-detail'],'filterFields':[],'sortFields':['from:name','to:name','relation:relationship-detail'],'defaultSort':'from:name','groupBy':None,'pageSize':20}
model['applications'][0]['views'].append({'key':'relationship-json-example','name':'Relationship JSON example','type':'relationTable','config':config})
result=compile_model(model)
assert not result.valid
print('JSON attribute editor configuration refusal:',[(d.code,d.path,d.message) for d in result.diagnostics])
