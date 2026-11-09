"""Validate the illustrative stops extension; no persistence or reference-data changes."""
import json
from pathlib import Path
from app.engine.model.compiler import compile_model
root=Path('guide')
model=json.loads((root/'samples/model.json').read_text())
model['attributeTypes'].extend([
 {'key':'local-name','name':'Local name','valueType':'text'},
 {'key':'is-primary','name':'Primary contact','valueType':'boolean'},
])
next(b for b in model['objectTypeRelations'] if b['relationTypeKey']=='stop-operated-by-operator')['attributeTypeKeys']=['local-name','is-primary']
api={
 'key':'stops','name':'Stops API','contractVersion':2,
 'exposes':['stop'],'publicNames':{'stop':'Stop'},
 'object':{'fields':{'id':{'role':'id'},'name':{'role':'name','from':'name'}},'related':{'operator':{'via':'stop-operated-by-operator','fields':{'id':'id','name':'name','localName':'relation:local-name','isPrimary':'relation:is-primary'}}}},
 'operations':{'objects':{},'lists':{'all-stops':{'of':'stop','sortBy':'stop-number'}},'xref':{'matchOn':[{'field':'name','exact':10}],'alsoMatchThrough':[{'related':'operator','firstOf':[{'field':'relation:local-name','exact':90}]}]},'resolve':{},'events':{'custom':[{'key':'stops-changed','objectTypes':['stop'],'changes':['updated'],'watch':{'related':['operator']}}]}},
 'filters':{'contact':{'onRelated':'operator','matchOn':['relation:local-name'],'keepOnlyMatching':True},'primary':{'onRelated':'operator','matchOn':['relation:is-primary'],'keepOnlyMatching':True}}
}
model['consumerApis']=[api]
result=compile_model(model)
assert result.valid, result.diagnostics
(root/'_coverage/notes/RV-GUIDE/consumer-declaration.json').write_text(json.dumps(api,indent=2)+'\n')
print('Illustrative stops v2 extension: model shape and references valid.')
