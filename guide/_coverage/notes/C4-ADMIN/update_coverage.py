from pathlib import Path
import re
from write_unit import progress
path=Path('guide/_waves/coverage/administer.md')
groups={}
def assign(slug, numbers):
    for n in numbers: groups[n]=slug
assign('administer/roles-and-grants',[2230,2232,2233,2235,2236,2237,2241,2245,2252,2253,2255,2261,2270,2271,2272,2273,2275,2276,2285,2286,2288,2294,2295,2301,2304,2310,2313,2315,2316,2317,2405,2406,2407,2408,2409,2410,2411,2414,2416,2422,2423,2458,2460,2461,2462,4014,4038])
assign('administer/roles-and-grants#the-predefined-roles',range(2426,2453))
assign('administer/clients',[2201,2202,2203,2204,2205,2206,2207,2208,2213,2214,2215,2231,2249,2250,2269,2525,4013])
assign('administer/people-and-groups',[2229,2239,2254,2256,2274,2277,2278,2279,2280,2281,2289,2305,2306,2307,2308,2309,2418,2464,2466,2467,2468,2469,2470,2471,4020])
assign('administer/sign-in',[2424,2238,2265,2402,2439,2454,2490,2491,2492,2493,2494,2495,2496,2497,2498,2499,2500,2501,2502,2503,2504,2505,4018,4019,4021,4022])
assign('administer/mail',[2218,2219,2220,2221,2222,2223,2224,2225,2226,2227,2228,2290,2291,2292,2293,2296,2297,2298,2299,2300,2303,2401,2465,4023])
assign('administer/audit',[2200,2246,2258,2311,2314,2413])
assign('administer/approval-policies',[2195,2243,2266,2268,2302,2463])
assign('administer/signing-keys',[2425,2506,2514,2515,2516,2517,2518,2519,2520])
assign('administer/webhooks',[2521,2522,2523,2524,2527,2528,2529,2530,2531,2532,2533])
assign('administer/api-reference-and-consumer-api-pages',[2194])
assign('administer/deployment-pages',[2216])
assign('administer/jobs-and-limits',[2217,2287])
assign('use/records',[2234])
assign('use/history',[2247])
assign('model/managing-workspaces',[2248,2257,2259,2403,2404,2412,2419,2420,2455,3962])
assign('model/consumer-apis',[2260])
assign('use/lists-and-filters',[2251])
assign('guide/model/add-a-record-type-and-fields',[2264])
assign('integrate/identifiers-paging-and-errors',[2263])
assign('use/home',[2282,2283])
assign('use/importing-and-exporting',[2284])
assign('use/account',[2457])
for n,slug in {
2534:'add-a-person',2535:'add-a-sign-in-provider',2536:'create-a-client',2537:'create-a-custom-role',2538:'create-a-webhook',2539:'find-out-why-a-webhook-paused',2540:'find-who-changed-something',2541:'grant-a-consumer-api-to-a-client',2542:'grant-a-role',2543:'help-someone-who-lost-a-device',2544:'link-a-provider-person',2545:'manage-a-group',2546:'narrow-a-grant-to-record-types',2547:'require-a-second-factor',2548:'rotate-a-client-secret',2549:'rotate-a-webhook-key',2550:'rotate-signing-keys',2551:'set-an-approval-policy',2552:'set-up-mail',2553:'turn-off-local-sign-in'
}.items(): groups[n]='guide/administer/'+slug

def link(slug):
    file,sep,anchor=slug.partition('#')
    assert Path('guide/src/content/docs/'+file+'.md').exists(),slug
    return f'[{slug}](../../src/content/docs/{file}.md'+('#'+anchor if sep else '')+')'
lines=[]; changed=0; retained=[]
for l in path.read_text().splitlines():
    parts=l.split('|')
    if len(parts)>7 and re.fullmatch(r' C\d+ ',parts[1]):
        n=int(parts[1].strip()[1:]); old=parts[7].strip()
        if old.startswith(('after 0.16','not for readers:')):
            retained.append((n,old))
        elif n in [2318,2321,2335,2342,2345,2359,2374,2385,2386,2473,2476]:
            # AI task evidence explicitly deferred by COMPLETE-COMMON; preserve its row.
            retained.append((n,'AI deferred; original open row retained'))
        elif n in [2262,2453]:
            parts[7]=' not for readers: security acceptance-test method, not an additional browser capability. '
            l='|'.join(parts); changed+=1
        else:
            assert n in groups, f'No mapping for C{n}: {parts[2]}'
            dest=link(groups[n])
            if n==2506: dest+='; '+link('administer/clients')+'; '+link('administer/mail#messages-and-retries')+' — no delete controls; use deactivate/restore or Stop sending.'
            if n==4022: dest+='; '+link('administer/mail#mail-server')
            if n==4038: dest+='; '+link('guide/administer/manage-a-group#change-or-remove-membership')+' — grants save separately; bulk removal is atomic.'
            if n==2238: dest+='; '+link('guide/administer/add-a-sign-in-provider')
            if n==2302: dest+='; '+link('use/change-sets')
            if n in [4018,4019]: dest+='; '+link('use/account')+' — administrator recovery and policy documented here; personal tasks stay in Use.'
            if n in [2206,2213,2230,2231,2265,2269,2521,2522,2523,2524,4013,4014]: dest+='; '+link('integrate/security-model-for-integrators')+' — integration contract in Integrate.'
            if n in [2234,2251,2260,2264,2282,2283,2284,2412,2419,2420,2457,3962]: dest+=' — reader task belongs to the linked section; no duplicate access-administration instructions.'
            parts[7]=' '+dest+' '; l='|'.join(parts); changed+=1
    lines.append(l)
path.write_text('\n'.join(lines)+'\n')
progress(str(path),f'Reconciled {changed} browser-capability and cross-reader rows against the pages and source. Retained excluded/internal and after-0.16 rows unchanged.','Eleven previously open rows are AI task, assistant or explanation evidence; their original rows remain unchanged under the wave’s explicit deferral.')
Path('guide/_coverage/notes/C4-ADMIN/coverage-review.md').write_text('# Coverage review\n\nThe old ledger frequently pointed unrelated screens to roles-and-grants; those pointers were corrected to their actual homes. Personal tasks stay in Use, workspace/model editing in Model, and integration contracts in Integrate. No other section files changed.\n\nDeferred/excluded rows retained:\n'+''.join(f'- C{n}: {status}\n' for n,status in retained))
print(f'{changed} reconciled rows; {len(retained)} deferred/excluded retained.')
