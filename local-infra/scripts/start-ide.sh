#!/usr/bin/env bash
set -Eeuo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# Starting the IDE backend starts only PostgreSQL; IntelliJ launches Odoo on the host.
exec "$SCRIPT_DIR/db-ide.sh" start
