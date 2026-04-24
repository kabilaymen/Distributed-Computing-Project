#!/bin/bash
# Stop all load servers we own and clean up.
# Uses fuser -k on the port: reliably kills any process (ours) listening
# there, even orphaned ones from previous deploys.
# Usage: ./kill.sh [alive_file] [port]

set -uo pipefail

ALIVE_FILE="${1:-machines_alive.txt}"
PORT="${2:-54321}"
REMOTE_USER="kabil-25"
JUMP="ssh.enst.fr"
SERVER="server.py"
L_OPTS="-o StrictHostKeyChecking=no -o ConnectTimeout=15 -o BatchMode=yes -o LogLevel=ERROR"

if [[ ! -f "$ALIVE_FILE" ]]; then
    echo "No $ALIVE_FILE found. Nothing to kill."
    exit 0
fi

echo "Stopping servers on port $PORT..."

# shellcheck disable=SC2086
scp -q $L_OPTS "$ALIVE_FILE" "${REMOTE_USER}@${JUMP}:machines_kill.txt"

# shellcheck disable=SC2086
ssh $L_OPTS "${REMOTE_USER}@${JUMP}" bash -s <<REMOTE
set -uo pipefail
ROPTS="-o StrictHostKeyChecking=no -o ConnectTimeout=6 -o BatchMode=yes"
PORT=${PORT}
while IFS= read -r host; do
    [[ -z "\$host" ]] && continue
    result=\$(ssh -n \$ROPTS "\$host" "
        if fuser -k -TERM \${PORT}/tcp >/dev/null 2>&1; then
            sleep 0.2
            fuser -k -KILL \${PORT}/tcp >/dev/null 2>&1 || true
            rm -f ~/.server.pid
            echo killed
        else
            rm -f ~/.server.pid
            echo not_running
        fi
    " 2>/dev/null || echo unreachable)
    echo "  [\${result}]  \$host"
done < ~/machines_kill.txt

rm -f ~/machines_kill.txt ~/server.py
echo ""
echo "  Removed ~/server.py from NFS home."
REMOTE

rm -f "$ALIVE_FILE"
echo "  Removed $ALIVE_FILE."
echo ""
echo "All clean."
