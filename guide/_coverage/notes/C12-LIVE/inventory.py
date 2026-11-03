"""Inventory documented requests only; never contacts an instance."""
from pathlib import Path
from datetime import datetime
from urllib.parse import urlsplit, parse_qsl
import json
import re
import shlex

ROOT = Path(__file__).resolve().parents[3]
DOCS = ROOT / 'src/content/docs'
MANIFEST = ROOT / '_waves/C12.requests.json'
PROGRESS = ROOT / '_waves/progress/C12-LIVE.md'
RECONCILE = ROOT / '_waves/reconcile/C12-LIVE.md'
STEER = ROOT / '_waves/steer/C12-LIVE.md'


def steering():
    if STEER.exists():
        raise SystemExit('Steering now exists; read it before continuing: ' + str(STEER))


def entry(page, line, label, method, url, headers=None, body=None, auth=None):
    parsed = urlsplit(url)
    path = parsed.path
    result = {
        'name': page.removesuffix('.md').replace('/', '--') + '--' + label,
        'auth': auth or ('consumer' if path.startswith('/api/consumer') else
                         'admin' if path.startswith('/api/v1') else 'none'),
        'method': method,
        'path': path,
        'query': dict(parse_qsl(parsed.query, keep_blank_values=True)),
        'headers': headers or {},
        'body': body,
        'write': method not in ('GET', 'HEAD', 'OPTIONS') and not path.endswith('/resolve'),
        'page': page,
        'line': line,
    }
    if parsed.hostname:
        result['exampleOrigin'] = f'{parsed.scheme}://{parsed.netloc}'
    return result


def save(page, entries, explanation):
    steering()
    manifest = json.loads(MANIFEST.read_text())
    names = {r['name'] for r in manifest['requests']}
    if any(r['name'] in names for r in entries):
        raise SystemExit('Examples already inventoried: ' + page)
    manifest['requests'].extend(entries)
    MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + '\n')
    with RECONCILE.open('a') as f:
        f.write(f'\n## {page}\n\n')
        if not entries:
            f.write('No concrete request example to run. ' + explanation + '\n')
        for r in entries:
            reason = ('Write or outbound webhook: excluded from execution.' if r['write'] else
                      'Reference instance unavailable from the sandbox; awaiting external run.')
            if 'If-None-Match' in r['headers']:
                reason += ' Replace the documented ETag placeholder with the tag from the preceding GET before running.'
            f.write(f'- `{r["name"]}` (line {r["line"]}): **could not run**. {reason}\n')
    now = datetime.now().astimezone().isoformat(timespec='seconds')
    with PROGRESS.open('a') as f:
        f.write(f'\n- {now} — `src/content/docs/{page}`: inventoried {len(entries)} requests. '
                + explanation + ' Steering file absent; no corrections to apply.\n')
    print(page, len(entries))


def http_pages():
    for p in sorted(DOCS.rglob('*.md')):
        text = p.read_text()
        blocks = list(re.finditer(r'^```([^\n]*)\n(.*?)^```', text, re.M | re.S))
        entries = []
        for block in blocks:
            match = re.match(r'(GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS) (\S+) HTTP/1\.1\n', block[2])
            if not match:
                continue
            method, url = match.groups()
            header_text, _, raw_body = block[2][match.end():].partition('\n\n')
            headers = dict(line.split(': ', 1) for line in header_text.strip().splitlines())
            # Authentication and the instance host are supplied by the external runner.
            headers.pop('Authorization', None)
            host = headers.pop('Host', None)
            line = text[:block.start()].count('\n') + 2
            body = json.loads(raw_body) if raw_body.strip() else None
            before = text[:block.start()]
            headings = re.findall(r'^#{1,6} (.+)$', before, re.M)
            label = re.sub(r'[^a-z0-9]+', '-', headings[-1].lower()).strip('-') if headings else 'request'
            label += '-' + str(len(entries) + 1)
            r = entry(str(p.relative_to(DOCS)), line, label, method, url, headers, body,
                      'none' if host == 'receiver.example' else None)
            if host == 'receiver.example':
                r['exampleHost'] = host
            following = text[block.end():]
            status = re.match(r'\s*```http\nHTTP/1\.1 (\d+)', following)
            if status:
                r['expectStatus'] = int(status[1])
            elif method == 'POST' and url == '/api/v1/consumer-subscriptions':
                r['expectStatus'] = 201
            entries.append(r)
        if entries:
            save(str(p.relative_to(DOCS)), entries,
                 'Preserved the displayed queries, headers and JSON bodies; response comparison awaits the external run.')


def curl_pages():
    for p in sorted(DOCS.rglob('*.md')):
        text = p.read_text()
        entries = []
        # Includes indented numbered-step fences as well as top-level fences.
        for block in re.finditer(r'^[ \t]*```(?:bash|sh|shell)\n(.*?)^[ \t]*```', text, re.M | re.S):
            commands = block[1].replace('\\\n', ' ')
            for command in commands.splitlines():
                if not command.strip().startswith('curl '):
                    continue
                tokens = shlex.split(command.strip())
                url = next(t for t in tokens if t.startswith(('http://', 'https://')))
                method = 'HEAD' if '-I' in tokens else 'GET'
                headers = {}
                auth = 'none'
                body = None
                for i, token in enumerate(tokens):
                    if token in ('-H', '--header'):
                        key, value = tokens[i + 1].split(': ', 1)
                        if key.lower() == 'authorization':
                            auth = 'admin'
                        else:
                            headers[key] = value
                    if token in ('-d', '--data'):
                        method = 'POST'
                        body = tokens[i + 1]
                        headers['Content-Type'] = 'application/x-www-form-urlencoded'
                line = text[:block.start()].count('\n') + 1
                label = 'curl-' + str(len(entries) + 1)
                r = entry(str(p.relative_to(DOCS)), line, label, method, url, headers, body, auth)
                if '-u' in tokens:
                    r['headers']['Authorization'] = 'Basic <base64(CLIENT_ID:CLIENT_SECRET)>'
                    r['credentialRequired'] = True
                if r['path'] == '/metrics':
                    r['expectStatus'] = 404
                elif r['path'] == '/api/v1/workspaces' and auth == 'none':
                    r['expectStatus'] = 401
                elif r['path'].startswith('/health'):
                    r['expectStatus'] = 200
                entries.append(r)
        if entries:
            save(str(p.relative_to(DOCS)), entries,
                 'Included each curl example, including repeated recovery probes; public proxy and TLS checks require the documented caller network.')


if __name__ == '__main__':
    import sys
    {'http': http_pages, 'curl': curl_pages}[sys.argv[1]]()
