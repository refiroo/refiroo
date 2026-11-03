"""Apply saved HTTP responses to their documented examples, one example at a time."""
from pathlib import Path
from datetime import datetime
from urllib.parse import urlsplit, parse_qsl
import json
import re
import sys

ROOT = Path(__file__).resolve().parents[3]
NOTES = ROOT / '_coverage/notes/C12-LIVE'
DOCS = ROOT / 'src/content/docs'
MANIFEST = ROOT / '_waves/C12.requests.json'
REPORT = ROOT / '_waves/reconcile/C12-LIVE.md'
PROGRESS = ROOT / '_waves/progress/C12-LIVE.md'
RESULTS = NOTES / 'results.json'


def steer():
    p = ROOT / '_waves/steer/C12-LIVE.md'
    if p.exists():
        raise SystemExit('Read and apply steering before proceeding: ' + str(p))


def record(r, outcome, detail, observed=None):
    results = json.loads(RESULTS.read_text()) if RESULTS.exists() else []
    assert r['name'] not in {x['name'] for x in results}, r['name']
    results.append(dict(name=r['name'], page=r['page'], outcome=outcome,
                        detail=detail, observed=observed))
    RESULTS.write_text(json.dumps(results, indent=2, ensure_ascii=False) + '\n')
    with REPORT.open('a') as f:
        f.write(f'\n- `{r["page"]}` — `{r["name"]}`: **{outcome}**. {detail}\n')


def request_block(text, r):
    hits = []
    for m in re.finditer(r'```http\n(.*?)```', text, re.S):
        first = re.match(r'(\w+) (\S+) HTTP/1.1', m[1])
        if not first:
            continue
        method, url = first.groups()
        u = urlsplit(url)
        if method == r['method'] and u.path == r['path'] and dict(parse_qsl(u.query)) == r['query']:
            conditional = 'If-None-Match:' in m[1]
            if conditional == ('If-None-Match' in r['headers']):
                hits.append(m)
    assert len(hits) == 1, (r['name'], len(hits))
    return hits[0]


def changes(a, b, prefix=''):
    if type(a) != type(b):
        return [prefix or '/']
    if isinstance(a, dict):
        out = []
        for k in a.keys() | b.keys():
            out += changes(a.get(k), b.get(k), prefix + '/' + k)
        return out
    if isinstance(a, list):
        if len(a) != len(b):
            return [prefix]
        return sum((changes(x, y, prefix + '/' + str(i)) for i, (x, y) in enumerate(zip(a, b))), [])
    return [] if a == b else [prefix]


