# D-RUN report

Reviewed 23 existing pages; changed 18 pages. No new pages or sidebar changes were needed.
Word counts use whitespace-separated words, including front matter and code.

| Page in run/ | Before | After |
| --- | ---: | ---: |
| ai.md | 3584 | 3859 |
| background-jobs.md | 2041 | 2349 |
| backup-and-restore.md | 2134 | 2331 |
| command-line.md | 1437 | 1443 |
| configure.md | 2723 | 2808 |
| database.md | 1023 | 1335 |
| developer-instance.md | 1307 | 1308 |
| health-and-startup-checks.md | 1922 | 1922 |
| https.md | 1884 | 2214 |
| install-with-compose.md | 3289 | 3530 |
| licence-and-source.md | 502 | 502 |
| model-releases-and-rollback.md | 908 | 908 |
| monitoring.md | 2001 | 2201 |
| overview.md | 1127 | 1130 |
| production-checklist.md | 1303 | 1356 |
| secrets-and-keys.md | 1105 | 1417 |
| security-checklist.md | 984 | 968 |
| set-up-ai.md | 2304 | 2421 |
| several-processes.md | 1071 | 1116 |
| sign-in-and-mail-setup.md | 2541 | 2798 |
| troubleshooting.md | 1575 | 1712 |
| upgrades.md | 1394 | 1394 |
| webhook-delivery.md | 1629 | 1629 |
| **Total** | **39788** | **42651** |

Coverage: 146/146 current run inventory entries covered: 62 settings, 47 deployment pieces,
24 commands/options, 9 management operations and 4 screens. Nine initially uncovered deployment
entries resolved. No new exclusions; existing 254 historical rows retained with their classifications.
All applicable depth topics were reviewed; page-by-page answers and non-applicable topics are in
depth.md. No reader capability deliberately left open.

Screens: seven existing images reused; no new screenshot or placeholder. Deployment needs its
existing image refreshed for current paths; screens-wanted/D-RUN.md describes the state. Images
were not visually inspected in this writing wave.

Verification: GUIDE_OUT=_build/D-RUN npm run verify runs the required isolated build, terminology,
brand and built-link checks. Final result: passed, 247 built pages, terminology/brand passed, 69,685 local links/sources checked. See verify.log. The coverage command uses the
original tools/check.mjs with coverage-output.cjs redirecting only its generated uncovered report
into the allowed notes directory. The shared inventory report was not overwritten. Other sections
have uncovered rows, so the whole-site coverage command exits 1; no run row remains uncovered.
See coverage.log and uncovered.md here for the bounded results.

Unverified: deployment commands, certificate issuance/renewal, password/key rotation, backup/restore,
upgrades, phone trust, provider and SMTP/receiver connectivity and paid AI calls were not executed.
Capacity, recovery time, external credential lifecycle and multi-node topology require the operator's
own measurements or provider controls. No servers or scratch databases were started.

Product defects: no new product defect confirmed. Existing comments claiming both 80 and 443 are
needed remain outside this wave's allowance and are assigned to Claude in D-RUN.md; the operator
pages now say only 443 is required, with optional HTTP redirects on 80. Documentation tooling issue:
check.mjs normalPath() erases the braces around {$PUBLIC_URL}, so its label is missed despite the
Caddyfile excerpt and directive explanation. A hidden exact inventory provenance comment beside
the explanation satisfies coverage without excluding the capability or altering the checker.

Files: only allowed run pages, coverage/run.md, screens-wanted/D-RUN.md, progress/D-RUN.md and
notes/D-RUN were edited; no commits or git state changes. No steering file existed during the work.
