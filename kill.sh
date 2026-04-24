#!/bin/bash
# Stop all load servers and clean up.
# Uses PID file written by server.py; no fragile pattern matching.
# Usage: ./kill.sh [alive_file]

set -uo pipefail

ALIVE_FILE="${1:-machines_alive.txt}"
REMOTE_USER="kabil-25"
JUMP="ssh.enst.fr"
SERVER="server.py"
L_OPTS="-o StrictHostKeyChecking=no -o ConnectTimeout=15 -o BatchMode=yes -o LogLevel=ERROR"

if [[ ! -f "$ALIVE_FILE" ]]; then
    echo "No $ALIVE_FILE found. Nothing to kill."
    exit 0
fi

echo "Stopping servers..."

# shellcheck disable=SC2086
scp -q $L_OPTS "$ALIVE_FILE" "${REMOTE_USER}@${JUMP}:machines_kill.txt"

# shellcheck disable=SC2086
ssh $L_OPTS "${REMOTE_USER}@${JUMP}" bash -s <<'REMOTE'
set -uo pipefail
ROPTS="-o StrictHostKeyChecking=no -o ConnectTimeout=6 -o BatchMode=yes"
while IFS= read -r host; do
    [[ -z "$host" ]] && continue
    result=$(ssh -n $ROPTS "$host" \
        'xargs kill 2>/dev/null < ~/.server.pid; rm -f ~/.server.pid; echo killed' \
        2>/dev/null || echo unreachable)
    echo "  [${result}]  $host"
done < ~/machines_kill.txt

rm -f ~/machines_kill.txt ~/server.py
echo ""
echo "  Removed ~/server.py from NFS home."
REMOTE

rm -f "$ALIVE_FILE"
echo "  Removed $ALIVE_FILE."
echo ""
echo "All clean."