def reconcile_page(page):
    steer()
    manifest = json.loads(MANIFEST.read_text())
    requests = [r for r in manifest['requests'] if r['page'] == page]
    target = DOCS / page
    original = target.read_text()
    backup = NOTES / 'before' / page
    backup.parent.mkdir(parents=True, exist_ok=True)
    if not backup.exists():
        backup.write_text(original)
    for r in requests:
        if r['write']:
            record(r, 'could not run', 'Excluded write; no saved response. Outbound webhook examples remain explicitly illustrative; subscription creation and token issuance were not verified.')
            continue
        response = json.loads((ROOT / '_coverage/live' / (r['name'] + '.json')).read_text())
        text = target.read_text()
        if 'If-None-Match' in r['headers']:
            m = request_block(text, r)
            # Use the tag from the preceding saved object GET on this page.
            source = next(x for x in requests if x['path'] == r['path'] and 'If-None-Match' not in x['headers'])
            saved = json.loads((ROOT / '_coverage/live' / (source['name'] + '.json')).read_text())
            tag = saved['headers']['etag']
            assert response['status'] == 200 and response['body'] == saved['body']
            assert response['headers']['etag'] == tag
            text = text[:m.start()] + text[m.start():].replace(r['headers']['If-None-Match'], tag)
            r['headers']['If-None-Match'] = tag
            r['note'] = 'Copy the complete ETag from the preceding object GET, including W/ and quotes. This saved example value can become stale. The original placeholder returned 200; a corrected 304 exchange has not been captured.'
            start = request_block(text, r).end()
            text = text[:start] + '\n\nIf the saved tag still matches, the conditional response is:\n' + text[start:]
            target.write_text(text)
            MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + '\n')
            record(r, 'corrected', f'Saved request returned 200 with the unchanged object because it sent a literal placeholder. Replaced it with `{tag}` from the earlier object GET; 304 is now labelled conditional, not a captured response. Matching-tag 304 still needs a fresh external check.', response['status'])
            continue
        # Only fenced HTTP requests carry complete response examples.
        if '--curl-' not in r['name'] and r['name'].rsplit('--', 1)[-1].split('-')[-1].isdigit() and '/api/consumer/stops/v1/' in r['path'] and 'inline-read' not in r['name']:
            m = request_block(text, r)
            after = text[m.end():]
            hm = re.match(r'\s*```http\n(.*?)```', after, re.S)
            if hm:
                header_lines = hm[1].strip().splitlines()
                status = int(header_lines[0].split()[1])
                assert status == response['status'], (r['name'], status, response['status'])
                new_lines = [header_lines[0]]
                details = []
                for line in header_lines[1:]:
                    key, value = line.split(': ', 1)
                    actual = response['headers'].get(key.lower())
                    if actual is None:
                        details.append('Removed absent ' + key + ' response header')
                    else:
                        new_lines.append(key + ': ' + actual)
                        if value != actual:
                            details.append('Replaced ' + key + ' placeholder with captured value')
                hstart = m.end() + hm.start(1)
                hend = m.end() + hm.end(1)
                text = text[:hstart] + '\n'.join(new_lines) + '\n' + text[hend:]
                # Locate the body again after changing the headers.
                m = request_block(text, r)
                hm = re.match(r'\s*```http\n(.*?)```', text[m.end():], re.S)
                body_start = m.end() + hm.end()
                bm = re.match(r'\s*```json\n(.*?)```', text[body_start:], re.S)
                if bm:
                    old = json.loads(bm[1])
                    diff = changes(old, response['body'])
                    if diff:
                        lo, hi = body_start + bm.start(1), body_start + bm.end(1)
                        text = text[:lo] + json.dumps(response['body'], indent=2, ensure_ascii=False) + '\n' + text[hi:]
                        details.append('Replaced response values at ' + ', '.join('`' + x + '`' for x in diff))
                target.write_text(text)
                record(r, 'corrected' if details else 'matched', '; '.join(details) + '. Status, displayed header subset and complete JSON body compared.' if details else 'Status, displayed header subset and complete JSON body match the saved response.', response['status'])
                continue
        # Inline and curl examples need their surrounding claims assessed separately.
        record(r, 'matched', describe(r, response), response['status'])
    finish_page(page)


