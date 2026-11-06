"""One scratch tool for the fifth-round fixtures, extended with subcommands (backend/.venv python).
Secrets stay out of output. Usage: fixtures.py <command> [args]"""
import json, sys, os, time
from pathlib import Path
from hashlib import sha256
from uuid import UUID
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'samples'))
import load  # noqa
HERE = Path(__file__).resolve().parent
ENV = load.read_env(HERE.parents[2] / 'reference' / '.env')
BASE = 'http://localhost:8480'


def api():
    a = load.Api(load.urllib_send(BASE), BASE, ENV['GUIDE_ADMIN_USERNAME'], ENV['GUIDE_ADMIN_PASSWORD'],
                 log=lambda t: print(t, flush=True))
    a.login()
    return a


def pj(x, n=6000):
    print(json.dumps(x, indent=1, ensure_ascii=False, default=str)[:n])


def cmd_get(a, path):
    pj(a.call('GET', path))


PD = HERE / 'picture-data'
WORKSPACES = {
    'c10-workbook-pictures': 'C10 workbook pictures', 'c10-words-pictures': 'C10 words pictures',
    'c10-whole-move-pictures': 'C10 whole move pictures', 'c10-partial-move-pictures': 'C10 partial move pictures',
    'c10-mapping-pictures': 'C10 mapping pictures', 'c10-history-pictures': 'C10 history pictures',
    'c10-jobs-pictures': 'C10 jobs pictures', 'c10-import-pictures': 'C10 import pictures',
    'c10-webhook-pictures': 'C10 webhook pictures',
}


def cmd_workspaces(a, *only):
    """Fixture 1: load the nine isolated copies of the docs set; the default workspace is never switched."""
    orig = a.call

    def call(method, path, body=None, ok=(200, 201, 202, 204), headers=None):
        if method == 'PATCH' and path == '/api/v1/workspace-runtime-state':
            return orig('GET', path)
        return orig(method, path, body, ok, headers)
    a.call = call
    for key, label in WORKSPACES.items():
        if only and key not in only:
            continue
        load.WORKSPACE, load.LABEL, load.DATA = key, label, PD / key
        print(f'== {key}')
        load.load_set(a, 'docs', changeset=False, client_name=None)


def cmd_newws(a, key, label):
    """Sixth capture: one more isolated docs-set copy (remapped for `key`), default workspace untouched."""
    import importlib.util
    spec = importlib.util.spec_from_file_location('prep', HERE / 'prepare-picture-data.py')
    prep = importlib.util.module_from_spec(spec); spec.loader.exec_module(prep)
    target = PD / key / 'docs'
    target.mkdir(parents=True, exist_ok=True)
    for source in (HERE.parents[2] / 'samples' / 'data' / 'docs').glob('*.json'):
        target.joinpath(source.name).write_text(json.dumps(prep.remap(json.loads(source.read_text()), key), ensure_ascii=False) + '\n')
    WORKSPACES[key] = label
    cmd_workspaces(a, key)


def remap(ws, value):
    return str(UUID(bytes=sha256(f'guide:C10:{ws}:{value}'.encode()).digest()[:16], version=4))


def cmd_matchcodes(a):
    """Fixture 2: two fictional C10-MATCH system codes in c10-mapping-pictures, no mappings."""
    ws = 'c10-mapping-pictures'
    parent = remap(ws, '7569eaad-7028-4abe-bc62-0d59558d1e6a')
    items = []
    for n, stop in ((1, 'Chur Wiesental'), (2, 'Chur West')):
        rid = str(UUID(bytes=sha256(f'guide:C10:C10-MATCH:{n}'.encode()).digest()[:16], version=4))
        name = f'C10-MATCH {stop}'
        items.append(load.upsert('systems', 'system-code', rid, name,
                                 load.attrs(external_id=name, description=f'FICTIONAL guide code for the stop {stop}'), parent))
        print(name, rid)
    job = a.batch('match codes', items, {'workspaceKey': ws}, None, 'overwrite')
    print('job', job['id'])


