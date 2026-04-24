#!/bin/bash
# Deploy load server on all reachable machines.
# Strategy:
#   1. ONE scp uploads server.py + machines.txt to the NFS home.
#   2. ONE ssh to the jump host runs a sequential loop there; each hop
#      jump -> lab is direct and fast.
# Usage: ./deploy.sh [port]

set -euo pipefail

PORT=${1:-54321}
REMOTE_USER="kabil-25"
JUMP="ssh.enst.fr"
SERVER="server.py"
ALL_MACHINES="machines.txt"
ALIVE_FILE="machines_alive.txt"
L_OPTS="-o StrictHostKeyChecking=no -o ConnectTimeout=15 -o BatchMode=yes -o LogLevel=ERROR"

if [[ ! -f "$ALL_MACHINES" ]]; then
    echo "error: $ALL_MACHINES not found."
    exit 1
fi

echo "=========================================="
echo "  Load Server Deployment  (port $PORT)"
echo "=========================================="
echo ""
echo "[1/2] Uploading $SERVER and $ALL_MACHINES via NFS..."
# shellcheck disable=SC2086
scp -q $L_OPTS "$SERVER" "$ALL_MACHINES" "${REMOTE_USER}@${JUMP}:"
echo "      Done."
echo ""
echo "[2/2] Starting server on each machine from jump host..."

# Unquoted heredoc: ${PORT} is expanded LOCALLY.
# Remote $-refs are escaped with backslash.
# shellcheck disable=SC2086
ssh $L_OPTS "${REMOTE_USER}@${JUMP}" bash -s <<REMOTE
set -uo pipefail
ROPTS="-o StrictHostKeyChecking=no -o ConnectTimeout=6 -o BatchMode=yes"
: > ~/machines_alive.txt
count=0
total=0

while IFS= read -r host; do
    [[ -z "\$host" ]] && continue
    total=\$((total + 1))
    result=\$(ssh -n \$ROPTS "\$host" \
        "nohup python3 ~/server.py ${PORT} >/dev/null 2>&1 & echo ok" \
        2>/dev/null || true)
    if [[ "\$result" == "ok" ]]; then
        echo "  [OK]  \$host"
        echo "\$host" >> ~/machines_alive.txt
        count=\$((count + 1))
    else
        echo "  [--]  \$host"
    fi
done < ~/machines.txt

echo ""
echo "  --> \$count / \$total machines deployed."
REMOTE

# shellcheck disable=SC2086
scp -q $L_OPTS "${REMOTE_USER}@${JUMP}:machines_alive.txt" "$ALIVE_FILE"
# shellcheck disable=SC2086
ssh -n $L_OPTS "${REMOTE_USER}@${JUMP}" "rm -f ~/machines_alive.txt ~/machines.txt" 2>/dev/null || true

ALIVE_COUNT=$(wc -l < "$ALIVE_FILE")
TOTAL=$(wc -l < "$ALL_MACHINES")
echo ""
echo "=========================================="
echo "  Alive: $ALIVE_COUNT / $TOTAL  -->  $ALIVE_FILE"
echo "=========================================="
echo ""
echo "Run client:  python3 client.py $PORT $ALIVE_FILE"
