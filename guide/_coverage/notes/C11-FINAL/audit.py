from pathlib import Path
import re,json,hashlib
ROOT=Path(__file__).resolve().parents[3]
DOCS=ROOT/'src/content/docs'
NOTES=Path(__file__).resolve().parent

def rows():
    result=[]
    for file in sorted((ROOT/'_waves/coverage').glob('*.md')):
        for line in file.read_text().splitlines():
            if not re.match(r'\| C\d+',line):continue
            cols=re.split(r'(?<!\\)\|',line)[1:-1]
            if len(cols)!=7:raise ValueError((file,line))
            ident,item,kind,reader,section,source,coverage=map(str.strip,cols)
            links=re.findall(r'\]\(([^)]+)\)',coverage)
            targets=[]
            for link in links:
                if 'src/content/docs/' in link:slug=link.split('src/content/docs/',1)[1].split('#')[0].removesuffix('.md')
                elif link.startswith('/docs/'):slug=link[6:].split('#')[0].rstrip('/')
                else:continue
                page=DOCS/(slug+'.md')
                targets.append({'slug':slug,'exists':page.exists(),'sha256':hashlib.sha256(page.read_bytes()).hexdigest() if page.exists() else None,'link':link})
            status='deferred' if coverage.startswith('after 0.16') else 'excluded' if coverage.lower().startswith('not for readers') else 'open' if re.search('uncovered|partly',coverage) else 'covered'
            result.append(dict(id=ident,item=item,source=source,coverage=coverage,section=file.stem,status=status,targets=targets))
    return result

def counts(data):
    return {section:{s:sum(r['section']==section and r['status']==s for r in data) for s in ['covered','excluded','deferred','open']} for section in sorted({r['section'] for r in data})}

if __name__=='__main__':
    data=rows()
    if not (NOTES/'before.json').exists():(NOTES/'before.json').write_text(json.dumps(data,indent=2))
    (NOTES/'current.json').write_text(json.dumps(data,indent=2))
    print(json.dumps(counts(data),indent=2))
    for r in data:
        if r['status']=='covered' and (not r['targets'] or any(not t['exists'] for t in r['targets'])):print('BAD TARGET',r['id'],r['coverage'])