STOPS_CHECKER = '235f0ca1-92dd-4621-9bab-f5e140815464'


def agent_token(a, client_id=STOPS_CHECKER):
    """Rotate the fictional client's secret in memory only and answer an agent-audience token."""
    c = a.call('GET', f'/api/v1/clients/{client_id}')
    out = a.call('POST', f'/api/v1/clients/{client_id}/secrets', {'expectedVersion': c['version'], 'overlapHours': 0})
    st, tok = a.raw('POST', '/oauth/token', form={'grant_type': 'client_credentials', 'client_id': client_id,
                                                  'client_secret': out['secret'], 'scope': 'agent'}, auth=False)
    if st != 200:
        raise SystemExit(f'token refused: {st} {str(tok)[:300]}')
    return tok['access_token']


def cmd_mcphistory(a):
    """Fixture 3: grant, then real MCP calls: create, change, validate and submit a change set (never publish)."""
    import asyncio
    from mcp import ClientSession
    from mcp.client.streamable_http import streamablehttp_client
    ws = 'c10-history-pictures'
    roles = a.call('GET', '/api/v1/roles')['items']
    role = next(r for r in roles if r['key'] == 'steward')
    grants = a.call('GET', f'/api/v1/grants?pageSize=200')['items']
    have = [g for g in grants if g.get('principal', {}).get('id') == STOPS_CHECKER and g.get('scope', {}).get('workspaceKey') == ws]
    if not have:
        g = a.call('POST', '/api/v1/grants', {'principal': {'kind': 'client', 'id': STOPS_CHECKER}, 'role': role['key'], 'scope': {'workspaceKey': ws}})
        print('grant', g['id'])
    tok = agent_token(a)

    async def run():
        async with streamablehttp_client(BASE + '/mcp', headers={'Authorization': 'Bearer ' + tok}) as (r, w, _):
            async with ClientSession(r, w) as s:
                await s.initialize()

                async def call(name, args):
                    res = await s.call_tool(name, args)
                    text = res.content[0].text if res.content else ''
                    print(name, 'ERROR' if res.isError else 'ok', text[:300].replace('\n', ' '))
                    if res.isError:
                        raise SystemExit(1)
                    return json.loads(text)
                cs = await call('create_change_set', {'workspace': ws, 'name': 'C10 assistant history'})
                found = await call('find_records', {'workspace': ws, 'objectTypeKey': 'stop', 'where': [{'field': 'name', 'op': 'eq', 'value': 'Chur Wiesental'}]})
                items = found.get('items') or found.get('records') or []
                stop = next(i for i in items if i['name'] == 'Chur Wiesental')
                ch = await call('change_record', {'changeSetId': cs['changeSetId'], 'expectedChangeSetVersion': cs['version'], 'objectType': 'stop',
                                                  'id': stop['id'], 'expectedVersion': stop['version'],
                                                  'attributes': [{'attributeTypeKey': 'abbreviation', 'value': 'C10-MCP'}]})
                await call('validate_change_set', {'changeSetId': cs['changeSetId']})
                sub = await call('submit_change_set', {'changeSetId': cs['changeSetId'], 'expectedChangeSetVersion': ch['changeSetVersion'],
                                                       'comment': 'Prepared for the guide; ready for human review'})
                print('change set', cs['changeSetId'], 'submission', sub)
    asyncio.run(run())


LANG_RELEASE = 'c10-language-picture-model'
COMPOSE = ['docker', 'compose', '-p', 'refiroo-guide-ref', '-f', str(HERE.parents[3] / 'compose.yml'),
           '-f', str(HERE.parents[2] / 'reference' / 'compose.override.yml'),
           '--env-file', str(HERE.parents[2] / 'reference' / '.env')]


