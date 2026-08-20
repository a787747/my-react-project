# SERVER MAP — 92.51.45.147

Captured: 2026-08-12, approximately 20:59–21:05 UTC.  
Host: `3569961-foreignpay.twc1.net` (`92.51.45.147`).  
Method: read-only SSH via an already-open multiplexed session as `root`. No container, firewall, cron, schema, or config was changed in this session.  
Items not proven here are marked **unverified**.

This VPS is a **shared Timeweb host**. EPE is a tenant, not the owner. The hostname is `foreignpay`. Last year’s evaluation data lives in the same Postgres cluster as a live clinic catalog.

---

## How to classify a future action

Use this first. If the action is not in the table, treat it as **affects someone else too** until proven otherwise.

| Action | Blast radius | Why |
|--------|----------------|-----|
| `SELECT`/`UPDATE`/`DELETE` on `performance_db.*` only | **EPE only** (data) | Other products use other schemas. Still the same superuser `admin` — an unqualified table name can hit `public` or `new_scheme`. |
| Edit an EPE workflow whose name starts `API:` | **EPE + shared n8n process** | Same n8n container serves school-helper and `new_clinic/*`. A bad deploy/restart of n8n takes them down too. |
| Restart / recreate `n8n-n8n-1` | **EPE + foreign** | Active foreign webhooks: `school-helper`, `new_clinic/equipment`, `new_clinic/request`, `new_clinic/rooms`. |
| Restart / stop `postgres_n8n` | **EPE + foreign** | Holds n8n metadata, `performance_db`, `medical_equipment`, and `new_scheme` (108 079 equipment rows). |
| Unpublish host port `5432` | **Unverified clients + scanners** | n8n itself connects over Docker DNS hostname `postgres` (`172.18.0.3`), not via the published port. Who else uses `92.51.45.147:5432` is **unverified**. Clinic apps may. |
| Restart `postgres_main` | **Foreign only** (not EPE data) | Separate cluster. Contains `employees` (4) / `users` (1) plus leftover n8n tables. Shares network `n8n_default`. |
| Restart `redis_prod` | **Foreign** | Active workflow «Добавить оборудование» mentions Redis. EPE workflows do not. |
| Restart `portainer` | **Foreign** | Ports 8000/9000. Bind-mounts the Docker socket — this is the control plane for every container. |
| `docker compose down` in `/root/n8n` | **Dangerous / mismatch** | On-disk compose names the container `n8n` and is **not** what is running (`n8n-n8n-1`). Do not run it. |
| `docker compose down` using Portainer stack 5 / project `n8n` | **EPE + foreign** | That is the running n8n service. |
| Host reboot / `systemctl restart docker` | **Everyone, and n8n may stay down** | Proven 2026-07-10: n8n `RestartPolicy=on-failure` + clean SIGTERM (exit 0) → Docker does not start it. Others are `always`. |
| Truncate `postgres_n8n` json log | **Ops only** | Does not touch databases. No log rotation exists; this is the 1.6 GiB file. |
| `docker system prune` / volume prune | **Forbidden** | Leftover Mattermost and Metabase volumes still hold data. Anonymous volumes include both Postgres data dirs. |
| iptables / ufw / `DOCKER-USER` | **Everyone on published ports** | 5431, 5432, 5678, 8000, 9000 plus Swarm 2377/7946. |
| Change role `admin` password / `pg_hba` on `postgres_n8n` | **EPE + n8n + clinic** | Single login role for the whole cluster. n8n env has that password. |

There is **no** action that restarts Docker, n8n, or `postgres_n8n` and stays EPE-only.

---

## 1. Host

