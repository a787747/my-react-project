# FRONTEND MAP — 135.232.120.40:8080

Captured: 2026-08-12, approximately 21:38–21:45 UTC.  
Host: `135.232.120.40` (RIPE inetnum `135.232.0.0/24` range `135.232.0.0 – 135.232.255.255`, `netname: cloud`, `mnt-by: MICROSOFT-MAINT` — **Microsoft Azure**). No PTR.  
Method: read-only. Public HTTP GET of the SPA and static assets. TCP probes of common ports from this workstation and, for 22/80/3389/8080, from `root@92.51.45.147` over the existing ControlMaster socket. No rebuild, restart, redeploy, or EPE webhook call.  
Items not proven here are marked **unverified**.

This host is the **legacy production frontend**. It currently talks to nothing: the n8n EPE workflows on `92.51.45.147:5678` were deactivated in this same day. The bundle still points at that URL.

The API a replacement backend must satisfy is in [`docs/API_CONTRACT.md`](./API_CONTRACT.md).

---

## 1. Access path and user

| Field | This session |
|-------|----------------|
| Public URL | `http://135.232.120.40:8080` (HTTP only, no domain) |
| SSH from this Mac | **TCP/22 timeout** (`ssh` BatchMode, 6s). Not in `~/.ssh/config` or `known_hosts`. WebStorm `sshConfigs.xml` has only `92.51.45.147`. |
| SSH from `92.51.45.147` | TCP/22 **not open** within 4s. |
| SSH user | **Not established this session.** December 2025 deploy conversation used Windows user `Administrator`. |
| RDP | **TCP/3389 open** from this Mac and from the n8n VPS. |
| Key / password used | None. No ControlMaster socket exists for this host. |

**Consequence:** this inventory has no shell on the box. Disk path, Node version, service name, Task Scheduler, Docker, and whether source or git exist on disk are inferred from HTTP fingerprints plus the 2025-12-23 deploy conversation, and are labeled accordingly.