def cmd_language(a, step='make'):
    """Fixture 6: step make = release+workspace, then rewrite the stored schema to 0.9 (outside-API); step preview."""
    import subprocess
    if step == 'make':
        rel = [r for r in a.call('GET', f'/api/v1/model-releases?releaseKey={LANG_RELEASE}&pageSize=50')['items']]
        if not rel:
            m = json.loads((HERE.parents[2] / 'samples' / 'model.json').read_text())
            m['release'].update(key=LANG_RELEASE, name='Guide language example', version='1.0.0')
            d = a.call('POST', '/api/v1/model-drafts', {'name': 'Guide language example', 'model': m})
            rel = [a.call('POST', f"/api/v1/model-drafts/{d['id']}/installation", {'expectedVersion': d['version']})]
        rid = rel[0]['id']
        print('release', rid)
        st, ws = a.raw('GET', '/api/v1/workspaces/c10-language-pictures')
        if st == 404:
            ws = a.call('POST', '/api/v1/workspaces', {'key': 'c10-language-pictures', 'label': 'C10 language pictures', 'modelReleaseId': rid})
        print('workspace', ws['key'], ws.get('model', {}).get('releaseKey'), ws.get('state') or ws.get('status'))
        code = f"""
import json, hashlib
from sqlalchemy import select
from app.db import SessionLocal
from app.models.database import ModelRelease, WorkspaceModel
with SessionLocal() as s:
    r = s.scalar(select(ModelRelease).where(ModelRelease.public_id == '{rid}').with_for_update())
    assert r.release_key == '{LANG_RELEASE}', r.release_key
    users = s.execute(select(WorkspaceModel)).scalars().all()
    mine = [u for u in users if u.model_release_id == r.id]
    print('assignments', [u.workspace_key for u in mine])
    assert [u.workspace_key for u in mine] == ['c10-language-pictures']
    m = json.loads(json.dumps(r.model_json)); m['schemaVersion'] = '0.9'
    r.schema_version = '0.9'; r.model_json = m
    r.model_hash = hashlib.sha256(json.dumps(m, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    s.commit(); print('rewritten', r.schema_version)
"""
        out = subprocess.run(COMPOSE + ['exec', '-T', 'engine', 'python', '-c', code], capture_output=True, text=True)
        print(out.stdout, out.stderr[-1500:])
    ws = a.call('GET', '/api/v1/workspaces/c10-language-pictures')
    pj({k: ws.get(k) for k in ('key', 'state', 'status', 'unavailable', 'reason', 'raisable', 'model')})


def cmd_export(a):
    """Fixture 8: For people XLSX export of c10-import-pictures, Height of the first data row made text."""
    import openpyxl, urllib.request
    body = {'workspaceKey': 'c10-import-pictures', 'context': {}, 'scope': {'types': [{'objectTypeKey': 'stop', 'where': []}]},
            'include': {'relations': 'none'}, 'format': 'xlsx', 'layout': 'people',
            'people': {'columns': ['name', 'designation', 'stop-number', 'height'], 'sheets': []}}
    job = a.call('POST', '/api/v1/exports', body)
    job = a.wait_job(job['id'], 'export')
    print('export job', job['id'], job['state'], job.get('counts'))
    req = urllib.request.Request(BASE + f"/api/v1/jobs/{job['id']}/output", headers={'Authorization': 'Bearer ' + a.token})
    raw = HERE / 'import-original.xlsx'
    raw.write_bytes(urllib.request.urlopen(req).read())
    wb = openpyxl.load_workbook(raw)
    print([(w.title, w.sheet_state, w.max_row, w.max_column) for w in wb.worksheets])
    ws = next(w for w in wb.worksheets if w.sheet_state == 'visible')
    for row in ws.iter_rows(min_row=1, max_row=4):
        print([c.value for c in row])
    hdr = next(r for r in range(1, 10) if any(str(c.value or '').startswith('Height') for c in ws[r]))
    col = next(c.column for c in ws[hdr] if str(c.value or '').startswith('Height'))
    cell = ws.cell(row=hdr + 1, column=col)
    print('header row', hdr, 'height col', col, 'was', cell.value)
    cell.value = 'not a number'
    wb.save(HERE / 'import-invalid-height.xlsx')
    raw.unlink()