| Field | Value |
|-------|--------|
| Hostname | `3569961-foreignpay.twc1.net` |
| IPv4 | `92.51.45.147/24` on `eth0` (DHCP, metric 100) |
| IPv6 | link-local only on `eth0` (`fe80::c000:fff:fe06:190c/64`) |
| OS | Ubuntu 22.04.5 LTS (jammy), kernel `5.15.0-119-generic` |
| Timezone | `Europe/Moscow` (MSK, +0300), NTP active |
| CPU / RAM | 2 × AMD EPYC-Rome, 3.8 GiB RAM, **no swap** |
| Load (this session) | 0.00 / 0.15 / 0.31 |
| Uptime | 33 days 17 h, boot **2026-07-10 06:11 MSK** = 03:11 UTC |
| Interactive logins now | none (`who` empty; this session is `sshd` notty) |
| Human users | `root` only (uid 0). No other login-capable passwd entries. |
| SSH | `PermitRootLogin yes`, `PasswordAuthentication yes`. `/root/.ssh/authorized_keys` exists and is **empty** (0 bytes). Password-only, as hypothesized. |
| Provider extras | `qemu-guest-agent` running; `zabbix-agent-timeweb` listening on `0.0.0.0:10050`, `Server=92.53.116.12,92.53.116.111,92.53.116.119`. |

`/var/run/reboot-required` is present (`libc6`, `libssl3`). Unattended-upgrades has `Automatic-Reboot` **commented out** (Ubuntu default: do not reboot). A human reboot to clear that flag would take n8n down until someone starts it.

Last interactive `root` logins in `wtmp` (not this multiplexed session): 2025-08-30 from `38.180.133.3`; 2025-05-24 from `45.136.48.196`; earlier from `217.142.21.*`. Ownership of those IPs is **unverified**.

---

## 2. Containers

Five containers. Zero exited leftovers. Docker Engine **27.3.1**, Swarm **active** (1 node, 0 services, 0 stacks). Live restore **off**. No `/etc/docker/daemon.json`. Logging driver `json-file` with **empty LogOpts** (no `max-size`, no `max-file`).

Compose project label `n8n` exists on network `n8n_default`. The running n8n container was created from Portainer stack files under `portainer_data/_data/compose/5`, working-dir label `/data/compose/5` (that host path is gone; the files live in the Portainer volume).

### 2.1 Inventory

| Name | Owner | Image (running ID) | Created | Started | Status | Restart | Published ports | Networks | Volumes |
|------|-------|--------------------|---------|---------|--------|---------|-----------------|----------|---------|
| `n8n-n8n-1` | **SHARED** (EPE + foreign workflows) | `n8nio/n8n:latest` `b18bb0e36633` → n8n **1.121.3** | 2025-11-30 09:33:55Z | 2026-08-12 19:22:45Z | Up (this session ~2 h) | **`on-failure`** (retry 0) | `0.0.0.0:5678`, `[::]:5678` → 5678 | `n8n_default` `172.18.0.5` | **none** |
| `postgres_n8n` | **SHARED** | untagged `f0dfc903a663` (Config.Image still says `postgres:latest`; **Postgres 17.0**) | 2024-10-06 16:21:39Z | 2026-07-10 03:11:53Z | Up 4 weeks | `always` | `0.0.0.0:5432`, `[::]:5432` → 5432 | `n8n_default` `172.18.0.3`, hostname **`postgres`** | anonymous `a3bc67b0c768…` → `/var/lib/postgresql/data` (164.5 MB) |
| `postgres_main` | **FOREIGN** | `postgres:latest` `7fb32a7ac3a9` (**Postgres 17.5**) | 2025-05-24 12:43:29Z | 2026-07-10 03:11:53Z | Up 4 weeks | `always` | `0.0.0.0:5431`, `[::]:5431` → 5432 | `n8n_default` `172.18.0.4`, hostname `postgres_main` | anonymous `cea9302e00cf…` → `/var/lib/postgresql/data` (59.14 MB) |
| `redis_prod` | **FOREIGN** | `redis:latest` `0378d73bea8b` (Redis **8.0.3**) | 2025-08-03 15:54:40Z | 2026-07-10 03:11:53Z | Up 4 weeks | `always` | none on host (6379 inside `n8n_default` only) | `n8n_default` `172.18.0.2` | anonymous `d7d272e3389a…` → `/data` (529 B) |
| `portainer` | **FOREIGN** | `portainer/portainer-ce:latest` `ac6e9f6834c8` | 2025-03-17 10:38:47Z | 2026-07-10 03:11:53Z | Up 4 weeks | `always` | `0.0.0.0:8000` and `9000` (+ IPv6); 9443 unpublished | `bridge` `172.17.0.2` | `portainer_data`; **bind `/var/run/docker.sock`** |

