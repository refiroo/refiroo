# Uncovered inventory entries

Written by `node tools/check.mjs coverage`. 20 of 911 entries.

## use (7)

### screen (7)

- `route:list` (frontend/src/types/ui.ts:46)
- `route:detail` (frontend/src/types/ui.ts:56)
- `route:changeSetChanges` (frontend/src/types/ui.ts:73)
- `route:group` (frontend/src/types/ui.ts:92)
- `settings:ai-tasks` (frontend/src/types/ui.ts:153)
- `confirm:NotificationsPage.tsx:Delete read notifications` — "Delete all read notifications?", "Delete read notifications" (frontend/src/features/inbox/NotificationsPage.tsx:331)
- `confirm:DeleteAction.tsx:dialog` (frontend/src/features/settings/DeleteAction.tsx:53)

## integrate (13)

### consumer-api (12)

- `GET /api/consumer/{consumer_api}/v{contract_version}/objects/{object_id}` — "/api/consumer/{consumer_api}/v{contract_version}/objects/{object_id}" (backend/app/consumer/router.py:281)
- `GET /api/consumer/{consumer_api}/v{contract_version}/lists/{list_key}` — "/api/consumer/{consumer_api}/v{contract_version}/lists/{list_key}" (backend/app/consumer/router.py:314)
- `GET /api/consumer/{consumer_api}/v{contract_version}/xref` — "/api/consumer/{consumer_api}/v{contract_version}/xref" (backend/app/consumer/router.py:361)
- `POST /api/consumer/{consumer_api}/v{contract_version}/resolve` — "/api/consumer/{consumer_api}/v{contract_version}/resolve" (backend/app/consumer/router.py:406)
- `GET /api/consumer/{consumer_api}/v{contract_version}/publications` — "/api/consumer/{consumer_api}/v{contract_version}/publications" (backend/app/consumer/router.py:446)
- `GET /api/consumer/{consumer_api}/v{contract_version}/events` — "/api/consumer/{consumer_api}/v{contract_version}/events" (backend/app/consumer/router.py:479)
- `GET /api/consumer/{consumer_api}/v{contract_version}/openapi.json` — "/api/consumer/{consumer_api}/v{contract_version}/openapi.json" (backend/app/consumer/router.py:688)
- `GET /api/consumer/stops/v1/lists/municipalities` — "/api/consumer/stops/v1/lists/municipalities": List municipalities (guide/samples/model.json (consumer_openapi, api 'stops'))
- `GET /api/consumer/stops/v1/lists/stops` — "/api/consumer/stops/v1/lists/stops": List stops (guide/samples/model.json (consumer_openapi, api 'stops'))
- `GET /api/consumer/stops/v1/lists/operators` — "/api/consumer/stops/v1/lists/operators": List operators (guide/samples/model.json (consumer_openapi, api 'stops'))
- `GET /api/consumer/stops/v1/lists/modes` — "/api/consumer/stops/v1/lists/modes": List modes (guide/samples/model.json (consumer_openapi, api 'stops'))
- `GET /api/consumer/stops/v1/publications` — "/api/consumer/stops/v1/publications": Publications (guide/samples/model.json (consumer_openapi, api 'stops'))

### mcp-tool (1)

- `read_resource` (backend/app/management/mcp_tools.py:1058)
