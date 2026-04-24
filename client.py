#!/usr/bin/env python3
'''
Load client: connects to all alive servers, prints per-node loads and the
cluster-wide averages (1, 5, 15 min).

Machine list is fetched live from the Telecom Paris API. Falls back to a
local file if the API is unreachable.

Usage: python3 client.py [port] [max_machines]
'''
import concurrent.futures
import json
import socket
import sys
import time
import urllib.request

PORT          = int(sys.argv[1]) if len(sys.argv) > 1 else 54321
MAX_MACHINES  = int(sys.argv[2]) if len(sys.argv) > 2 else 100
TIMEOUT       = 5
API_URL       = "https://tp.telecom-paris.fr/ajax.php?_="
FALLBACK_FILE = "machines_alive.txt"


def get_machines(max_count: int = 100) -> list:
    """Fetch online machine hostnames from the Telecom Paris API."""
    url = API_URL + str(int(time.time() * 1000))
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        available = [entry[0] for entry in data["data"] if entry[1] is True]
        return available[:max_count]
    except Exception as e:
        print(f"[WARN] API request failed ({e}), falling back to {FALLBACK_FILE}")
        try:
            with open(FALLBACK_FILE) as f:
                return [l.strip() for l in f if l.strip()][:max_count]
        except FileNotFoundError:
            print(f"error: {FALLBACK_FILE} not found and API unreachable.")
            sys.exit(1)


def query(host):
    try:
        # Try all resolved addresses (IPv6 and IPv4) until one succeeds.
        last_err = None
        for af, socktype, proto, _, sa in socket.getaddrinfo(
                host, PORT, type=socket.SOCK_STREAM):
            try:
                with socket.socket(af, socktype, proto) as s:
                    s.settimeout(TIMEOUT)
                    s.connect(sa)
                    chunks = []
                    while True:
                        b = s.recv(1024)
                        if not b:
                            break
                        chunks.append(b)
                data = b''.join(chunks).decode().strip()
                l1, l5, l15 = map(float, data.split())
                return host, l1, l5, l15
            except OSError as e:
                last_err = e
                continue
        raise last_err or OSError('no address')
    except Exception:
        return host, None, None, None


def main():
    print(f"Fetching up to {MAX_MACHINES} available machines from API...")
    machines = get_machines(MAX_MACHINES)
    print(f"Got {len(machines)} machines.\n")

    print(f'Connecting to {len(machines)} machines on port {PORT}...\n')
    results, failed = [], []

    with concurrent.futures.ThreadPoolExecutor(max_workers=50) as ex:
        for fut in concurrent.futures.as_completed(
                {ex.submit(query, m): m for m in machines}):
            host, l1, l5, l15 = fut.result()
            if l1 is None:
                failed.append(host)
                print(f'  {host:<35} UNREACHABLE')
            else:
                results.append((host, l1, l5, l15))
                print(f'  {host:<35} load: {l1:.2f}  {l5:.2f}  {l15:.2f}')

    n = len(results)
    print(f'\n{"=" * 55}')
    print(f'  Nodes responded: {n}/{len(machines)}')
    if n:
        a1 = sum(r[1] for r in results) / n
        a5 = sum(r[2] for r in results) / n
        a15 = sum(r[3] for r in results) / n
        print(f'  Avg load  1 min : {a1:.4f}')
        print(f'  Avg load  5 min : {a5:.4f}')
        print(f'  Avg load 15 min : {a15:.4f}')
    print('=' * 55)
    if failed:
        print(f'\n  Unreachable ({len(failed)}): {", ".join(failed)}')


if __name__ == '__main__':
    main()