`postgres_n8n` and `postgres_main` are **different clusters** (different data volumes, different major-patch versions). They share only the Docker network and the host.

n8n talks to Postgres at `DB_POSTGRESDB_HOST=postgres` / database `postgres` / user `admin`. That hostname is `postgres_n8n`, not `postgres_main`.

### 2.2 Images present but unused

| Image | Size | Used by |
|-------|------|---------|
| `n8nio/n8n` dangling `59b0698b0b36` (9 months old) | 969 MB | nothing |
| `postgres:latest` tag currently points at 17.5 | — | `postgres_main` only; `postgres_n8n` is pinned to the old ID |

`docker pull n8nio/n8n:latest` or `postgres:latest` would move tags. Recreating `n8n-n8n-1` after a pull would run n8n schema migrations on the **shared** `public` schema. Do not pull.

### 2.3 On-disk compose (do not apply)

| Path | What it is | Match to running? |
|------|------------|-------------------|
| `/root/n8n/docker-compose.yml` | Stub: image `n8nio/n8n`, `container_name: n8n`, port 5678, volume `~/.n8n`, only `N8N_SECURE_COOKIE=false` | **No.** Running name is `n8n-n8n-1`, no mounts, Postgres-backed. |
| Portainer `compose/5/docker-compose.yml` | Real n8n: Postgres env, `WEBHOOK_URL=http://92.51.45.147:5678/`, `restart_policy: on-failure`, external net `n8n_default` | **Yes** (this is the running service). |
| Portainer `compose/2` | Mattermost + Postgres 13, host port **8065** | Containers **not running**. Volumes still exist. |
| Portainer `compose/3` | Metabase, host port **3000** | Containers **not running**. Volume still exists. |

`/root/.n8n` exists (uid 1000) and is leftover from an older bind-mount era. Live n8n has **zero mounts**; state is in `postgres_n8n.public`.

---

## 3. Listening sockets

`ss -tulpn` this session. Anything not `docker-proxy` is a host process.

| Bind | Process | Owner | Reachable from this workstation (nc) |
|------|---------|-------|--------------------------------------|
| `0.0.0.0:22` / `[::]:22` | `sshd` | host | yes |
| `0.0.0.0:5432` / `[::]:5432` | `docker-proxy` → `postgres_n8n` | SHARED | yes |
| `0.0.0.0:5431` / `[::]:5431` | `docker-proxy` → `postgres_main` | FOREIGN | yes |
| `0.0.0.0:5678` / `[::]:5678` | `docker-proxy` → `n8n-n8n-1` | SHARED | yes |
| `0.0.0.0:8000` / `[::]:8000` | `docker-proxy` → `portainer` | FOREIGN | yes |
| `0.0.0.0:9000` / `[::]:9000` | `docker-proxy` → `portainer` | FOREIGN | yes |
| `0.0.0.0:10050` | `zabbix_agentd` (5 workers) | FOREIGN (Timeweb) | yes |
| `*:2377` | `dockerd` Swarm manager | host / Swarm | yes |
| `*:7946` tcp+udp | `dockerd` Swarm gossip | host / Swarm | tcp yes |
| `0.0.0.0:4789` udp | no userspace process (kernel VXLAN) | Swarm data path | **unverified** (UDP) |
| `127.0.0.53:53` | `systemd-resolved` | stock | localhost only |
| `eth0:68` udp | `systemd-network` DHCP | stock | n/a |