def stop_of(a, ws, name='Chur Wiesental'):
    r = a.call('GET', f'/api/v1/objects/stop?workspaceKey={ws}&search={name.replace(" ", "%20")}&pageSize=5')
    return next(i for i in r['items'] if i['name'].startswith(name))


def rename(a, ws, new):
    o = stop_of(a, ws)
    out = a.call('PATCH', f"/api/v1/objects/stop/{o["id"]}", {'name': new, 'expectedVersion': o['version']})
    print('renamed ->', new, 'version', out['version'])


def receiver(mode):
    import subprocess
    subprocess.run(COMPOSE + ['exec', '-T', 'guide-webhook-receiver', 'sh', '-c', f'echo {mode} > /state/mode'], check=True)
    print('receiver mode', mode)


def deliveries(a, sid):
    return a.call('GET', f'/api/v1/consumer-subscriptions/{sid}/deliveries?pageSize=20')['items']


def cmd_webhook(a, step, sid=''):
    """Fixture 9. steps: create | one | fail | two | show SID | accept | resume SID | restore | suspend SID"""
    ws = 'c10-webhook-pictures'
    if step == 'create':
        receiver('accept')
        body = {'name': 'C10 retrying receiver', 'source': 'consumerApi', 'consumerApi': 'stops', 'workspaceKey': ws,
                'events': ['stops-changed'], 'filters': {}, 'url': 'http://127.0.0.1:8099/events', 'maxEventsPerBatch': 1,
                'payload': 'identity', 'format': 'rdm'}
        out = a.call('POST', '/api/v1/consumer-subscriptions', body)
        print('subscription', out['id'], 'state', out.get('state'), 'version', out.get('version'))  # the signing key is not printed
    elif step == 'one':
        rename(a, ws, 'Chur Wiesental — guide delivery 1')
    elif step == 'fail':
        receiver('fail')
    elif step == 'two':
        rename(a, ws, 'Chur Wiesental — guide delivery 2')
    elif step == 'show':
        for d in deliveries(a, sid):
            print({k: d.get(k) for k in ('id', 'state', 'attempts', 'status', 'lastStatus', 'responseStatus', 'nextAttemptAt')})
        pj({k: v for k, v in a.call('GET', f'/api/v1/consumer-subscriptions/{sid}').items() if k not in ('secret', 'signingKey')}, 1800)
    elif step == 'accept':
        receiver('accept')
    elif step == 'resume':
        sub = a.call('GET', f'/api/v1/consumer-subscriptions/{sid}')
        out = a.call('POST', f'/api/v1/consumer-subscriptions/{sid}/resume', {'expectedVersion': sub['version'], 'reset': False})
        print('resumed', out.get('state'))
    elif step == 'suspend':
        sub = a.call('GET', f'/api/v1/consumer-subscriptions/{sid}')
        out = a.call('POST', f'/api/v1/consumer-subscriptions/{sid}/suspend', {'expectedVersion': sub['version']})
        print('suspended', out.get('state'))
    elif step == 'restore':
        rename(a, ws, 'Chur Wiesental')


SCRATCH = Path('/private/tmp/claude-502/-Users-krisztian-Documents-Projects-rdm-engine/bd43701d-2cdd-48e1-8749-15e7f39afb9e/scratchpad')


def user_of(a, username):
    return next(u for u in a.call('GET', f'/api/v1/users?q={username}&pageSize=20')['items'] if u['username'] == username)


