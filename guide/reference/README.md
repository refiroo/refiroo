# The reference instance

A local refiroo instance with the guide's reference set loaded: the public transport stops of
Graubünden (about 3,500 records). It serves the screenshots (DOC10) and the fresh-reader check (DOC11),
and anyone who wants to repeat the guide's examples on a larger set. It is the engine image from this
checkout, Docker Compose project `refiroo-guide-ref`, on ports 8480 (HTTP) and 8443 (unused). It never
uses ports 8000, 5173, 5000, 7000, 9443, 54320 or 11434.

```bash
guide/reference/reference.sh up      # build, start, create the administrator, load the set
guide/reference/reference.sh load    # load again (safe to repeat)
guide/reference/reference.sh stop    # stop, keeping the data     (start: start again)
guide/reference/reference.sh down    # remove the instance and its data; .env stays
```

Open http://localhost:8480 and sign in as `guide`. The password is `GUIDE_ADMIN_PASSWORD` in
`guide/reference/.env`, generated from `.env.example` on the first `up` and git-ignored. The API
reference is at http://localhost:8480/docs.

What is loaded, and the command that loads either set on any instance, is in
[`../samples/README.md`](../samples/README.md); the sources and their licences are in
[`../samples/SOURCES.md`](../samples/SOURCES.md). The reference set also holds an open change set,
"December 2026 timetable change", and a client "Stops reader (guide)" holding the `stops` consumer API
(its credentials are `GUIDE_CONSUMER_CLIENT_ID` and `_SECRET` in `.env`).