Not listening (connection refused from this workstation): 80, 443, 3000 (Metabase), 5001 (`finance_dashboard`), 8065 (Mattermost).

Host processes that are **not** containers: `sshd`, `zabbix_agentd`, `dockerd`/`containerd`, `systemd-*`, `cron`, `qemu-guest-agent`, `snapd`, `lxd` daemon (no instances). The only `node` process is n8n inside its container (uid 1000).

`finance_dashboard` at `/root/finance_dashboard` is an Express+`pg` app that would listen `0.0.0.0:${PORT||5001}`. **Not running.** Its `.env` was not read.

---

## 4. systemd and cron

### 4.1 Enabled, not stock Ubuntu cloud

| Unit | Why it is here |
|------|----------------|
| `docker.service` + `containerd.service` + `docker.socket` | Installed 2024-10-06 (symlink date). Owns every app container. |
| `zabbix-agent.service` | Package `zabbix-agent-timeweb`. Timeweb monitoring. |
| `snap.lxd.activate.service` / `snap.lxd.daemon.service` | LXD 5.0.8 snap. `lxc list` is **empty**. User `lxd` (uid 999) is the mapped uid of the Postgres/Redis container processes on the host — not a second database. |
| `/etc/systemd/system/dhclient6.service` | Custom Timeweb IPv6 oneshot. |
| `ufw.service` | Enabled, but **`ufw status` = inactive**. |
| `qemu-guest-agent.service` | Timeweb hypervisor channel. |
| `unattended-upgrades.service` | Stock-ish; Automatic-Reboot not enabled. |

No systemd unit named n8n, postgres, redis, or portainer. Those exist only as Docker containers.

### 4.2 Cron

- Root crontab: **none**.
- `/var/spool/cron/crontabs`: empty.
- No user crontabs.
- `/etc/cron.d/`: only stock `e2scrub_all`.
- `/etc/cron.daily|hourly|weekly|monthly`: stock apport/apt/dpkg/logrotate/man-db only.
- `/etc/crontab`: stock `run-parts` lines.

No application cron. n8n schedule workflow «Подкачка кэша в Redis» is **inactive**.

---

## 5. Disk and logs

| Filesystem | Size | Used | Avail | Use% |
|------------|------|------|-------|------|
| `/dev/vda1` ext4 `/` | 50 G | 22 G | **28 G** | 44% |
| inodes | 3.2 M | 402 K | 2.8 M | 13% |
| swap | none | | | |

`/var/lib/docker` = **9.1 G** (overlay2 6.5 G, containers 1.7 G, volumes 826 M, swarm 123 M).

### 5.1 Container json logs

| Container | Bytes this session | Notes |
|-----------|-------------------|--------|
| `postgres_n8n` | **1 710 309 517** (~1.59 GiB) | Still the brute-force log. Grew ~7 KiB vs 20:40 UTC capture. `docker logs --since 10m` FATAL count this session: **0**. |
| `postgres_main` | 19 126 904 (~18 MiB) | Same exposure pattern on 5431, smaller file. FATAL last 10 m: **0**. |
| `n8n-n8n-1` | 981 687 | |
| `redis_prod` | 295 573 | last write 2026-07-10 (container not logging much) |
| `portainer` | 277 184 | |

### 5.2 Rotation

| Mechanism | Present? |
|-----------|----------|
| `/etc/docker/daemon.json` `log-opts` | **No file** |
| Per-container `LogConfig.Config` | **{}** on all five |
| `/etc/logrotate.d/` docker rule | **None** |
| Host `logrotate` | weekly, rotate 4; covers rsyslog/ufw/apt — **not** Docker json logs |
| systemd journal | **4.0 G** under `/var/log/journal` |
| `/var/log` total | 4.2 G |

