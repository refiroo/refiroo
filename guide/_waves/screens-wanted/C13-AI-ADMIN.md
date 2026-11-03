# Screens wanted — C13-AI-ADMIN

Steering 2026-11-03 says the reference provider and assistant are now enabled. Capture these from the reference instance after this wave. Use only guide reference data and fictional people. Do not expose secrets or create a deliberate outage just for a failure screenshot; a controlled test instance can show failures.

| File under public/screens | Page | Screen, state and what must be visible |
| --- | --- | --- |
| admin-ai-settings.png | administer/ai | Settings › Administration › AI, both switches on. What is switched on, Assistant, Provider, Model, Endpoint, Key set status without its value, What may be sent, Content kept and available features. |
| admin-ai-calls.png | administer/ai | Calls with a provider call and assistant turn, Asked by, Model, outcomes, tokens, Cost including unreported cost if available, Duration and last-30-day totals. Include a safe failure reason if available. |
| admin-ai-test-answered.png | guide/administer/check-the-ai-provider | Test request just answered. Send a test request, The AI provider answered with duration/model, newest Test request row below. |
| admin-ai-test-failed.png | guide/administer/check-the-ai-provider | Controlled provider test failure. The test request failed and concise safe reason, failed Test request row. No keys, private endpoint credentials or raw tracebacks. |
| admin-agent-access-enabled.png | administer/agent-access | Enabled Settings › Security › Agent access. How to connect, Address and Limit, Agent clients with access and last use, Assistants people sign in with showing Returns to and Signed in now. |
| admin-agent-calls.png | administer/agent-access | Calls populated, When, Who, Through, Tool, argument names only and outcomes. Prefer an answered and a refused call; no argument values. |
| admin-agent-new-client.png | guide/administer/manage-agent-access | New agent client dialog, empty or fictional Name and Create and show its secret. Do not capture the resulting secret. |
| admin-agent-register.png | guide/administer/manage-agent-access | Register an assistant dialog, Name, Return addresses with safe example addresses, help text and Register. |
| admin-agent-block.png | guide/administer/manage-agent-access | Block confirmation for a fictional reference assistant, affected-session count and Block button. No active real-user assistant should be blocked to obtain the image. |

Existing `admin-agent-access.png` was visually inspected and reused only for its disabled state. New screenshots have not been captured or inspected by this wave.
