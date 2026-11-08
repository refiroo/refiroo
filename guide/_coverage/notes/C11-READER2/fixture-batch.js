globalThis.ids=Object.fromEntries(['canton','district','munA','munB','stopA','stopB','lang','nameA','nameB','system','codeA','codeB'].map(k=>[k,crypto.randomUUID()]));
const attrs=o=>Object.entries(o).map(([attributeTypeKey,value])=>({attributeTypeKey,value}));
const item=(ref,type,name,parent,values,app='network',initialRelations=[])=>({ref,op:'create',id:ids[ref],applicationKey:app,objectTypeKey:type,name,...(parent?{parent:{id:ids[parent]}}:{}),attributes:attrs(values),initialRelations});
const items=[item('canton','canton','Graubünden reader',null,{'canton-abbreviation':'GR-C11'}),item('district','district','Plessur reader','canton',{}),item('munA','municipality','Chur reader','district',{'fso-number':3901}),item('munB','municipality','Arosa reader','district',{'fso-number':3921}),item('stopA','stop','Chur reader A','munA',{'designation':'Chur reader A','stop-number':8509000}),item('stopB','stop','Chur reader B','munA',{'designation':'Chur reader B','stop-number':8509006}),item('lang','language','English reader',null,{'language-code':'en'},'names'),item('nameA','name-translation','Chur reader English','lang',{'translated-name':'Chur reader','active':true},'names',[{relationTypeKey:'object-has-translation',direction:'incoming',object:{id:ids.munA}}])];
const req={workspaceKey:'reader',policy:'atomic',run:'inline',items};
fs.writeFileSync('guide/_coverage/notes/C11-READER2/fixture-batch-request.json',JSON.stringify(req,null,2));
const result=await api('/api/v1/batches',{method:'POST',headers:{'Content-Type':'application/json','Idempotency-Key':'C11-reader2-owned-hierarchy'},body:JSON.stringify(req)});
console.log(JSON.stringify(result));
fs.writeFileSync('guide/_coverage/notes/C11-READER2/fixture-ids.json',JSON.stringify(ids,null,2));