Headroom: **28 G free**. The 1.59 GiB `postgres_n8n` log can grow without bound. At the 10-minute sample this session it was quiet; historically it reached 1.7 GiB under internet scanning. No swap, so memory pressure is a separate risk (3.8 GiB, n8n RSS ~247 MiB this session).

---

## 6. Firewall reality

Checked: `iptables -S`, `iptables -L -n -v`, `iptables -t nat -S`, `nft list ruleset`, `ufw status`, `ip6tables -S`, `firewalld`, `fail2ban`.

| Control | Reality |
|---------|---------|
| ufw | **inactive** (unit enabled) |
| firewalld | inactive |
| fail2ban | not installed |
| iptables `INPUT` | **policy ACCEPT, zero rules** |
| iptables `OUTPUT` | policy ACCEPT |
| iptables `FORWARD` | policy DROP, then Docker chains |
| ip6tables `INPUT` | policy ACCEPT |
| nft | iptables-nft translation of the same Docker rules |

**`DOCKER` chain exists.**  
**`DOCKER-USER` chain exists and is empty** (`-A DOCKER-USER -j RETURN` only). Nothing in `DOCKER-USER` restricts any port.

Docker publishes and **accepts** DNAT for:

| Host port | Destination | DOCKER-chain packets this boot (approx) |
|-----------|-------------|------------------------------------------|
| 5432 | `172.18.0.3:5432` (`postgres_n8n`) | 72 202 ACCEPT / 70 663 DNAT |
| 5431 | `172.18.0.4:5432` (`postgres_main`) | 3 267 ACCEPT / 1 621 DNAT |
| 5678 | `172.18.0.5:5678` (n8n) | 8 ACCEPT / 8 DNAT (n8n was down most of this boot) |
| 8000 | `172.17.0.2:8000` (Portainer) | 61 436 ACCEPT |
| 9000 | `172.17.0.2:9000` (Portainer) | 4 635 ACCEPT |

**Nothing currently restricts 5432, 5431, 5678, 8000, or 9000** at the OS firewall. All five answered `nc` from this workstation (`212.36.169.90` previously recorded). Swarm **2377** and **7946** and Zabbix **10050** also answered.

A Timeweb panel / cloud security-group in front of the VPS is **unverified** (Alexander has no panel access). From this network, those ports are open.

---

## 7. Postgres cluster `postgres_n8n`

Single database `postgres` (62 MB), owner `admin`. `template0`/`template1` also owned by `admin`.

### 7.1 Roles

Login-capable role: **`admin` only**. `rolsuper=t`, `rolcreaterole=t`, `rolcreatedb=t`, `rolcanlogin=t`. No `postgres` role. No memberships besides defaults.

**Every application schema is owned by `admin`.** There is no separate clinic role. A password change, `DROP SCHEMA`, or `GRANT` on this cluster is never EPE-only.

Table grants in `performance_db`, `medical_equipment`, `new_scheme`, and `public` are **only to `admin`** (full DML).

### 7.2 Schemas (non-system)

| Schema | Owner | Tables | Sequences | Live `COUNT(*)` (this session) | Tenant |
|--------|-------|--------|-----------|--------------------------------|--------|
| `performance_db` | admin | 12 | 11 | users 73, evaluations 234, evaluation_scores 644, criteria 8, departments 14 | **EPE** |
| `new_scheme` | admin | 6 | 6 | departments 450, equipments **108 079**, rooms 8 381, user_log 21, manufacturer_blacklist 17, manufacturer_top_list 19 | **FOREIGN (clinic, live)** |
| `medical_equipment` | admin | 3 | 3 | departments 64, equipment 158, user_requests 8 | **FOREIGN (older clinic)** |
| `public` | admin | 52 | 12 | n8n metadata (58 workflows, 52 executions, 6 credentials, 1 n8n user) + leftover `equipment` (0) / `user_requests` (3) | **SHARED** (n8n + debris) |

