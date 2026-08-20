#!/bin/bash
# Restrict published DB/Portainer/Swarm ports to one admin IPv4.
# 22 (ssh) stays public. 80/443 are public through Caddy; direct n8n 5678 is blocked.
set -euo pipefail

ALLOW_IP="188.137.254.191"
IFACE="eth0"
CHAIN_FWD="EPE-DOCKER-USER"
CHAIN_IN="EPE-INPUT"

ensure_jump() {
  local table="$1" parent="$2" child="$3"
  if ! "$table" -C "$parent" -j "$child" 2>/dev/null; then
    "$table" -I "$parent" 1 -j "$child"
  fi
}

apply_family() {
  local ipt="$1"

  if ! "$ipt" -nL DOCKER-USER >/dev/null 2>&1; then
    echo "DOCKER-USER missing; is docker running?" >&2
    return 1
  fi

  "$ipt" -N "$CHAIN_FWD" 2>/dev/null || "$ipt" -F "$CHAIN_FWD"
  "$ipt" -N "$CHAIN_IN" 2>/dev/null || "$ipt" -F "$CHAIN_IN"

  "$ipt" -A "$CHAIN_FWD" -m conntrack --ctstate ESTABLISHED,RELATED -j RETURN
  "$ipt" -A "$CHAIN_IN" -m conntrack --ctstate ESTABLISHED,RELATED -j RETURN

  # Public Caddy ports (match pre-DNAT host ports).
  for p in 80 443; do
    "$ipt" -A "$CHAIN_FWD" -i "$IFACE" -p tcp -m conntrack --ctorigdstport "$p" -j RETURN
  done
  "$ipt" -A "$CHAIN_FWD" -i "$IFACE" -p udp -m conntrack --ctorigdstport 443 -j RETURN

  # n8n is reachable only through Caddy or a local SSH tunnel.
  "$ipt" -A "$CHAIN_FWD" -i "$IFACE" -p tcp -m conntrack --ctorigdstport 5678 -j DROP
  "$ipt" -A "$CHAIN_IN" -i "$IFACE" -p tcp --dport 5678 -j DROP

  # Restricted Docker-published admin/database ports.
  local tcp_docker_ports="5432 5431 8000 9000"
  local p
  for p in $tcp_docker_ports; do
    if [ "$ipt" = "iptables" ]; then
      "$ipt" -A "$CHAIN_FWD" -i "$IFACE" -p tcp -s "$ALLOW_IP" -m conntrack --ctorigdstport "$p" -j RETURN
    fi
    "$ipt" -A "$CHAIN_FWD" -i "$IFACE" -p tcp -m conntrack --ctorigdstport "$p" -j DROP
  done

  # Swarm control/data ports are host listeners; DOCKER-USER never sees them.
  # Same DROP/ALLOW intent, on INPUT.
  for p in 2377 7946; do
    if [ "$ipt" = "iptables" ]; then
      "$ipt" -A "$CHAIN_IN" -i "$IFACE" -p tcp -s "$ALLOW_IP" --dport "$p" -j RETURN
    fi
    "$ipt" -A "$CHAIN_IN" -i "$IFACE" -p tcp --dport "$p" -j DROP
  done
  if [ "$ipt" = "iptables" ]; then
    "$ipt" -A "$CHAIN_IN" -i "$IFACE" -p udp -s "$ALLOW_IP" --dport 7946 -j RETURN
    "$ipt" -A "$CHAIN_IN" -i "$IFACE" -p udp -s "$ALLOW_IP" --dport 4789 -j RETURN
  fi
  "$ipt" -A "$CHAIN_IN" -i "$IFACE" -p udp --dport 7946 -j DROP
  "$ipt" -A "$CHAIN_IN" -i "$IFACE" -p udp --dport 4789 -j DROP

  # Same ports in DOCKER-USER (no-op today: Swarm listens on the host, not via DNAT).
  for p in 2377 7946; do
    if [ "$ipt" = "iptables" ]; then
      "$ipt" -A "$CHAIN_FWD" -i "$IFACE" -p tcp -s "$ALLOW_IP" -m conntrack --ctorigdstport "$p" -j RETURN
    fi
    "$ipt" -A "$CHAIN_FWD" -i "$IFACE" -p tcp -m conntrack --ctorigdstport "$p" -j DROP
  done
  if [ "$ipt" = "iptables" ]; then
    "$ipt" -A "$CHAIN_FWD" -i "$IFACE" -p udp -s "$ALLOW_IP" -m conntrack --ctorigdstport 7946 -j RETURN
    "$ipt" -A "$CHAIN_FWD" -i "$IFACE" -p udp -s "$ALLOW_IP" -m conntrack --ctorigdstport 4789 -j RETURN
  fi
  "$ipt" -A "$CHAIN_FWD" -i "$IFACE" -p udp -m conntrack --ctorigdstport 7946 -j DROP
  "$ipt" -A "$CHAIN_FWD" -i "$IFACE" -p udp -m conntrack --ctorigdstport 4789 -j DROP

  ensure_jump "$ipt" DOCKER-USER "$CHAIN_FWD"
  ensure_jump "$ipt" INPUT "$CHAIN_IN"
}

apply_family iptables
apply_family ip6tables
echo "epe-firewall applied allow_ip=$ALLOW_IP iface=$IFACE"
iptables -L EPE-DOCKER-USER -n --line-numbers
echo "--- INPUT ---"
iptables -L EPE-INPUT -n --line-numbers
