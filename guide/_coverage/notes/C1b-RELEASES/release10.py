from reconcile import apply,split,NOTES,ROOT
s='CL [0.10.0]/[0.10.0-alpha.1]; PL 0.10 '
a=[]
def add(i,t,reader,sec,home,pkg):a.append((f'R{i:03}',t,reader,sec,home,s+pkg))
add(93,'A model operation request applies up to 500 operations atomically as one recorded step at the draft version, stores inverses and diagnostics, allows intermediate invalid drafts, and counts migration impact across live data and open change sets in all affected workspaces.','model-admin, integrator','model','model/model-editor','A2 D33; MODEL_OPERATION_MAX_ITEMS')
add(94,'Installing a model draft makes the installed release its base without resetting its version; reinstalling the same model key and version is a conflict, so the install dialog proposes an editable next version.','model-admin','model','model/releases','A2 D17/D34; A0 D18')
add(95,'The layout preview reads chosen live data through the draft’s model, uses an empty record for a new type and disables writes; invalid drafts cannot preview, and layout edits are ordinary undoable draft steps.','model-admin','model','model/model-editor','A4b D43–D50')
add(96,'Turning off XREF in the consumer editor asks for confirmation, removes its match rules and turns off Resolve; draft schema, example and OpenAPI documents are available before installation.','model-admin','model','model/consumer-apis','A4c D51–D59')
add(97,'Uploading a source file replaces its owner’s current file, retains the superseded file for job retention, profiles every filled cell and deletes files with their owner; deleting a file first stops every job reading it.','model-admin','model','model/workbook-onboarding','A3; R-F5/R-F8')
add(98,'A load-affecting model or profile step replaces the current dry run; labels, navigation, release identity, layout and consumer definitions do not cancel a running dry run or start another.','model-admin','model','model/workbook-onboarding','A3/A5a; R-F15')
add(99,'Model operations update the draft’s import profile too: renamed references follow, moved or split fields acquire matching sources, merges repoint sources, and removals leave unmapped columns with warnings rather than silently ignoring them.','model-admin','model','model/import-profiles','A5a D74–D80')
add(100,'Missing named parent or related records can be created once per value during loading, but missing:create requires matching by name; fixed source parents cannot also be bound by a parent column.','model-admin, integrator','model','model/import-profiles','A5a D77; A8c D140–D146')
add(101,'A rules-based proposal explains its pattern, evidence, alternatives and requirements; repeated inference updates only unedited proposals, preserves administrator edits and undone decisions, and reports disagreements instead of replaying them.','model-admin','model','model/workbook-onboarding','A6a/A6b D86–D98; R038 supersedes AI helper')
add(102,'Workbook checks report new, missing or renamed columns, new lookup values, name drift and missing records before loading; a rename candidate keeps its column position and shares at least half the values.','model-admin, steward','model','model/import-profiles','A5c D82–D85')
add(103,'Deleting records missing from a workbook requires a change set, excludes records named by refused rows, and refuses surviving descendants or required dependants; single-valued relationship mappings replace their old targets on the next load.','model-admin, integrator','model','model/import-profiles','A5c D104/D105; R-F1')
add(104,'A source may skip rows without keys only when it declares a key; its binding report and dry run count skipped rows, while empty source rows and identified heading or note rows do not create records.','model-admin, integrator','model','model/import-profiles','A6b/A7/A8a/A8c')
add(105,'Laid-out workbook lists can be adjusted by header, last row and columns, unloaded or read from a chosen rectangle; column bindings follow their original letters, and three matching lists under one title can be read as a parent list with contained records.','model-admin','model','model/workbook-onboarding','A8a/A8b/A8c')
add(106,'An editable multi-valued relationship cell saves additions and removals in one atomic batch; single-valued cells use candidate choices, and computed, ancestor, containment, ownership, read-only and publication cells offer no edit controls.','steward','use','use/records','A9 D131–D139')
r=[('L29','Deleting records absent from a workbook is allowed only in a change set.','Profile missing:delete','Review missing records before publishing; surviving dependants can refuse deletion.','Keep or delete missing records.','model-admin, integrator','422 MISSING_DELETE_NEEDS_CHANGE_SET',s+'A5c D104','model','model/import-profiles'),('L30','A source cannot bind its parent both as a fixed value and as a column.','One parent per source','Choose one parent binding.','Profile issue names the binding.','model-admin, integrator','PARENT_BOUND_TWICE',s+'A8c','model','model/import-profiles'),('L31','Automatic creation of a missing named parent or related record requires a name match.','Profile missing:create','Use name matching or supply an existing record.','Mapping issue.','model-admin, integrator','CREATE_NEEDS_NAME_MATCH',s+'A5a D77','model','model/import-profiles'),('L32','A model preview never writes and cannot open an invalid draft.','Preview is over compiled draft definitions','Resolve draft issues before previewing.','Controls appear disabled.','model-admin','',s+'A4b','model','model/model-editor')]
x={}
m={1:['J34.10','R105'],2:['J02.7','R106'],3:['J34.10','R105'],4:['J34.10','R104'],5:['J34.9','R104'],6:['J35.S1','R102','R103'],7:['J34.4','R101'],8:['J34.4','J34.5','J34.6','R101'],9:['J34.2','R100'],10:['J34.7','R099','R098'],11:['R100'],12:['J34.1','R036','R097'],13:['J34.S1','J34.2','J34.8'],14:['R103'],15:['R101'],17:['J34.2'],18:['R036'],19:['R036']}
for i,t in m.items():x[f'CL-0.10.0-#{i}']=('merged',t,'Current delivered model/profile behavior retained.')
x['CL-0.10.0-#16']=('dropped',[],'Internal profiling analysis and code consolidation; no extra reader capability.')
# Map alpha checkpoint leads by the actual content, not numerical coincidence.
alpha={2:['J33.9','R034'],3:['F18.b'],4:['J33.S2','R093','R094','R035'],5:['J33.S1','R037'],6:['J33.10','R095'],7:['J33.13','J33.14','R096']}
for i,t in alpha.items():x[f'CL-0.10.0-alpha.1-#{i}']=('merged',t,'Designer behavior retained with later reference-rewrite amendment.')
for i in [1,8]:x[f'CL-0.10.0-alpha.1-#{i}']=('dropped',[],'Design approval or checkpoint acceptance evidence rather than a separate capability.')
# The earlier extractor collapsed D numbers across releases. These origins follow the retained text.
old7={8:'J18.1',9:'J10.S1',11:'R004'}
old8={2:'F03.c',4:'F03.c',5:'J21.4',10:'R005',13:'R007',14:'R070',16:'GL-33',21:'R066',22:'R066',27:'J19.S4',24:'R066',32:'R012',35:'J14.10',36:'R009',38:'J15.S1',39:'J15.S1',42:'R069',45:'R068'}
old9={43:'F16.a',47:'J21.9',48:'J21.9',49:'J27.3',50:'J27.1',51:'J27.1',52:'J27.1',53:'R031',54:'R022',55:'J27.S4',57:'J27.6',59:'J27.6',60:'R030',61:'J27.6',62:'J27.6',63:'J27.6',64:'J27.9',65:'J27.7',66:'J27.8',67:'J27.8',69:'R032',70:'J27.8',71:'J27.9',72:'J27.10',73:'J27.S3',77:'R016',78:'J02.5',80:'J27.11',81:'R088',82:'R036',83:'J27.12',84:'J27.10',85:'J27.10',86:'J27.11',87:'R088',89:'J27.13',90:'J27.11',91:'J27.13',92:'J27.13',93:'J27.13',94:'J27.13',96:'J27.14',97:'R084',98:'R084',99:'J27.14',100:'R084',102:'J32.1',103:'J32.1',104:'J32.1',105:'J32.1',106:'J32.2',107:'J11.3',108:'J32.1',109:'J32.1',110:'J32.1',111:'J32.S1',112:'J11.9',113:'J11.9',114:'J32.2',115:'J32.2',117:'J32.2',118:'J32.2',119:'R088',120:'J11.6',121:'J11.6',122:'J11.6',125:'J32.3',126:'J32.3',127:'J32.4',128:'J32.4',129:'J11.10',130:'J11.11',131:'J32.4',132:'J32.4',133:'J32.4',134:'J32.4',135:'J01.8',136:'J11.12',137:'J11.12',138:'J11.12',139:'J32.5',140:'J01.8',141:'J08.12',142:'J01.8',143:'J01.8',144:'J01.8',145:'J01.10',146:'J01.8',148:'J01.9',149:'J01.9',150:'J01.9',151:'J01.9',153:'J01.10',3:'J27.8',12:'J27.S4',19:'J22.S2',20:'J23.5',29:'R019',31:'J26.S1',34:'J26.4',37:'R055',40:'R022'}
new10={1:'J33.9',6:'J34.S1',18:'R094',23:'R034',25:'J33.9',26:'J33.9',33:'R093',44:'R095',56:'R096'}
origins={**{f'PL-D{i}':'0.7' for i in old7},**{f'PL-D{i}':'0.8' for i in old8},**{f'PL-D{i}':'0.9' for i in old9},**{f'PL-D{i}':'0.10' for i in new10}}
for d,mp in [('0.7',old7),('0.8',old8),('0.9',old9),('0.10',new10)]:
 for i,t in mp.items():x[f'PL-D{i}']=('merged',[t],f'Corrected origin: PL {d} D{i}; old inventory combined unrelated decisions with the same number.')