`performance_db` tables: `criteria`, `departments`, `email_verification_codes`, `evaluation_periods`, `evaluation_scores`, `evaluations`, `global_settings`, `grades`, `invite_tokens`, `score_coefficients`, `score_corrections`, `users`. All owned by `admin`.

`new_scheme` tables: `departments`, `equipments`, `manufacturer_blacklist`, `manufacturer_top_list`, `rooms`, `user_log`. All owned by `admin`.

`medical_equipment` tables: `departments`, `equipment`, `user_requests`. All owned by `admin`.

`public` is the n8n 1.121 schema (`workflow_entity`, `execution_entity`, `credentials_entity`, `webhook_entity`, …) plus two non-n8n tables `equipment` and `user_requests`. Dropping `public` would destroy n8n for **all** products.

n8n credentials in this cluster (names only): `Postgres account`, `Redis account`, `SMTP account`, `OpenAi account`, `OpenRouter account`, `n8n account`. One Postgres credential is shared by EPE and clinic workflows.

---

## 8. n8n workflows (58)

Source this session: `postgres_n8n.public.workflow_entity` + `webhook_entity`, cross-checked with node text (`performance_db` / `medical_equipment` / `new_scheme` / `school` / `redis` / `new_clinic`). Counts: 58 total; 40 active not archived; 9 inactive not archived; 9 archived (all inactive). Matches the 2026-08-12 20:41 UTC dump.

Classification rule used:

- **EPE** — name starts `API:`, or nodes mention `performance_db`, or the diagnostic workflow that queries that schema.
- **FOREIGN** — nodes mention `medical_equipment` / `new_scheme` / `new_clinic` / `school` / Redis cache, or medical-request paths.
- **UNCLEAR** — no schema/path markers (manual stubs).

### 8.1 EPE (39)

38 named `API:*` plus archived `ДИАГНОСТИКА: Проверка БД (Простая версия)` (`debug/check-db`, not in live `webhook_entity`).

`API: Global CORS Handler` does **not** mention `performance_db`; it is EPE because it owns `admin/*` OPTIONS for the portal.

Active EPE = 36 `API:*` (including CORS). Archived EPE = 3× `API: Check Self Review` / `evaluation-details-by-user` duplicates + diagnostic.

### 8.2 Registered EPE webhook paths

Live `webhook_entity` (production URL prefix `http://92.51.45.147:5678/webhook/`):

```
admin/*                              OPTIONS
admin/save-user                      POST
api/admin/all-evaluations            GET
api/admin/clear-test-evaluations     OPTIONS, POST
api/admin/create-invite              POST
api/admin/evaluation-details-by-user GET
api/admin/evaluations-matrix         GET
api/admin/score-correction           POST
api/admin-users-data                 GET
api/analytics                        GET
api/check-evaluated                  GET
api/check-self-review                GET
api/criteria                         GET
api/employees                        GET
api/employee-self-review             GET
api/evaluation-details               GET
api/evaluation-history               GET
api/get-my-manager                   GET
api/hr/evaluation-status             GET
api/manager-subordinates-matrix      GET, OPTIONS
api/my-profile                       GET
api/periods                          GET
api/periods/activate                 POST
api/periods/create                   POST
api/register                         POST
api/score-coefficients               GET, POST
api/self-review-submit               POST
api/send-verification-code           POST
api/submit-evaluation                POST
api/update-evaluation                OPTIONS, POST
api/verify-code                      POST
api/verify-invite                    GET
auth/login                           POST
get-admin-data                       GET
manage-criteria                      POST
update-admin-data                    POST
```

Webhook `authentication` on these nodes is null (no n8n-level auth). That is an exposure, not a classification issue.

### 8.3 FOREIGN (17)

