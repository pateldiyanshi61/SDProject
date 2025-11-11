#!/usr/bin/env bash
set -euo pipefail

# Configuration (can be set via docker-compose environment)
MONGOS_HOST="${MONGOS_HOST:-mongos:27017}"
SHARD_HOSTS="${SHARD_HOSTS:-shard1:27018 shard2:27018}"   # space-separated host:port
DB_TO_CHECK="${DB_TO_CHECK:-banking}"
AUTO_CLEAN="${AUTO_CLEAN:-false}"    # set to "true" to enable automated dump -> drop -> restore
DUMP_DIR="/tmp/shard_dumps"

echo "=== init-shard-entrypoint starting ==="
echo "MONGOS: $MONGOS_HOST"
echo "SHARD HOSTS: $SHARD_HOSTS"
echo "DB TO CHECK: $DB_TO_CHECK"
echo "AUTO_CLEAN: $AUTO_CLEAN"

# Wait for mongos to be ready
echo "Waiting for mongos to be healthy..."
until mongosh --host "$MONGOS_HOST" --quiet --eval "db.adminCommand('ping').ok" >/dev/null 2>&1; do
  echo "Waiting for mongos ($MONGOS_HOST) ..."
  sleep 2
done
echo "mongos is healthy"

# Helper: check a mongod for the presence of DB_TO_CHECK
function check_db_present() {
  local hostport="$1"
  mongosh --host "$hostport" --quiet --eval "db.adminCommand({ listDatabases: 1 }).databases.map(d => d.name).indexOf('$DB_TO_CHECK') >= 0" | tr -d '\n'
}

# Loop shards and decide
mkdir -p "$DUMP_DIR"
for h in $SHARD_HOSTS; do
  echo "Checking host $h for database '$DB_TO_CHECK'..."
  present="$(check_db_present "$h")" || present="false"
  if [[ "$present" == "true" ]]; then
    echo " -> Found database '$DB_TO_CHECK' on $h"
    if [[ "$AUTO_CLEAN" != "true" ]]; then
      echo "ERROR: $h contains database '$DB_TO_CHECK'. Init will stop to avoid data loss."
      echo "Set AUTO_CLEAN=true to automatically dump & drop, or manually inspect and remove the DB from $h."
      exit 2
    else
      # AUTO_CLEAN flow: dump, drop on shard, add shard later and restore via mongos
      echo "AUTO_CLEAN enabled: dumping $DB_TO_CHECK from $h to $DUMP_DIR..."
      mongodump --host "$h" --db "$DB_TO_CHECK" --out "$DUMP_DIR/$(echo $h | tr ':' '_')" \
        || { echo "mongodump failed for $h"; exit 3; }
      echo "Dump complete. Dropping $DB_TO_CHECK on $h..."
      mongosh --host "$h" --quiet --eval "db.getSiblingDB('$DB_TO_CHECK').dropDatabase()" \
        || { echo "Failed to drop db on $h"; exit 4; }
      echo "Dropped $DB_TO_CHECK on $h"
    fi
  else
    echo " -> No local $DB_TO_CHECK on $h"
  fi
done

# Run the original init-sharding.js against mongos
echo "Running init-sharding.js on mongos..."
if ! mongosh --host "$MONGOS_HOST" --file /init-sharding.js; then
  echo "init-sharding.js failed"
  exit 5
fi

# If AUTO_CLEAN used and we dumped any dumps, restore them via mongos so sharding config is respected
if [[ "$AUTO_CLEAN" == "true" ]]; then
  echo "AUTO_CLEAN was used. Restoring dumps via mongos (so mongos routes correctly)..."
  # Find all dumps
  for d in "$DUMP_DIR"/*; do
    if [[ -d "$d/$DB_TO_CHECK" ]]; then
      echo "Restoring dump from $d for database $DB_TO_CHECK via mongos..."
      mongorestore --host "$MONGOS_HOST" --db "$DB_TO_CHECK" --drop "$d/$DB_TO_CHECK" \
        || { echo "mongorestore failed for $d"; exit 6; }
      echo "Restore complete for $d"
    fi
  done
fi

echo "=== init-shard-entrypoint finished successfully ==="
exit 0