for i,origin in [(7,'0.8'),(28,'0.8'),(46,'0.8'),(30,'0.8'),(58,'0.9'),(68,'0.9'),(74,'0.9'),(75,'0.9'),(76,'0.9'),(88,'0.9'),(95,'0.9'),(101,'0.9'),(123,'0.9'),(124,'0.9'),(147,'0.9')]:
 x[f'PL-D{i}']=('dropped',[],f'PL {origin} D{i}: internal measurement, implementation, fixture or delivery sequencing.');origins[f'PL-D{i}']=origin
for i,reason in [(17,'0.8 split-topology restriction superseded by 0.11 N1/N3.'),(41,'0.8 D41 5,000-record limit lowered to 500 by D44.'),(79,'0.9 D79 upgrade-duplicate handling was withdrawn.'),(116,'0.9 K2 deletion exclusion superseded by delivered K2b.')]:x[f'PL-D{i}']=('superseded',[],reason);origins[f'PL-D{i}']='0.8' if i in [17,41] else '0.9'
x['PL-A-D5']=('superseded',[],'The optional AI naming helper was removed in 0.16 AP6a; rules-based inference remains R038.')
x['PL-A-D9']=('merged',['J34.10'],'Laid-out list behavior retained; formatting and colours are not semantic input.')
# Correct the provenance text on these evidence rows before moving it onto semantic records.
for path in [ROOT/'_waves/PROMISES.md',ROOT/'_waves/COVERAGE.md']:
 text=path.read_text()
 for line in text.splitlines():
  if not line.startswith('|'):continue
  for ident,origin in origins.items():
   if (path.name=='PROMISES.md' and line.startswith('| '+ident+' |')) or (path.name=='COVERAGE.md' and 'PROMISES.md '+ident+';' in line):
    import re
    corrected=re.sub(r'PL §0\.10 plan,.*? (D\d+)(?= \||;|$)',lambda m:'PL §'+origin+' plan '+m[1],line)
    text=text.replace(line,corrected);break
 path.write_text(text)
leads=[split(l)[0] for l in (NOTES/'0.10-leads.txt').read_text().splitlines() if l.startswith('|')]
x.pop('CL-0.10.0-alpha.1-#8',None);x.pop('CL-0.10.0-#19',None)
assert set(leads)==set(x),(set(leads)-set(x),set(x)-set(leads))
apply('0.10 (including alpha.1 and corrected cross-release decision leads)',a,r,x)