| id | name | active | archived | Markers | Registered path |
|----|------|--------|----------|---------|-----------------|
| `S8j5OeUNh4bIgAkH` | My workflow 7 | **true** | false | school | **`school-helper` POST** (this is the registered owner) |
| `qgXjtH5gCW4PgYDX` | school-helper | **true** | false | school | same path in nodes; **not** in `webhook_entity` (duplicate active) |
| `GJMngle3t7qxCLvj` | My workflow 9 | false | false | school | `school` (not registered) |
| `YZsxqjxUVhqh0Kfh` | Добавить оборудование | **true** | false | `new_scheme`, redis, `new_clinic` | `new_clinic/equipment` POST |
| `o4cSxegfSGGQKM7l` | Добавить комнаты | **true** | false | `new_scheme`, `new_clinic` | `new_clinic/rooms` POST |
| `Ro2zyLRh66D2S2n0` | Создать запрос | **true** | false | `new_scheme`, `new_clinic` | `new_clinic/request` POST |
| `94rbRP9YdzpKZF4n` | Подкачка кэша в Redis | false | false | `new_scheme`, redis, schedule | none (inactive) |
| `wqnss3lCadwp0Xo0` | Medical Equipment Selection | false | true | `medical_equipment` | `medical-request` |
| `EEmwqFpAOUHps5Ey` | My workflow | false | true | `medical_equipment` | `medical-request` |
| `rOnwCT3a7Vjl5gwl` | My workflow 2 | false | true | `medical_equipment` | `medical-request` |
| `6RGlnwOkBq80OImj` | My workflow 3 | false | false | `medical_equipment` | `medical-request` |
| `2XNmKIay2SlXRhDh` | My workflow 4 | false | true | `medical_equipment` | `medical-request` |
| `UH4VLFXjUjw9Rebq` | My workflow 5 | false | false | `medical_equipment` | `medical-request` |
| `T4LxzjGSjn8ltjKr` | My workflow 6 | false | false | `medical_equipment` | `medical-request` |
| `WWULXBimjGwAPbQc` | Workflow A | false | false | `medical_equipment` | `medical-request` |
| `VZkADNbuEeJgTBQk` | Workflow B | false | false | `medical_equipment` | executeWorkflow (not webhook) |
| `IilQ0V9Z8lDTPDV6` | get-equipment | false | true | name only, no schema hit | none |

Active foreign HTTP surface: `school-helper`, `new_clinic/equipment`, `new_clinic/request`, `new_clinic/rooms`.

### 8.4 UNCLEAR (2)

| id | name | active | Why unclear |
|----|------|--------|-------------|
| `dGoTHi9129S0FBTW` | My workflow 8 | false | manual trigger, no schema/path markers |
| `2NXBJwobb3I5R2nU` | My workflow 10 | false | manual trigger, no schema/path markers |

---

## 9. Other tenants on this host (not running as containers, still real)

| Tenant | Evidence | Running now? | Restart of Docker/host |
|--------|----------|--------------|------------------------|
| Clinic / `new_scheme` | 108 079 equipment rows; three active n8n webhooks | via n8n + `postgres_n8n` + `redis_prod` | **killed** |
| school-helper | two active workflows | via n8n | **killed** |
| `postgres_main` app | `employees` (4 rows: salary, hire_date, names, email), `users` (1 row: username, password_hash) | DB up; no matching process on 5001 | DB restart kills it; app not running |
| Mattermost | compose/2, volumes `mattermost_db-data` (86 MB) + `mattermost_mattermost-data` (298 MB), empty network `mattermost_mattermost-network` | **no** | volume prune would destroy it |
| Metabase | compose/3, volume `metabase_metabase-data` (26 MB), empty network `metabase_default` | **no** | volume prune would destroy it |
| `finance_dashboard` | `/root/finance_dashboard` Express+pg, default port 5001 | **no** | files only |
| Docker Swarm | manager on public IP, ports 2377/7946/4789 open, 0 services | Swarm node Ready | `docker swarm leave` / engine restart affects overlay |
| Timeweb Zabbix | host agent 10050 | yes | systemd brings it back after reboot |
| LXD | snap installed, **zero** instances | daemon only | snap/lxd restart is unrelated to EPE data |

