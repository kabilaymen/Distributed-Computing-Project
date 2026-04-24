#!/usr/bin/env python3
'''
Load server: accepts TCP connections and sends CPU load averages (1/5/15 min).
Writes its PID to ~/.server.pid for clean shutdown by kill.sh.
Usage: python3 server.py [port]
'''
import atexit
import os
import signal
import socket
import sys

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 54321
PID_FILE = os.path.expanduser('~/.server.pid')


def cleanup():
    try:
        os.remove(PID_FILE)
    except OSError:
        pass


def get_load():
    with open('/proc/loadavg') as f:
        parts = f.read().split()
    return float(parts[0]), float(parts[1]), float(parts[2])


def main():
    with open(PID_FILE, 'w') as f:
        f.write(str(os.getpid()) + '\n')
    atexit.register(cleanup)
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))

    srv = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
    srv.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(('::', PORT))
    srv.listen(64)

    while True:
        conn, _ = srv.accept()
        try:
            l1, l5, l15 = get_load()
            conn.sendall(f'{l1} {l5} {l15}\n'.encode())
        except OSError:
            pass
        finally:
            conn.close()


if __name__ == '__main__':
    main()
