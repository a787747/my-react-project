# EPE — project rules (ports, naming, diagnosis)

This file did not exist. `AGENTS.md` pointed at it for a reserved port range that was never written down. These are the **live facts** from `infra/caddy-compose.yml`, `infra/n8n-stack.yml`, and `~/.ssh/config` Host `epe-vps-tunnel`, verified 2026-08-20. There is no separate reserved-range document.

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

Firewall (not a port-range file): 80/443 open; 5432/5431/8000/9000/2377/7946 restricted; 5678 DROP on `eth0`. SSH 22 stays public.

## Hard constraints (repeat)

No `docker system/volume/network prune`. No `docker compose down -v`. Do not stop or remove a container this project does not own. No bind mounts outside the project directory on new Compose work. Named volumes keep the `epe_` prefix.