def cmd_device(a, step):
    """Fixture 11 (private files in the scratchpad). steps: password | totp | list"""
    import secrets, hmac, hashlib, struct, base64, urllib.parse
    u = user_of(a, 'c10-device-person')
    pwfile = SCRATCH / 'device.pw'
    if step == 'password':
        link = a.call('POST', f"/api/v1/users/{u['id']}/password-reset", {})
        token = urllib.parse.parse_qs(urllib.parse.urlparse(link['url']).query)['token'][0]
        pw = secrets.token_urlsafe(18) + 'aA1!'
        import urllib.request
        req = urllib.request.Request(BASE + '/oauth/password', data=urllib.parse.urlencode({'token': token, 'password': pw, 'repeat': pw}).encode(),
                                     method='POST', headers={'Origin': BASE, 'Content-Type': 'application/x-www-form-urlencoded'})
        try:
            st = urllib.request.urlopen(req).status
        except urllib.error.HTTPError as e:
            st = e.code
        print('password form status', st)
        if st == 200:
            pwfile.write_text(pw); pwfile.chmod(0o600)
    elif step == 'totp':
        pw = pwfile.read_text()
        b = load.Api(load.urllib_send(BASE), BASE, 'c10-device-person', pw, log=lambda t: None)
        b.login()
        enrol = b.call('POST', '/api/v1/me/second-factor', {})
        key = base64.b32decode(enrol['secret'] + '=' * (-len(enrol['secret']) % 8))
        step_n = int(time.time()) // 30
        mac = hmac.new(key, struct.pack('>Q', step_n), hashlib.sha1).digest()
        o = mac[-1] & 15
        code = f"{(struct.unpack('>I', mac[o:o+4])[0] & 0x7FFFFFFF) % 10**6:06d}"
        (SCRATCH / 'device.totp').write_text(enrol['secret']); (SCRATCH / 'device.totp').chmod(0o600)
        b.call('POST', '/api/v1/me/second-factor/confirmation', {'code': code})  # recovery codes dropped unread
        print('second factor', b.call('GET', '/api/v1/me/second-factor'))
    elif step == 'unpasskey':
        for pk in a.call('GET', f"/api/v1/users/{u['id']}/passkeys")['items']:
            a.call('DELETE', f"/api/v1/users/{u['id']}/passkeys/{pk['id']}")
        print('passkeys removed (to be registered again after the authenticator app)')
    elif step == 'list':
        print('passkeys', [p['name'] for p in a.call('GET', f"/api/v1/users/{u['id']}/passkeys")['items']])


def cmd_oidc(a, step):
    """Fixture 10 provider. steps: save | show | local (state of the local provider) | restore-local"""
    if step == 'save':
        secret = (SCRATCH / 'oidc.client_secret').read_text().strip()
        body = {'key': 'guide-oidc', 'name': 'Guide identity provider', 'issuer': 'http://localhost:8491/realms/guide',
                'clientId': 'refiroo-guide', 'clientSecret': secret, 'groupsClaim': 'groups', 'enabled': True, 'signOutOfProvider': True}
        out = a.call('POST', '/api/v1/sign-in-providers', body)
        print({k: v for k, v in out.items() if 'ecret' not in k})
    elif step == 'show':
        out = a.call('GET', '/api/v1/sign-in-providers/guide-oidc')
        print({k: v for k, v in out.items() if 'ecret' not in k})
    elif step == 'local':
        out = a.call('GET', '/api/v1/sign-in-providers/local')
        pj(out, 1500)
    elif step == 'restore-local':
        cur = a.call('GET', '/api/v1/sign-in-providers/local')
        if not cur['enabled']:
            cur = a.call('PATCH', '/api/v1/sign-in-providers/local', {'enabled': True, 'expectedVersion': cur['version']})
            print('restored local sign-in')
        print('local sign-in enabled =', cur['enabled'])
    elif step == 'users':
        pj([(u['username'], u.get('name'), u.get('state') or u.get('status')) for u in a.call('GET', '/api/v1/users?pageSize=50')['items']], 1500)