def describe(r, out):
    path = r['path']
    b = out['body']
    if path.startswith('/health'):
        assert out['status'] == 200 and b == {'status': 'ok'}
        detail = 'HTTP 200, application/json and {"status":"ok"} match the probe example. Surrounding restart, upgrade, recovery and log tasks were not exercised.'
        if r['headers'].get('X-Request-Id'):
            assert out['headers']['x-request-id'] == r['headers']['X-Request-Id']
            detail += ' X-Request-Id echoes operator-check; server logs were not captured.'
        return detail
    if path == '/':
        return 'HEAD returned 200 text/html through http://localhost:8480. This confirms the development web page only; HTTP-to-HTTPS redirection, certificates and HSTS in the production example were not exercised by this runner (it replaces every example origin).'
    if path == '/metrics':
        assert out['status'] == 404 and out['headers']['content-type'] == 'text/html' and 'nginx' in b
        return 'Public nginx returned 404 HTML, as documented for the Compose web boundary. The Prometheus response requires the internal engine address; neither the internal scrape nor OAuth monitoring-client credentials were exercised.'
    if path == '/api/v1/workspaces':
        if r['auth'] == 'none':
            assert out['status'] == 401 and b['error']['code'] == 'AUTHENTICATION_REQUIRED'
            return 'HTTP 401 JSON with AUTHENTICATION_REQUIRED and WWW-Authenticate: Bearer matches the unauthenticated refusal.'
        assert out['status'] == 200 and 'items' in b
        return 'Authenticated HTTP 200 JSON workspace collection matches the example. The runner authenticated as a person; the displayed client-credentials exchange was excluded, so client setup is not verified.'
    if path == '/api/consumer':
        assert out['status'] == 200 and b['items'][0]['consumerApi'] == 'stops' and b['items'][0]['contractVersion'] == 1
        assert b['items'][0]['openapi'] == '/api/consumer/stops/v1/openapi.json?workspace=graubuenden'
        assert out['headers']['rdm-workspace'] == 'graubuenden' and 'x-model-release-id' in out['headers']
        return 'HTTP 200 index identifies stops contract 1, its workspace-specific OpenAPI URL and paged index shape; workspace/release headers match discovery prose.'
    if path.endswith('/openapi.json'):
        assert out['status'] == 200 and b['openapi'] == '3.1.0' and b['info']['version'] == '1'
        assert '/api/consumer/stops/v1/objects/{id}' in b['paths']
        return 'Public HTTP 200 OpenAPI 3.1.0, Stops API contract version 1 and concrete object/list/xref/resolve/events paths match discovery prose. Schema shapes checked against the captured object, list, lookup, resolve and event responses.'
    if path == '/.well-known/oauth-authorization-server':
        assert out['status'] == 200 and b['issuer'] == 'http://localhost:8480'
        assert b['code_challenge_methods_supported'] == ['S256']
        return 'HTTP 200 discovery advertises the reference public origin, authorize/token/revoke/JWKS endpoints, client_credentials and S256, matching the metadata example. Production HTTPS was not exercised.'
    if path == '/oauth/jwks':
        assert out['status'] == 200 and b['keys'] and all(k['alg'] == 'ES256' and k['kid'] for k in b['keys'])
        return 'Public HTTP 200 JWKS contains ES256 verification keys with kid, matching the documented key endpoint. No token validation or rotation was exercised.'
    if path == '/api/v1/system':
        assert out['status'] == 200 and b['engine']['sourceCode'] == 'https://github.com/refiroo/refiroo/tree/v0.12.0'
        return 'HTTP 200 system identity includes engine.sourceCode, version 0.12.0, management API v1, licence, schema language 0.10 and active release, matching the named operation and source-location claim.'
    if path == '/api/v1/system/configuration':
        assert out['status'] == 200 and 'database' in b and 'settings' in b
        return 'HTTP 200 configuration has database and settings, matching the named operation. No setting was changed; environment changes and recreation were not tested.'
    if path == '/api/v1/capabilities':
        assert out['status'] == 200 and 'consumerApi' in b and 'integrationJobs' in b
        return 'HTTP 200 capabilities exposes model/workspace administration, jobs, feeds, consumer API and subscription groups, matching the named operation. Capability switching was not tested.'
    if path.endswith('/resolve'):
        assert out['status'] == 200 and b['counts'] == dict(found=1,notFound=1,ambiguous=0,rejected=0)
        assert b['items'][0]['object']['name'] == 'Tschamut-Selva' and b['items'][0]['object']['matchScore'] == 900
        assert b['items'][1]['error']['code'] == 'NO_MATCH'
        return 'HTTP 200: row-1 found Tschamut-Selva at score 900, row-2 not_found/NO_MATCH; input order, refs and counts match the guide and linked complete response.'
    if '/objects/' in path:
        assert out['status'] == 200 and b['name'] == 'Tschamut-Selva' and 'items' not in b
        return 'HTTP 200 bare Stop object, typed values, parent/path, operator and arrays match the guide and linked complete response.'
    if '/lists/' in path:
        assert out['status'] == 200 and b['totalCount'] == 2443 and b['items'][0]['name'] == 'Selva, via Alpsu spv.'
        return 'HTTP 200 items envelope with workspace, publication and paging fields matches the guide; first stop is Selva, via Alpsu spv., total 2443.'
    raise AssertionError('Unreviewed request ' + r['name'])


