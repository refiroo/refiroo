from pathlib import Path
import re,json
root=Path('guide')
p=root/'_waves/coverage/model.md'
steer=root/'_waves/steer/C3-MODEL.md'
if steer.exists() and steer.read_text().strip():raise RuntimeError('Read steering first')
lines=p.read_text().splitlines()
# Keep all explicitly deferred rows and the AI-only entries misfiled as ordinary gaps verbatim.
ai={1650,1698,1699,1781,1782,1789,1871,1872,1874,1950,2168}
cross={1679:'use/records',1681:'index',1683:'use/account',1685:'use/lists-and-filters',1800:'use/change-sets',1900:'use/applications',1938:'use/appearance-and-devices',1940:'use/relationships',1963:'use/appearance-and-devices',1981:'use/appearance-and-devices'}
overrides={
1363:'model/types-attributes-relations',1364:'model/types-attributes-relations',1365:'guide/model/split-merge-and-move-types',
1608:'guide/model/undo-and-review-the-draft-history',1611:'guide/model/undo-and-review-the-draft-history',
1613:'guide/model/export-a-release',1614:'guide/model/create-a-model-draft',
1620:'model/model-language-versions',1624:'guide/model/retire-or-delete-a-release',1626:'model/json-view',
1628:'model/migrations',1629:'guide/model/install-and-activate-a-release',1630:'model/migrations',1640:'model/releases',1642:'model/models',
1645:'model/migrations',1652:'guide/model/change-a-workspaces-model',1653:'model/managing-workspaces',1660:'guide/model/install-and-activate-a-release',1675:'model/model-language-versions',1678:'guide/model/raise-a-model-language-version',
1686:'guide/model/see-a-consumer-apis-documents',1702:'use/records',1715:'model/model-mappings',1725:'model/applications-and-views',1740:'guide/model/change-a-workspaces-model',1741:'model/migrations',1745:'model/consumer-apis',1748:'model/workbook-onboarding',
1754:'model/releases',1756:'guide/model/map-a-column',1758:'guide/model/map-a-column',1759:'model/model-mappings',1761:'model/migrations',1764:'model/model-language-versions',1775:'guide/model/choose-what-moves',1776:'model/migrations',1777:'model/migrations',1778:'model/model-language-versions',1779:'model/record-pages-and-tables',1780:'model/workbook-onboarding',1798:'guide/model/retire-or-delete-a-release',1802:'model/workbook-onboarding',1805:'guide/model/read-lists-in-a-sheet',1807:'model/model-mappings',1809:'model/models',1812:'model/model-language-versions',1816:'model/model-mappings',1817:'model/migrations',1820:'model/managing-workspaces',1821:'model/workbook-onboarding',1822:'model/workbook-onboarding',1823:'model/record-pages-and-tables',
1830:'guide/model/raise-a-contract-version',1833:'model/types-attributes-relations',1838:'model/workbook-onboarding',1840:'model/releases',1841:'model/releases',1842:'model/releases',1857:'guide/model/undo-and-review-the-draft-history',1859:'model/record-pages-and-tables',1893:'model/models',1896:'guide/model/retire-or-delete-a-workspace',1899:'model/applications-and-views',1902:'guide/model/preview-a-type',1904:'guide/model/edit-a-workspaces-model',1905:'guide/model/raise-a-contract-version',1908:'guide/model/work-on-a-draft-with-others',1909:'guide/model/edit-a-mapping-row',1910:'model/migrations',1911:'model/workbook-onboarding',1912:'guide/model/undo-and-review-the-draft-history',1913:'model/consumer-apis',1914:'model/consumer-apis',1918:'guide/model/edit-a-workspaces-model',1919:'guide/model/define-a-consumer-api',1920:'guide/model/reuse-and-change-attributes',1923:'guide/model/edit-a-record-page',1924:'guide/model/map-a-column',1928:'model/json-view',1932:'model/record-pages-and-tables',1933:'guide/model/group-collections-in-navigation',1935:'model/record-pages-and-tables',1936:'guide/model/split-merge-and-move-types',1947:'model/types-attributes-relations',1956:'model/types-attributes-relations',1957:'guide/model/remove-an-element',1958:'guide/model/remove-an-element',1961:'guide/model/move-records-to-another-model',1964:'model/record-pages-and-tables',1965:'guide/model/propose-again-with-a-newer-workbook',1976:'guide/model/load-a-workbook-into-a-change-set',1978:'guide/model/propose-again-with-a-newer-workbook',1985:'guide/model/group-collections-in-navigation',1986:'model/json-view',1988:'guide/model/edit-a-workspaces-model',
1989:'model/types-attributes-relations',1990:'guide/model/group-collections-in-navigation',1991:'guide/model/add-a-relation-matrix',1992:'guide/model/add-a-record-type-and-fields',1993:'guide/model/rename-or-re-key-an-element',1994:'guide/model/arrange-applications-and-views',1995:'guide/model/remove-an-element',1996:'guide/model/rename-or-re-key-an-element',1997:'guide/model/add-a-relationship',2003:'model/types-attributes-relations',2007:'guide/model/rename-or-re-key-an-element',2008:'guide/model/group-collections-in-navigation',2009:'guide/model/group-collections-in-navigation',2010:'guide/model/group-collections-in-navigation',2011:'guide/model/group-collections-in-navigation',2012:'guide/model/group-collections-in-navigation',2013:'guide/model/add-a-relationship',2014:'guide/model/reuse-and-change-attributes',2015:'guide/model/rename-or-re-key-an-element',2018:'guide/model/split-merge-and-move-types',2019:'guide/model/group-collections-in-navigation',2020:'guide/model/split-merge-and-move-types',2021:'guide/model/add-a-record-type-and-fields',2022:'guide/model/remove-an-element',2023:'guide/model/rename-or-re-key-an-element',2024:'guide/model/split-merge-and-move-types',2025:'guide/model/arrange-applications-and-views',2035:'guide/model/reuse-and-change-attributes',2036:'model/types-attributes-relations',2135:'model/migrations',2169:'model/workbook-onboarding',
3924:'guide/model/compare-releases',3925:'guide/model/export-a-release',3964:'model/consumer-apis',3973:'model/models',3974:'model/releases',3975:'model/record-pages-and-tables',3976:'model/consumer-apis',3999:'model/the-model-editor',4028:'model/releases',4029:'model/model-language-versions',4056:'guide/model/edit-a-workspaces-model',4057:'guide/model/edit-a-workspaces-model',4061:'guide/model/add-a-relation-matrix',4062:'guide/model/remove-an-element'}
def link(slug):
 assert (root/'src/content/docs'/f'{slug}.md').exists(),slug
 return f'[{slug}](../../src/content/docs/{slug}.md)'
