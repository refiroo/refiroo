# untagged

## GET /health

Title: Check readiness

Tells a load balancer or orchestrator whether this process can serve requests. It needs no token. The body is JSON, `{"status": "ok"}`, or `{"status": "unhealthy"}` with status 503 (not the error body) while the database is unreachable or no workspace's model can be served. Use `GET /health/live` to ask only whether the process runs.

## GET /health/live

Title: Check liveness

Tells whether this process answers, and asks nothing else, so a database outage does not make an orchestrator restart it. It needs no token. The body is JSON, `{"status": "ok"}`. Use `GET /health` for readiness.
