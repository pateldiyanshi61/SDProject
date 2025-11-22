#!/bin/bash
# verify-sharding.sh - Verify data is distributed across shards

echo "======================================"
echo "MongoDB Sharding Verification Script"
echo "======================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to run mongosh commands
run_mongosh() {
    docker exec -it mongos mongosh --quiet --eval "$1"
}

echo -e "${BLUE}1. Checking Cluster Status${NC}"
echo "========================================"
run_mongosh "sh.status()" | head -50
echo ""

echo -e "${BLUE}2. Listing All Shards${NC}"
echo "========================================"
run_mongosh "db.adminCommand({ listShards: 1 })"
echo ""

echo -e "${BLUE}3. Checking Database Sharding${NC}"
echo "========================================"
run_mongosh "use banking; db.stats()"
echo ""

echo -e "${BLUE}4. Sharded Collections${NC}"
echo "========================================"
run_mongosh "use config; db.collections.find({}, {_id: 1, key: 1, unique: 1}).pretty()"
echo ""

echo -e "${BLUE}5. Accounts Collection Distribution${NC}"
echo "========================================"
run_mongosh "use banking; db.accounts.getShardDistribution()"
echo ""

echo -e "${BLUE}6. Transactions Collection Distribution${NC}"
echo "========================================"
run_mongosh "use banking; db.transactions.getShardDistribution()"
echo ""

echo -e "${BLUE}7. Notifications Collection Distribution${NC}"
echo "========================================"
run_mongosh "use banking; db.notifications.getShardDistribution()"
echo ""

echo -e "${BLUE}8. Document Counts Per Collection${NC}"
echo "========================================"
run_mongosh "
use banking;
print('Users: ' + db.users.countDocuments());
print('Accounts: ' + db.accounts.countDocuments());
print('Transactions: ' + db.transactions.countDocuments());
print('Notifications: ' + db.notifications.countDocuments());
"
echo ""

echo -e "${BLUE}9. Checking Chunk Distribution${NC}"
echo "========================================"
run_mongosh "
use config;
print('Accounts chunks:');
db.chunks.aggregate([
  { \$match: { ns: 'banking.accounts' } },
  { \$group: { _id: '\$shard', count: { \$sum: 1 } } },
  { \$sort: { _id: 1 } }
]).forEach(printjson);

print('\\nTransactions chunks:');
db.chunks.aggregate([
  { \$match: { ns: 'banking.transactions' } },
  { \$group: { _id: '\$shard', count: { \$sum: 1 } } },
  { \$sort: { _id: 1 } }
]).forEach(printjson);
"
echo ""

echo -e "${BLUE}10. Replica Set Health${NC}"
echo "========================================"
echo -e "${YELLOW}Config Server:${NC}"
docker exec config1 mongosh --quiet --eval "rs.status().members.forEach(m => print(m.name + ' - ' + m.stateStr))"
echo ""
echo -e "${YELLOW}Shard 1:${NC}"
docker exec shard1a mongosh --quiet --eval "rs.status().members.forEach(m => print(m.name + ' - ' + m.stateStr))"
echo ""
echo -e "${YELLOW}Shard 2:${NC}"
docker exec shard2a mongosh --quiet --eval "rs.status().members.forEach(m => print(m.name + ' - ' + m.stateStr))"
echo ""
echo -e "${YELLOW}Shard 3:${NC}"
docker exec shard3a mongosh --quiet --eval "rs.status().members.forEach(m => print(m.name + ' - ' + m.stateStr))"
echo ""

echo -e "${GREEN}✓ Verification Complete!${NC}"
echo ""
echo "To check which shard contains a specific document:"
echo "docker exec mongos mongosh --eval 'use banking; db.accounts.find({accountNumber: \"ACC1001\"}).explain(\"executionStats\")'"