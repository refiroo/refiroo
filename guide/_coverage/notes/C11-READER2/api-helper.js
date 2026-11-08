globalThis.apiEvidence=[];
globalThis.api=async function(path,opts={}) {
 const r=await fetch('http://localhost:8480'+path,{...opts,headers:{Authorization:'Bearer '+consumerToken,...opts.headers}});
 const raw=await r.text();let body;try{body=JSON.parse(raw)}catch{body=raw.slice(0,300)}
 const entry={path,status:r.status,etag:r.headers.get('etag'),body};apiEvidence.push(entry);
 fs.writeFileSync('guide/_coverage/notes/C11-READER2/api-evidence.json',JSON.stringify(apiEvidence,null,2));
 return entry;
};
console.log('API helper ready; tokens remain in memory.');