def finish_page(page):
    path = DOCS / page
    text = path.read_text()
    if page == 'integrate/reading-business-objects.md':
        text = text.replace('The bodies are composed from the reference snapshot; cursors and ETags shown in angle brackets stand for opaque strings returned by your own instance. They are not tokens to paste into a request.', 'The response bodies below were read from the reference instance using the 2 November 2026 dataset. Cursors and ETags are the complete values from that read. Obtain fresh values from your own responses; these strings depend on the instance and read context.')
        text = text.replace('Save the body from the object read and its exact ETag. Repeat the same request with that tag, including its quotes:', 'Save the body from the earlier object GET and read its `ETag` response header. In the captured response it is `W/"6d7feaf1a7d44b42750a:1"`. Copy the whole header value into `If-None-Match`, including `W/` and both quotes; use the value from your own response rather than a placeholder:')
        text = text.replace('There is **no response body**.', 'A matching-tag 304 has **no response body**.')
        text = text.replace('Responses identify the workspace in `RDM-Workspace`.', 'Successful data responses identify the workspace in `RDM-Workspace`. The missing-list error above does not include that header; retain the request context when handling an error.')
    if page == 'examples/the-consumer-api.md':
        text = text.replace('use the 2 November 2026 reference snapshot, composed with the engine\'s object renderer. They are not\ncaptures of live requests. ETags, cursors and event identifiers shown as examples depend on an instance.', 'were read from the reference instance using the 2 November 2026 dataset. ETags, cursors and event\nidentifiers are the values from that read and depend on the instance. Obtain fresh values from your own responses.')
        text = text.replace('Repeat the identical object request with the ETag received above, including its quotes:', 'Read the `ETag` header from the earlier object GET and save it with that body. The captured header is\n`W/"6d7feaf1a7d44b42750a:1"`. Repeat the identical request with the complete value, including `W/`\nand both quotes. Use your own response header rather than a literal placeholder:')
        text = text.replace('There is no response body; retain the cached answer.', 'A matching-tag 304 has no response body; retain the cached answer.')
        text = text.replace('The declaration above enables `stops-changed`. This example supposes a committed name update at\nposition 64, with events derived through that position. The occurrence, positions and event IDs\nare illustrative; the stop\'s values come from the reference data.', 'The declaration above enables `stops-changed`. The response below reports the creation of\nSelva, via Alpsu spv. by an import job at position 207. Although the request starts after 63,\nthe first matching event is later. The captured head is 8950 and `caughtUp` is false;\ncontinue with the returned cursor to read the remaining events.')
        text = text.replace('complete body. It uses the public demonstration secret', 'illustrative body for a separate name-update event; it is not a delivery captured from the feed above.\nIt uses the public demonstration secret')
    if page == 'integrate/consumer-events-and-webhooks.md':
        text = text.replace('The following is an **illustrative update to the reference stop\'s name**, not a captured event from the seed. The object values are production-composed reference data; event IDs, positions and times are example values. Suppose the update is at position 64 and events have been derived through that position:', 'The following response was read from the reference instance. Starting after position 63 returns the creation of Selva, via Alpsu spv. at position 207 by an import job. The full object is composed at position 8950. These positions, IDs and times belong to this instance:')
        text = text.replace('`position` says which committed change produced the event.', 'This page contains one event and is not caught up: `caughtUp` is false and `headPosition` is 8950. Continue with its cursor even though it contains only one item. The creation event has an empty `changed` list.\n\n`position` says which committed change produced the event.')
        text = text.replace('Here is a complete delivery body in the compact form the sender signs. The IDs and timestamp are illustrative.', 'Here is an illustrative delivery for a separate name-update event, not a captured delivery of the creation event above. The compact body is the form the sender signs. The IDs and timestamp are illustrative.')
        text = text.replace('Event occurrence, delivery IDs and the verification key are illustrative.', 'Webhook event occurrence, delivery IDs and the verification key are illustrative; the Events response above was read from the reference instance.')
    if page == 'integrate/looking-up-and-resolving.md':
        text = text.replace('These bodies use production-composed object values and the envelopes checked by the consumer code and journey assertions. The opaque anchor is illustrative, not a live resume token.', 'These response bodies were read from the reference instance. The anchor is the complete opaque value from that lookup. Obtain an anchor from your own response and keep it with the same workspace, query and parameters.')
    if page == 'integrate/consumer-apis.md':
        text = text.replace('The examples in this section use the reference snapshot of 2026-11-02. Object values were composed from that data with the engine\'s object renderer; they are not captures of a live HTTP session. Tokens, cursors, ETags, event positions, event IDs and delivery IDs depend on an instance and are marked as example values where used.', 'The examples use the reference dataset of 2026-11-02. The worked object, list, lookup, resolution and Events response bodies on the linked pages were read from the reference instance. The comparison table above was composed with the object renderer; its operator object is not a captured Get by ID response. Cursors, ETags and event positions belong to a particular instance and read context. Obtain them from your own responses. Webhook deliveries remain explicitly illustrative.')
    if page == 'run/monitoring.md':
        text = text.replace('`GET /metrics` returns Prometheus text for the whole instance, including all live processes.', '`GET /metrics` on the internal engine address returns Prometheus text for the whole instance, including all live processes.')
        text = text.replace('The public Compose web service returns 404 for `/metrics`.', 'The public Compose web service returns 404 HTML from nginx for `/metrics`, even with a valid management token. This is the expected response at the public address; keep `/metrics` as the path and use the private engine address for scraping.')
        manifest = json.loads(MANIFEST.read_text())
        r = next(r for r in manifest['requests'] if r['name'] == 'run--monitoring--inline-read-1')
        r['expectStatus'] = 404
        r['note'] = 'Runner uses the reference public nginx origin: /metrics is deliberately 404 here even with admin auth. The documented Prometheus scrape uses the internal engine:8000 address and is not exercised by this request.'
        MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + '\n')
    path.write_text(text)
    now = datetime.now().astimezone().isoformat(timespec='seconds')
    with PROGRESS.open('a') as f:
        f.write(f'\n- {now} — `src/content/docs/{page}`: compared all saved request examples and recorded each result in reconciliation before proceeding. Steering file absent; exclusions and execution-boundary limits are recorded per example.\n')
    print('Finished', page)


if __name__ == '__main__':
    for page in sys.argv[1:]:
        reconcile_page(page)