def schema_home(item):
 cls=item.split('defines ')[1].split('.')[0]
 if cls=='EngineModel':return 'model/models'
 if cls=='ModelReleaseDefinition':return 'model/releases'
 if cls=='ProductDefinition':return 'model/models'
 if cls.startswith(('Consumer','Filter','FieldSpec','ObjectSpec','Operations','Operation','Related','ParentSpec','Event','Xref','Within','AlsoMatch','Ancestor','Projection','ObjectTypeParameter','_Described')):return 'model/consumer-apis'
 if cls.startswith(('ObjectType','AttributeType','RelationType','Candidate','Binding','Effective')):return 'model/types-attributes-relations'
 if cls in {'ApplicationDefinition','NavigationDefinition','NavigationGroupDefinition'}:return 'model/applications-and-views'
 return 'model/record-pages-and-tables'
changes=[]; deferred=[]
for i,l in enumerate(lines):
 if not l.startswith('| C'):continue
 cells=l.split('|'); cid=cells[1].strip();n=int(cid[1:]);item=cells[2].strip();old=cells[-2].strip()
 if old=='after 0.16' or n in ai:
  deferred.append(cid);continue
 if old.startswith('not for readers:'):continue
 if item.startswith('The model language defines'):
  slug=schema_home(item)
  new=link(slug)+'; specialist document settings and visual-control limits: '+link('model/json-view')
  why='Schema-derived row: browser meaning and visual limits, not a promise of a dedicated form or a repetition of the integration contract.'
 else:
  slug=cross.get(n) or overrides.get(n)
  if not slug:
   m=re.search(r'(?:uncovered → |\[)((?:guide/)?model/[a-z0-9-]+)',old)
   slug=m.group(1) if m else 'model/models'
  if slug=='guide/model/model-language-versions':slug='model/model-language-versions'
  new=link(slug)
  why='Reader behavior and task covered at the linked page; source labels checked by topic in frontend and backend.'
  if n in cross or n==1702:
   new='Outside Model scope: '+new
   why='Misassigned general browsing/account/approval behavior; link to its existing reader page, no edits outside this wave.'
  if n==2016:
   new='not for readers: This is an inventory table heading (Item / menu label), not another operation.'
   why='Inventory heading rather than feature.'
  if n==2160:
   new=link('model/workbook-onboarding')
   why='Current rules-based workbook proposals; removed helper is internal history, not an AI feature to document.'
 cells[-2]=' '+new+' ';lines[i]='|'.join(cells)
 changes.append({'id':cid,'item':item,'source':cells[6].strip(),'previous':old,'covered_by':new,'reason':why})
p.write_text('\n'.join(lines)+'\n')
(root/'_coverage/notes/C3-MODEL/coverage-decisions.json').write_text(json.dumps(changes,indent=2)+'\n')
(root/'_coverage/notes/C3-MODEL/deferred-rows.json').write_text(json.dumps(deferred,indent=2)+'\n')
print('Reconciled',len(changes),'rows; preserved',len(deferred),'AI/deferred rows verbatim.')
print('AI/deferred:',', '.join(deferred))
