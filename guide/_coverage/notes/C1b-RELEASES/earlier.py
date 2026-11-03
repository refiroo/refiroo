from reconcile import apply
m5={1:['J08.S1','J08.S2','J08.S3'],2:['J01.S3','J01.S5'],3:['J21.S1','J01.6'],4:['J08.S5','J12.10'],5:['J08.S4'],6:['J08.1','J08.2','J08.4'],8:['J03.3','J13.6','J13.5'],9:['J13.1','J14.6'],10:['J04.S1'],11:['J02.S1','J03.S1','J13.S1'],12:['F17.a','R062'],13:['J02.4'],14:['J13.S3'],15:['J02.5'],17:['J12.16'],18:['J13.2','J08.S3'],19:['J21.S1'],20:['F16.a'],21:['F16.a'],22:['J12.S1']}
x={f'CL-0.5.0-#{i}':('merged',t,'Earlier released rule retained through its later generic workspace contract.') for i,t in m5.items()}
x['CL-0.5.0-#7']=('superseded',['J36.S2'],'0.11 M1 replaces singleton model runtime state with per-workspace release assignments.')
for i in [16,23,24]:x[f'CL-0.5.0-#{i}']=('dropped',[],'Starter release numbering, query implementation or superseded development tooling.')
apply('0.5 (earlier C1 record verified)',[],[],x)
m6={1:['J07.1','J18.3'],2:['J05.1'],3:['J07.S1','J07.S2','J19.S3'],4:['J04.S1','J04.5'],5:['J05.S1','J07.S1'],6:['J02.S1','J05.S4','J06.S1'],7:['J05.1','J07.1'],9:['R062'],11:['F18.a'],12:['F18.a','J01.S5'],13:['J01.S5','J05.S1','J07.S1'],15:['J02.S1','J13.S1'],16:['J05.S1','J05.S3','J05.S4'],17:['R001']}
x={f'CL-0.6.0-#{i}':('merged',t,'Earlier workspace-level behavior retained with current lifecycle terms and release scopes.') for i,t in m6.items()}
for i in [8,10,14]:x[f'CL-0.6.0-#{i}']=('dropped',[],'Shared implementation or release-validation evidence, not a separate capability.')
x['CL-0.6.0-#18']=('superseded',[],'Rejected per-record lifecycle was replaced by workspace change sets and publications before 0.6 released.')
apply('0.6 (earlier C1 record verified)',[],[],x)
apply('0.3 (baseline; no remaining leads)',[],[],{})
x={f'PL-PP-D{i}':('dropped',[],'0.17 is explicitly unbuilt: this is a plan, not a current reader capability.') for i in [1,3,4,5,6,7,9,10]}
x['PL-PP-D2']=('merged',['J36.12'],'The only delivered clause points to 0.16 WM1; no 0.17 behavior is claimed.')
apply('0.13/0.14/0.15/0.17 status checked (no additional released product section)',[],[],x)
