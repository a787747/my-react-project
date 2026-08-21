# EPE — project rules (ports, naming, diagnosis)

This file did not exist. `AGENTS.md` pointed at it for a reserved port range that was never written down. These are the **live facts** from `infra/caddy-compose.yml`, `infra/n8n-stack.yml`, and `~/.ssh/config` Host `epe-vps-tunnel`, verified 2026-08-20 and re-checked 2026-08-21 (ports and firewall chain unchanged; the throwaway-stand and local-tooling sections were added then, and the backups section after the BUG-032 fix). There is no separate reserved-range document.

## Compose and names

| Thing | Fact |
|---|---|
| Caddy Compose project | `name: epe-proxy` (`infra/caddy-compose.yml`; remote `/opt/epe-proxy`) |
| Caddy volumes | `epe_proxy_caddy_data`, `epe_proxy_caddy_config` |
| Caddy static root | host `/var/www/epe` → `/srv/epe` (read-only in the container) |
| n8n | **not** this repo’s Compose. Running definition is the Portainer stack. `infra/n8n-stack.yml` is the documented pin: `n8nio/n8n@sha256:0a65e6e5995c19e0cf7e83d6b08ffa6c1898e8a53ff1658e6e7b22e68576c673`, `restart: unless-stopped`, network `n8n_default` (external) |
| Diagnose | `epe-proxy`: `docker compose` in that project. n8n/Postgres: `docker exec` on `n8n-n8n-1` / `postgres_n8n`. Do not use `docker ps -a` as the inventory. |

## Ports this project uses

Public (Caddy): **80**, **443** (TCP + UDP 443).

Host-published, **not** public: n8n **5678** (DROP from the internet; Caddy is the only path).

SSH tunnel alias `epe-vps-tunnel` (avoids the changing home-IP allowlist):

| Local | Remote | Service |
|---|---|---|
| `127.0.0.1:25432` | `127.0.0.1:5432` | `postgres_n8n` (live `epe_2026` + n8n `postgres`) |
| `127.0.0.1:25431` | `127.0.0.1:5431` | `postgres_main` (foreign) |
| `127.0.0.1:25678` | `127.0.0.1:5678` | n8n editor / API |
| `127.0.0.1:29000` | `127.0.0.1:9000` | Portainer |

Proof stands (created and destroyed per brief, never left running): n8n **25679** on VPS loopback; local
`vite` **5199** / **5299** on the laptop. See the stand section below.

Firewall (not a port-range file): 80/443 open; 5432/5431/8000/9000/2377/7946/4789 restricted **to one
allowlisted source IP** (Alexander's home address — it changes, which is why the SSH tunnel exists);
5678 DROP on `eth0`. SSH 22 stays public. Re-read from `iptables -S EPE-DOCKER-USER` on 2026-08-21.

## Throwaway proof stands (the pattern that produced the 20–21 Aug proofs)

Nothing is proven against live. Every behavioural proof since 2026-08-20 ran on an isolated stand: an n8n
container on the **VPS loopback** talking to a throwaway database restored from a dated dump of live.
`scripts/setup_hierarchy_throwaway.sh` is the reference implementation; `scripts/seed_*_throwaway.sql`
supply the fixtures and `scripts/prove_*.py` record the checks.

| Thing | Fact |
|---|---|
| Stand n8n container | `epe-prelaunch-n8n` (20 Aug) / `epe-hier-n8n` (21 Aug) — **same pinned image digest as live**, `--network n8n_default` |
| Stand port | `127.0.0.1:25679` **on the VPS**, published to loopback only. Reach it from the laptop with `ssh -N -L 25679:127.0.0.1:25679 root@92.51.45.147`, then `http://127.0.0.1:25679/webhook` |
| Throwaway DB | `epe_prelaunch_<stamp>` / `epe_hier_<stamp>`, restored from a dated dump of live into `postgres_n8n`. **The prefix is load-bearing** — the drop loop refuses any name that does not match it, so `epe_2026` can never be a candidate |
| Local frontend against the stand | `vite` on `:5199` (20 Aug) / `:5299` (21 Aug) with `VITE_DEV_API_PROXY=http://127.0.0.1:25679`. `.claude/launch.json` carries the `epe-hier-vite` launcher |
| Teardown | Drop the DB and remove the container at the end of the brief. A stand DB is a **second copy of production personal data** outside the backup regime — it is not a place to leave things |

Stand traps that already cost time, all of them silent:

- `docker cp <dir> container:/path` **nests** the directory when the target already exists, leaving the
  previous file at the top level — which is then what `n8n import:workflow --input=<dir>/` imports. Clear
  the container-side directory first.
- `n8n import:workflow` **always assigns a new workflow id**; the file's `id` is ignored. A stand
  accumulates duplicates, and the old one may still be the active definition. Deactivate the old ids and
  verify the active graph node-for-node against the repo before trusting any proof.
- Generate the workflow from its builder script; do **not** copy a tracked top-level export. At least one
  of those exports is stale against live (BUG-028).
- A proof artifact must record the compared values, not a summary string. A run that compared nothing
  writes the same slogan as a run that compared everything.

## Backups

Two cron jobs on `92.51.45.147`, both writing gzipped `pg_dump -Fc` files into `/root/backups/epe/daily`
with `chmod 600` and a **14-day** window. `0 3 * * * backup-performance-db.sh` dumps the read-only 2025
archive (`postgres`, schema `performance_db`) — pre-existing, do not edit. `20 3 * * * backup-epe-live.sh`
(added 2026-08-21 for BUG-032) dumps the **live** `epe_2026` in full and the **n8n application schema**
(`postgres`, schema `public`: 58 workflows, credentials, settings, webhook registrations) — before that
date neither had any backup at all. Pruning is keyed on the filename stem, so neither job can ever delete
the other's files. Failure leaves a non-zero exit, a `FAIL` line in `/root/backups/epe/backup.log` and
`FAIL` in `/root/backups/epe/backup-epe-live.status`; there is no MTA on the host, so that status file is
the alarm — `cat /root/backups/epe/backup-epe-live.status` must read `OK` with today's date. **To restore:**
`/root/backups/epe/verify-restore.sh <stem> <live_db> [schema]` gunzips the newest dump of that stem into a
throwaway `epe_bkverify_*` database, row-counts every table against live, and drops the throwaway — run it
first, read the data out of the throwaway, and only then touch live. Tracked copies of both scripts live in
`scripts/`; the host copies are authoritative. **There is still no off-host copy** (BUG-014): all three
stems are on one disk. `N8N_ENCRYPTION_KEY` is a Portainer stack environment variable and is in no dump —
restoring the n8n schema under a different key gives unusable credentials.

## Local tooling

`scripts/deploy_epe_frontend.sh` calls `rg` in both of its safety gates. Ripgrep is **not** installed on
the delivery laptop, so the deploy fails closed until it is (BUG-040). Run the two gates by hand — legacy
`:5678` absent, `/webhook` base present — before any shim.

## Hard constraints (repeat)

No `docker system/volume/network prune`. No `docker compose down -v`. Do not stop or remove a container this project does not own. No bind mounts outside the project directory on new Compose work. Named volumes keep the `epe_` prefix.
