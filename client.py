#!/usr/bin/env python3
'''
Load client: connects to all alive servers, prints per-node loads and the
cluster-wide averages (1, 5, 15 min).
Usage: python3 client.py [port] [machines_file]
'''
import concurrent.futures
import socket
import sys

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 54321
MACHINES_FILE = sys.argv[2] if len(sys.argv) > 2 else 'machines_alive.txt'
TIMEOUT = 5


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
    try:
        with open(MACHINES_FILE) as f:
            machines = [l.strip() for l in f if l.strip()]
    except FileNotFoundError:
        print(f'error: {MACHINES_FILE} not found. Run ./deploy.sh first.')
        sys.exit(1)

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
