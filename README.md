# CampusConnect registration site

A student registration site with a small Python backend. No packages to install; Python 3.8+ only.

## Run it

```
python3 server.py            # http://127.0.0.1:8000
python3 server.py --port 9000
```

- `/` is the registration form.
- `/registrations` lists everyone who has registered, with search and CSV download.
- Data is stored in `registrations.db` (SQLite), created on first run.

## Test it

```
python3 test.py
```

The tests start the real server on a free port with a temporary database, so your real data is never touched.

## Files

```
server.py              server, validation, SQLite storage, JSON API
test.py                unit and end-to-end tests
public/index.html      registration form
public/style.css       styles
public/script.js       form validation and submit
public/registrations.html, registrations.js    organiser list
```

## API

| Method | Path                 | What it does                                  |
|--------|----------------------|-----------------------------------------------|
| POST   | `/api/register`      | Save a registration. 201, 422 (errors), 409 (duplicate enrollment or email) |
| GET    | `/api/registrations` | List registrations (admin only, see below)    |
| GET    | `/api/health`        | `{"ok": true}`                                |

## Privacy and deployment

The list contains personal data. By default `/api/registrations` only answers requests that come from the same machine. Before putting the site on a network, set a key:

```
ADMIN_KEY="choose-a-long-random-value" python3 server.py --host 0.0.0.0
```

The registrations page then asks for that key. Serve the site over HTTPS (for example behind a reverse proxy) so the key and the form data are encrypted in transit. When behind a proxy, always set `ADMIN_KEY`, because every request will look like it comes from the proxy's machine.
