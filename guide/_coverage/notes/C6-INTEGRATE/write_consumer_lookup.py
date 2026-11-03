import json
from finish_unit import root,steering,finish
steering()
e=json.loads((root/'_coverage/notes/C6-INTEGRATE/examples.json').read_text()); stop=e['stop']; scored={**stop,'matchScore':900}
def js(x):return '```json\n'+json.dumps(x,ensure_ascii=False,indent=2)+'\n```\n'
def req(method,path,body=None):
 s='```http\n'+method+' '+path+' HTTP/1.1\nHost: <instance>\nAuthorization: Bearer <consumer-token>\nAccept: application/json\n'
 if body is not None:s+='Content-Type: application/json\n\n'+json.dumps(body,ensure_ascii=False,indent=2)+'\n'
 return s+'```\n'
p=root/'src/content/docs/integrate/looking-up-and-resolving.md'
s=p.read_text()+'''
## A lookup with a score

**Reference-data example:** the `stops` declaration includes these XREF rules. This excerpt shows selected rules; the complete declaration also matches IDs, other codes and translated names:

```json
{
  "xref": {
    "matchOn": [
      {"field": "stop-number", "exact": 900},
      {"field": "name", "exact": 200, "contains": 30}
    ],
    "alsoMatchThrough": [
      {
        "related": "systemCodes",
        "firstOf": [
          {"field": "external-id", "exact": 90},
          {"field": "name", "contains": 10}
        ]
      }
    ]
  }
}
```

The number `8505173` matches Tschamut-Selva's own stop number exactly, so its score is 900. A match through its Wikidata system code would use 90 instead. These weights come from this declaration; they are not universal thresholds or confidence percentages.

'''+req('GET','/api/consumer/stops/v1/xref?workspace=graubuenden&query=8505173&pageSize=20')+'''
```http
HTTP/1.1 200 OK
Content-Type: application/json
RDM-Workspace: graubuenden
```

'''+js({'results':[scored],'query':['8505173'],'workspace':'graubuenden','publication':None,'pageSize':20,'nextCursor':None,'prevCursor':None,'anchor':'<anchor-for-this-lookup>','totalCount':1,'startIndex':0})+'''
The complete shared object is returned with `matchScore` added. XREF pages use `results`, not a list's `items`. Here there is one candidate and no next page. If you add `expect=one`, the response is this one scored object directly, without the page envelope. With no candidate it is `404 NO_MATCH`; with tied top candidates it is `409 AMBIGUOUS_MATCH`. Lower-scoring alternatives do not make an untied top answer ambiguous.

Name search is case-insensitive. A contains match begins at three characters. Multiple terms use repeated `query` values or the supported comma syntax; percent-encode a literal comma inside a URL value. JSON resolution items can instead use arrays without URL splitting. Keep terms and filters unchanged when following a lookup cursor.

## A crosswalk from a stop number to another system's code

The reference declaration makes `system` target-capable:

```json
{
  "system": {
    "onRelated": "systemCodes",
    "matchOn": ["ancestor:system.system-key", "ancestor:system.name"],
    "keepOnlyMatching": true,
    "scoreOnlyMatching": true,
    "crosswalk": true
  }
}
```

As an ordinary filter, `system=wikidata-stations` narrows the objects and the related code records contributing scores. As a target, `to.system=wikidata-stations` selects the returned code representation while leaving source matching unchanged:

'''+req('GET','/api/consumer/stops/v1/xref?workspace=graubuenden&query=8505173&expect=one&to.system=wikidata-stations')+'''
```http
HTTP/1.1 200 OK
Content-Type: application/json
RDM-Workspace: graubuenden
```

'''+js({**stop,'target':stop['systemCodes'][0],'matchScore':900})+'''
`target` is the one selected system-code object. It is distinct from the source stop's identity and score. A page can carry a target array in the projection's declared shape; the single-object response requires exactly one target and returns that target as an object. The reference contract does not declare a target filter for translated names; that example capability needs a declaration that provides one.

## Resolve a small file in one request

`operations.resolve` enables this read by POST. Shared defaults are declared parameters; each item can override them. The workspace belongs on the URL. This complete request asks about two source rows and keeps their references:

'''+req('POST','/api/consumer/stops/v1/resolve?workspace=graubuenden',{'defaults':{'mode':'TRAIN'},'items':[{'ref':'row-1','query':'8505173'},{'ref':'row-2','query':'T-9999'}]})+'''
```http
HTTP/1.1 200 OK
Content-Type: application/json
RDM-Workspace: graubuenden
```

'''+js({'items':[{'index':0,'ref':'row-1','status':'found','object':scored},{'index':1,'ref':'row-2','status':'not_found','error':{'code':'NO_MATCH','message':'No object matches the query'}}],'workspace':'graubuenden','publication':None,'counts':{'found':1,'notFound':1,'ambiguous':0,'rejected':0}})+'''
`T-9999` is the reference data's deliberately unmapped **fictional** Regional ticketing code. The HTTP request succeeded, but the second source row has no answer. Keep its `not_found` outcome rather than replacing it with the first result. A malformed item is `rejected`; a tied best match is `ambiguous`. The response keeps input order and echoes each `ref`.

An item using `id` reads the known UUID directly and does not add a query score. Use one of `query` and `id` per item. For a whole file, follow [Resolve a file of codes](/docs/guide/integrate/resolve-a-file-of-codes/). The instance's [Resolve reference](/docs/api/?api=consumer-stops-v1#consumer-stops-v1/POST/api/consumer/stops/v1/resolve) remains the generated contract pointer.

These bodies use production-composed object values and the envelopes checked by the consumer code and journey assertions. The opaque anchor is illustrative, not a live resume token.

*Source: opentransportdata.swiss, Service Points (Didok), Federal Office of Transport / SBB, snapshot 2026-11-02. Wikidata, CC0. Regional ticketing and its codes are fictional.*
'''
p.write_text(s)
finish(['src/content/docs/integrate/looking-up-and-resolving.md'],'Applied steering: explained declared scoring and parameters with complete XREF, single-target crosswalk and two-row resolve request/response bodies. Checked J29 scoring, bare-single-object and batch outcome assertions. Reference values are production-composed; lookup envelopes and totals are derived, not live-captured.')