Named volume `postgres_data` (65 MB, 0 links) is **not** attached to a running container. Which product it belongs to is **unverified**. Do not delete.

---

## 10. What a careless restart kills

| If you… | Then… |
|---------|--------|
| Reboot the VPS (including to clear `reboot-required`) | `postgres_n8n`, `postgres_main`, `redis_prod`, `portainer` come back (`always`). **`n8n-n8n-1` does not** (proven 2026-07-10). Zabbix/ssh/docker do. Clinic + EPE HTTP API stay down until n8n is started. |
| `systemctl restart docker` | Same as reboot for containers. Swarm state is on disk (`/var/lib/docker/swarm` 123 MB). Live restore is off, so all containers stop. |
| `docker restart n8n-n8n-1` | EPE API + school-helper + new_clinic webhooks drop for the restart window. Postgres stays up. |
| `docker restart postgres_n8n` | n8n loses DB (it will error). EPE + clinic schemas unavailable. n8n may survive if it reconnects — **unverified**. |
| `docker restart redis_prod` | Active «Добавить оборудование» Redis use breaks. EPE workflows do not mention Redis. |
| `docker restart portainer` | UI on 8000/9000 drops. Containers keep running. |
| `docker compose down` against project `n8n` | Stops `n8n-n8n-1`. Does not stop `postgres_n8n` (not in that compose file). |
| Stop/remove `postgres_n8n` volume `a3bc67b0c768…` | Destroys EPE + n8n + clinic data. Irreversible without backup. |
| `docker system prune -a --volumes` | Destroys Mattermost, Metabase, anonymous Postgres volumes, unused n8n image. **Do not.** |

---

## 11. Urgent observations (not remediated)

Recorded only. Out of scope to fix in this session.

1. `postgres_n8n` port 5432 and `postgres_main` port 5431 are on `0.0.0.0`, `INPUT` ACCEPT, reachable from the internet, single superuser `admin`, SSL off. `postgres_n8n` json log is 1.59 GiB with no rotation. Clinic data (108 k rows) sits behind the same role as EPE.
2. n8n editor and all webhooks including `auth/login` are on plain HTTP `:5678` with no webhook authentication.
3. Portainer `:8000`/`:9000` and Docker Swarm manager `:2377` are reachable from this workstation. Portainer has the Docker socket.
4. n8n will not survive the next clean reboot.
5. `/var/run/reboot-required` is set (`libc6`, `libssl3`). Do not reboot to clear it until n8n restart policy is changed — and that change is **not EPE-only** (it also keeps school-helper and new_clinic up).

---

## 12. Unverified

- Timeweb cloud firewall / security groups in front of `0.0.0.0`.
- Who connects to `5432` / `5431` besides internet scanners and Docker-internal n8n (`172.18.0.5`).
- Whether any remote `admin` login to Postgres ever succeeded (`log_connections` off — see `docs/INCIDENT_2026-08-12.md`).
- Owner identity of school-helper, new_clinic, Mattermost, Metabase, `finance_dashboard`, `postgres_main.employees`.
- Whether `finance_dashboard` is meant to use `postgres_main`.
- Contents of named volume `postgres_data`.
- Whether UDP 4789 is filtered upstream.
- IPv6 public address: none observed on `eth0` besides link-local; IPv6 publish of Docker ports still exists on `[::]`.
- `PROJECT_RULES.md` is missing from the repo; port reservation rules were not verified from a project file.

---

## 13. Session control

- SSH: existing ControlMaster socket `/tmp/epe-ssh-%C`; password not written to any file this session.
- Server mutations: none.
- Repo artifact: this file.