Historical deploy conversation «Перенос проекта на сервер» (2025-12-23): Windows Server 2022; copy the Vite `dist/` to `C:\WebApps\evaluation-portal\`; run global npm `serve` as a Windows service:

```
C:\Program Files\nodejs\node.exe
C:\Users\Administrator\AppData\Roaming\npm\node_modules\serve\build\main.js -s . -l tcp://0.0.0.0:8080
```

Working directory `C:\WebApps\evaluation-portal`. Logs (instructed, **unverified** now): `C:\WebApps\evaluation-portal\logs\service.log` and `error.log`. IIS was an alternative that was **not** what is serving `:8080` today (see below).

---

## 2. What serves :8080

**Vercel `serve` (npm package) in SPA mode (`-s`), listening on `0.0.0.0:8080`.** Not nginx, not IIS, not Vite preview, not a Node API.

Live HTTP fingerprint (GET `/`, GET `/register`, GET `/this-path-does-not-exist-xyz` — all identical):

| Header | Value |
|--------|--------|
| Status | `200 OK` |
| `Content-Type` | `text/html; charset=utf-8` |
| `Content-Disposition` | `inline; filename="index.html"` |
| `Accept-Ranges` | `bytes` |
| `ETag` | `"55461a6b7b8d35ac0250749095bab5b970d0e5b3"` (SHA-1 of the file; `serve-handler` style) |
| `Vary` | `Accept-Encoding` |
| `Keep-Alive` | `timeout=5` |
| `Server` | **absent** |

Unknown paths rewrite to `index.html` (SPA fallback). Real files (`/assets/index-C9WM9w28.js`, `/assets/index-De9_K8gc.css`, `/vite.svg`) return their own `Content-Disposition: inline; filename="…"` and a distinct ETag. That combination is `serve` / `serve-handler`, not IIS (`Server: Microsoft-IIS/…`) and not nginx (`Server: nginx`).

Port **80** is a different process: `Server: Microsoft-HTTPAPI/2.0`, HTTP 404 HTML, no site. That is HTTP.sys with nothing bound. Confirms Windows; does **not** serve the portal.

---

## 3. Where the files live

| Path | Evidence |
|------|----------|
| `C:\WebApps\evaluation-portal\` | Historical deploy instructions. **Unverified on disk this session.** |
| Served tree (proven by HTTP) | `index.html`, `assets/index-C9WM9w28.js` (330 550 bytes), `assets/index-De9_K8gc.css` (83 482 bytes), `vite.svg` (1 497 bytes) |
| Not present at the web root | `package.json`, `src/`, `.git/HEAD`, `.env`, `web.config`, source map, xlsx import template — all SPA-fallback to `index.html` |

No directory listing. `GET /assets/` returns `index.html`.

---

## 4. Source vs artifact vs git

**On the host, only a Vite production build artifact is reachable.** There is no source tree, no source map, no `package.json`, no `.git` over HTTP.

**That artifact is not in git.**

| Location | What is there |
|----------|----------------|
| This host | Hashed `dist/` files only (see §3). |
| GitHub `a787747/my-react-project` (this repo) | **32 tracked files, 2 commits** (`9719998` «Мой первый коммит», `78dbeb1` «save»). No `dist/`. No hashed `index-C9WM9w28.js`. |
| Local working tree | Current `src/` (~100 files) is **mostly untracked**. Endpoint map in `src/config/api.js` is **byte-identical in path list** to the object compiled into the live bundle. A fresh local `dist/` was **not** built this session, so byte-identity of JS/CSS hashes is **unverified**. |

**The running frontend has no version history on the server and almost none in git.** Restoring or diffing a past production bundle cannot be done from git. The only copy of what users actually load is the files on this Azure VM (and this session’s download under `/tmp/epe-fe/`, not kept in the repo).

The live `index.html` is the production transform of the repo’s `index.html` (same title, fonts, theme-color) with Vite hashed script/link tags instead of `/src/main.jsx`.

---

## 5. Stack, build, Node, dependencies

From the **shipped bundle** plus this repo’s `package.json` (the config that produces that kind of build):

| Piece | Version / command | Proven how |
|-------|-------------------|------------|
| UI | React 19 (`react` / `react-dom` in bundle error URLs and `package.json` `^19.2.0`) | bundle + lockfile |
| Router | React Router 7 | bundle string `reactrouter.com/en/main/routers/picking-a-router` + `package.json` `^7.10.1` |
| HTTP | axios 1.x | interceptor code in bundle + `package.json` `^1.13.2` |
| Charts | recharts 3.x | `package.json`; present in admin/analytics pages of the bundle |
| Icons | lucide-react | bundle SVG helper + `package.json` |
| CSS | Tailwind 3 + hashed `index-De9_K8gc.css` | build output |
| Bundler | Vite 7 (rolldown-vite `7.2.5` in `package.json`) | hashed assets, `vite.svg` |
| Build command | `npm run build` → `vite build` | `package.json` |
| Dev | `vite` / `vite preview` | `package.json` — **not** what production uses |
| Production static server | npm `serve` `-s` `-l tcp://0.0.0.0:8080` | HTTP fingerprint + 2025-12-23 instructions |
| Node on this Azure VM | **Unverified.** Instructed path `C:\Program Files\nodejs\node.exe`. No `engines` in `package.json`. |
| Node on this Mac | not relevant to production | — |

Runtime dependencies of the SPA (from `package.json`): `axios`, `clsx`, `lucide-react`, `react`, `react-dom`, `react-router-dom`, `recharts`, `tailwind-merge`, `xlsx-js-style`. The xlsx import template is **not** deployed (`/шаблон_импорта_сотрудников.xlsx` → SPA fallback).

---

## 6. API base URL (where it is configured)

In **source** (`src/config/api.js`):

```js
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://92.51.45.147:5678/webhook';
```

In the **shipped bundle** the string `VITE_API` does not appear. The compiled constant is the default:

```
http://92.51.45.147:5678/webhook
```

Login **duplicates** that URL, bypassing the map:

```
http://92.51.45.147:5678/webhook/auth/login
```

Both copies are in the live JS. There is no runtime env file on the static host that can change this without a rebuild.

Full contract: [`docs/API_CONTRACT.md`](./API_CONTRACT.md).

---

## 7. Client-side auth

| What | Fact |
|------|------|
| After login | `localStorage.user` = JSON of `response.data.user`; `localStorage.token` = `response.data.token` |
| Session restore | `UserContext` reads **only** `localStorage.user` on load. Presence of that JSON is “logged in”. Token is not validated. |
| Header | `apiClient` (axios) request interceptor: if `localStorage.token` is set, send `Authorization: Bearer <token>`. |
| Login request | raw `axios.post`, **no** interceptor, **no** `Authorization`. |
| 401 handling | interceptor clears `user`+`token` and redirects to `/login`. |
| What the token is | n8n login workflow returns `token: 'fake-jwt-' + user.id`. Not a JWT. Backend webhooks do not read `Authorization` (already established on the n8n side). |

**The client does send an Authorization header on every `apiClient` call. The backend never uses it.** Spoofing `localStorage.user` with `"role":"admin"` is enough to see admin routes. Calling admin webhooks needs no token at all.

---

