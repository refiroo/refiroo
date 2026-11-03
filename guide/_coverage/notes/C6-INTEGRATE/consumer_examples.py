"""Offline composition evidence; no database or server. Run with bytecode writes disabled."""
from pathlib import Path
import json
from app.engine.model.compiler import compile_model
from app.engine.model.consumer_definitions import consumer_api
from app.engine.reads.consumer_objects import ConsumerObjects, _Record, _encode
ROOT=Path(__file__).resolve().parents[3]
d={p.stem:json.loads(p.read_text()) for p in (ROOT/'samples/data/reference').glob('*.json')}
raw=json.loads((ROOT/'samples/model.json').read_text())
compiled=compile_model(raw)
assert compiled.valid, compiled.diagnostics
model=compiled.model
definition=consumer_api(model,'stops')
composer=ConsumerObjects(model,definition)
records={}
def add(kind,x,**attrs):
 values={k.replace('_','-'):v for k,v in attrs.items() if v is not None}
 values={k:_encode(model.attribute_type(k).valueType,v) for k,v in values.items()}
 r=_Record(x['id'],kind,x['name'],x.get('parent'),values)
 records[r.id]=r
 return r
add('canton',d['canton'],fso_number=d['canton']['fso'])
for x in d['districts']:add('district',x,fso_number=x['fso'])
for x in d['municipalities']:add('municipality',x,fso_number=x['fso'])
for x in d['operators']:add('operator',x,operator_code=x['code'],operator_sboid=x['sboid'])
for x in d['modes']:add('mode',x,mode_code=x['code'])
for x in d['languages']:add('language',x,language_code=x['code'])
for x in d['systems']:add('system',x,system_key=x['key'])
for x in d['codes']:add('system-code',{**x,'parent':x['system']},external_id=x['code'])
for x in d['translations']:add('name-translation',{**x,'parent':x['language']},translated_name=x['text'],active=True)
for x in d['stops']:
 add('stop',x,stop_number=x['number'],sloid=x['sloid'],abbreviation=x['abbreviation'],latitude=x['lat'],longitude=x['lon'],height=x['height'],valid_from=x['validFrom'],valid_to=x['validTo'])
def obj(stop,system=None):
 related={p.output:[] for p in composer.projections}
 related['operator']=[(stop['id'],records[stop['operator']])] if stop['operator'] else []
 related['modes']=[(stop['id'],records[i]) for i in stop['modes']]
 related['systemCodes']=[(stop['id'],records[c['id']]) for c in d['codes'] if stop['id'] in c['targets'] and (system is None or records[c['system']].values['system-key']==system)]
 related['translations']=[(stop['id'],records[t['id']]) for t in d['translations'] if t['object']==stop['id']]
 related={k:sorted(v,key=lambda pair:(pair[1].name,pair[1].id)) for k,v in related.items()}
 return composer._object(records[stop['id']],related,records,None)
stop=next(x for x in d['stops'] if x['name']=='Tschamut-Selva')
output={'stop':obj(stop),'id':stop['id'],'operator':records[stop['operator']].values['operator-code'],'firstStop':obj(min(d['stops'],key=lambda x:x['number'])),'count':len(d['stops'])}
(ROOT/'_coverage/notes/C6-INTEGRATE/examples.json').write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n')
print('Compiled reference model; composed',stop['name'],'with production object composer; records',len(records))
print(json.dumps(output['stop'],ensure_ascii=False,indent=2))
print('first stop',output['firstStop']['name'],'total',output['count'])
print('Parameters',definition.parameters)