def cmd_jobs(a):
    """Fixture 7: hold the c10-jobs-pictures workspace row, queue two real batches, photograph run-jobs, release."""
    import subprocess, uuid
    ws = 'c10-jobs-pictures'
    o = stop_of(a, ws)
    lock = subprocess.Popen(['docker', 'exec', '-i', 'refiroo-guide-ref-database-1', 'psql', '-U', 'rdm', '-d', 'rdm', '-q', '-t', '-A'],
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
    try:
        lock.stdin.write("SET idle_in_transaction_session_timeout='180s';\nBEGIN;\nSELECT key FROM workspaces WHERE key='c10-jobs-pictures' FOR NO KEY UPDATE;\n")
        lock.stdin.flush()
        time.sleep(4)
        jobs = []
        for n in (1, 2):
            item = load.upsert('network', 'stop', o['id'], o['name'], load.attrs(abbreviation=f'C10-JOB-{n}'), o.get('parentObjectId'))
            body = {'workspaceKey': ws, 'policy': 'independent', 'run': 'background', 'onExisting': 'overwrite', 'items': [item]}
            jobs.append(a.call('POST', '/api/v1/batches', body, headers={'Idempotency-Key': str(uuid.uuid4())})['id'])
            time.sleep(2)
        for _ in range(30):
            st = [a.call('GET', f'/api/v1/jobs/{j}')['state'] for j in jobs]
            print('states', st)
            if st == ['running', 'queued']:
                break
            time.sleep(2)
        r = subprocess.run(['node', str(HERE.parents[2] / 'tools' / 'screens.mjs'), '--file', 'C10.screens.json', '--only', 'run-jobs'], capture_output=True, text=True)
        print(r.stdout.strip(), r.stderr.strip()[-300:])
    finally:
        try:
            lock.stdin.write('ROLLBACK;\n\\q\n'); lock.stdin.flush()
        except Exception:
            pass
        lock.wait(timeout=30)
    for j in jobs:
        print(j, a.wait_job(j, 'job')['state'], a.call('GET', f'/api/v1/jobs/{j}').get('counts'))


def cmd_drive(a, workspace, only, last, tries='6'):
    """Run recipes `only` (comma list) until the assistant task of `workspace` stops failing: a failed task
    (the shell-token flake) is discarded and the recipes restart; `last` is the recipe whose result ends the run."""
    import subprocess
    log = SCRATCH / f'drive-{workspace}.log'
    for n in range(int(tries)):
        with open(log, 'w') as fh:
            proc = subprocess.Popen(['node', str(HERE.parents[2] / 'tools' / 'screens.mjs'), '--file', 'C10.screens.json', '--only', only], stdout=fh, stderr=subprocess.STDOUT)
        time.sleep(20)
        failed = None
        while proc.poll() is None:
            ts = [t for t in a.call('GET', '/api/v1/ai/tasks?pageSize=10')['items'] if t['workspaceKey'] == workspace and t['state'] != 'cancelled']
            if ts and ts[0]['state'] == 'failed':
                failed = ts[0]
                break
            time.sleep(10)
        if failed:
            proc.kill()
            print('attempt', n + 1, 'task', failed['id'], 'failed:', failed['notes'][-1]['text'][:90].replace('\n', ' '), '; discarding', flush=True)
            a.call('POST', f"/api/v1/ai/tasks/{failed['id']}/discard", {'expectedVersion': failed['version']})
            continue
        print(open(log).read())
        return
    print('gave up')


def cmd_call(a, method, path, body=None):
    """Any API call (admin session); prints the answer."""
    pj(a.call(method, path, json.loads(body) if body else None), 8000)


COMMANDS = {k[4:]: v for k, v in globals().items() if k.startswith('cmd_')}
if __name__ == '__main__':
    COMMANDS[sys.argv[1]](api(), *sys.argv[2:])