## 8. Role handling — client-only

**The client decides what an admin sees. It does not ask the server for a permission set.**

1. Login returns `user.role` (and the rest of the `users` row minus `password_hash`). That object is stored in `localStorage` and trusted forever.
2. `App.jsx` gates: `ProtectedRoute` (any stored user), `AdminRoute` (`admin` \| `c_level` \| `hr`), `ManagerRoute` (`admin` \| `c_level` \| `hr` \| `manager`), `HRRoute` (`hr` only). All use `user.role` from context.
3. `src/utils/permissions.js` is a pure function of that string.
4. `Sidebar.jsx` hides/shows groups from `safeUser.role` and flags on the stored user (`has_subordinates`, `has_manager_subordinates`).
5. API calls that need a user id send `user.id` / `user.role` as **query or body fields** chosen by the client (`/api/employees?user_id=&role=`, score-correction `evaluator_id`, etc.). The server does not bind them to a session.

This is a finding, not a hypothesis.

---

## 9. Anything else on the host

Probed from this workstation (3s timeout unless noted). **Open** means TCP connect succeeded. **Timeout** means filtered or not listening; this is not a full port scan.

| Port | Result | What it is |
|------|--------|------------|
| 80 | open | HTTP.sys, `Microsoft-HTTPAPI/2.0`, 404. Not the portal. |
| 443 | timeout | No TLS for the portal. `curl -kI https://135.232.120.40/` did not complete a handshake in 8s. |
| 3389 | open | RDP (`ms-wbt-server`). Public. |
| 8080 | open | Portal (`serve`). Public, HTTP-only. |
| 22, 135, 139, 443, 445, 993, 995, 1433, 2200, 2222, 3000, 3306, 4173, 5000, 5432, 5678, 5985, 5986, 8000, 8081, 8443, 9000, 9443, 10050, 22222, 5357, 47001 | timeout (3s, scan completed) | No SSH, TLS, SMB, WinRM, Postgres, n8n, or extra HTTP from here. |

From `92.51.45.147`: 80, 3389, 8080 open; 22 not.

No cron/Task Scheduler/Docker inventory — no shell. IIS feature may be installed (HTTP.sys on 80) but has no site. Docker on this VM: **unverified**.

`:8080` is reachable from the public internet over plain HTTP. So is RDP.

---

## 10. Secrets in the shipped bundle

Searched the live `index-C9WM9w28.js` (328 611 chars) for URLs, `api_key` / `secret` / `password` assignments, `postgres://`, `mongodb://`, `sk-`, `AIza`, `AKIA`, Bearer literals.

| Found | Not a credential |
|-------|------------------|
| `http://92.51.45.147:5678/webhook` and `…/webhook/auth/login` | Hard-coded backend location (HTTP). |
| `Authorization: Bearer ${token}` | Reads `localStorage`, not a baked-in key. |
| `http://localhost` | axios / lib default. |
| SVG / React / ungap URLs | libraries. |

**No API keys, connection strings, or passwords in the bundle.** Login compares the password on the n8n side (plaintext equality to `password_hash`); that is not in this JS.

Google Fonts are loaded from `fonts.googleapis.com` in `index.html` (not a secret).

---

## 11. Findings (frontend host)

1. **Production is public HTTP on :8080** with a hard-coded HTTP API URL. Credentials would travel in cleartext if n8n were on.
2. **RDP :3389 is public.** SSH :22 is not reachable from this network. The access path Alexander actually uses was not proven this session.
3. **No git history for the running UI.** Artifact-only deploy; repo tracks 32 files.
4. **Auth is decorative.** Fake token in `localStorage`; `Authorization` sent and ignored; admin UI is a client `role` string.
5. **SPA fallback hides 404s.** Missing source files look like 200 HTML. That is expected for `serve -s`, not a leak of source.
6. **Port 80 HTTP.sys 404** — unused Windows HTTP stack facing the internet.

---

## 12. Unverified

- Exact on-disk path and whether `C:\WebApps\evaluation-portal` still exists.
- Windows service name / NSSM / WinSW / Task Scheduler.
- Node.js version on the VM.
- Whether source or a git clone exists somewhere else on the disk.
- Azure NSG / firewall rules (why 22 is dark and 3389/8080 are not).
- Other processes bound to localhost-only ports.
- Whether `serve` was installed globally vs a copied `node_modules`.
- Byte-identity of this bundle with a fresh `npm run build` of the current working tree.

---

## 13. Session control

- SSH to this host: none.
- Server mutations: none.
- EPE webhooks: not called.
- Repo artifacts: this file and `docs/API_CONTRACT.md`.
