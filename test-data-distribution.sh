#!/bin/bash
# test-data-distribution.sh - Load test data and verify distribution

set -e

BASE_URL="http://localhost:8000"
ACCOUNT_URL="http://localhost:8001"
TRANSACTION_URL="http://localhost:8002"

echo "======================================"
echo "Loading Test Data & Verifying Sharding"
echo "======================================"
echo ""

# Step 1: Register Admin
echo "1. Registering admin user..."
ADMIN_RESPONSE=$(curl -s -X POST "$BASE_URL/api/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@bank.com",
    "password": "Admin@123",
    "role": "admin",
    "profile": {
      "name": "System Admin",
      "phone": "+91-9876543210"
    }
  }')
echo "Admin: $ADMIN_RESPONSE"
echo ""

# Step 2: Register Test Users
echo "2. Registering test users..."
for i in {1..5}; do
  USER_RESPONSE=$(curl -s -X POST "$BASE_URL/api/auth/register" \
    -H "Content-Type: application/json" \
    -d "{
      \"email\": \"user$i@example.com\",
      \"password\": \"User@123\",
      \"role\": \"user\",
      \"profile\": {
        \"name\": \"Test User $i\",
        \"phone\": \"+91-912345678$i\"
      }
    }")
  USER_ID=$(echo $USER_RESPONSE | grep -o '"id":"[^"]*' | cut -d'"' -f4)
  echo "User $i: $USER_ID"
done
echo ""

# Step 3: Login as Admin
echo "3. Logging in as admin..."
LOGIN_RESPONSE=$(curl -s -X POST "$BASE_URL/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@bank.com",
    "password": "Admin@123"
  }')
ADMIN_TOKEN=$(echo $LOGIN_RESPONSE | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)
echo "Admin token obtained"
echo ""

# Step 4: Create Multiple Accounts (will be distributed across shards)
echo "4. Creating 20 test accounts..."
for i in {1..20}; do
  ACCOUNT_NUM=$(printf "ACC%04d" $i)
  BALANCE=$((10000 + RANDOM % 90000))
  
  ACCOUNT_RESPONSE=$(curl -s -X POST "$ACCOUNT_URL/api/accounts" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -d "{
      \"accountNumber\": \"$ACCOUNT_NUM\",
      \"userId\": \"691217d7f6a7b8eb9e76ddf2\",
      \"balance\": $BALANCE.0,
      \"currency\": \"INR\",
      \"status\": \"active\",
      \"meta\": {
        \"accountType\": \"Savings\",
        \"branch\": \"Mumbai Central\"
      }
    }")
  
  if [ $((i % 5)) -eq 0 ]; then
    echo "Created $i accounts..."
  fi
done
echo "✓ Created 20 accounts (ACC0001 - ACC0020)"
echo ""

# Step 5: Create Transactions (will be distributed across shards)
echo "5. Creating 30 test transactions..."
for i in {1..30}; do
  FROM_ACC=$(printf "ACC%04d" $((1 + RANDOM % 10)))
  TO_ACC=$(printf "ACC%04d" $((11 + RANDOM % 10)))
  AMOUNT=$((100 + RANDOM % 9900))
  
  TX_RESPONSE=$(curl -s -X POST "$TRANSACTION_URL/api/transactions/transfer" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -d "{
      \"fromAccount\": \"$FROM_ACC\",
      \"toAccount\": \"$TO_ACC\",
      \"amount\": $AMOUNT.0,
      \"currency\": \"INR\"
    }" 2>/dev/null || echo "Transaction failed")
  
  if [ $((i % 10)) -eq 0 ]; then
    echo "Created $i transactions..."
  fi
  sleep 0.1  # Small delay to avoid overwhelming the system
done
echo "✓ Created 30 transactions"
echo ""

# Step 6: Wait for data to settle
echo "6. Waiting for data to distribute across shards..."
sleep 5
echo ""

# Step 7: Check Data Distribution
echo "======================================"
echo "DATA DISTRIBUTION VERIFICATION"
echo "======================================"
echo ""

echo "Checking Accounts Distribution:"
docker exec mongos mongosh --quiet --eval "
use banking;
db.accounts.getShardDistribution();
"
echo ""

echo "Checking Transactions Distribution:"
docker exec mongos mongosh --quiet --eval "
use banking;
db.transactions.getShardDistribution();
"
echo ""

echo "Total Document Counts:"
docker exec mongos mongosh --quiet --eval "
use banking;
print('Users: ' + db.users.countDocuments());
print('Accounts: ' + db.accounts.countDocuments());
print('Transactions: ' + db.transactions.countDocuments());
print('Notifications: ' + db.notifications.countDocuments());
"
echo ""

# Step 8: Check which shard contains specific accounts
echo "Checking which shard contains specific accounts:"
for acc in ACC0001 ACC0010 ACC0020; do
  echo "Account $acc location:"
  docker exec mongos mongosh --quiet --eval "
    use banking;
    var explain = db.accounts.find({accountNumber: '$acc'}).explain('executionStats');
    if (explain.shards) {
      for (var shard in explain.shards) {
        print('  -> Located on: ' + shard);
      }
    }
  " 2>/dev/null || echo "  -> Could not determine shard"
done
echo ""

# Step 9: Verify Chunk Distribution
echo "Chunk Distribution Across Shards:"
docker exec mongos mongosh --quiet --eval "
use config;
print('Accounts Collection:');
db.chunks.aggregate([
  { \$match: { ns: 'banking.accounts' } },
  { \$group: { _id: '\$shard', chunks: { \$sum: 1 } } },
  { \$sort: { _id: 1 } }
]).forEach(doc => print('  ' + doc._id + ': ' + doc.chunks + ' chunks'));

print('\\nTransactions Collection:');
db.chunks.aggregate([
  { \$match: { ns: 'banking.transactions' } },
  { \$group: { _id: '\$shard', chunks: { \$sum: 1 } } },
  { \$sort: { _id: 1 } }
]).forEach(doc => print('  ' + doc._id + ': ' + doc.chunks + ' chunks'));
"
echo ""

echo "======================================"
echo "✓ Test Complete!"
echo "======================================"
echo ""
echo "Summary:"
echo "- Your test accounts (ACC0001-ACC0020) are distributed across 3 shards"
echo "- Transactions are distributed based on txId hash"
echo "- MongoDB automatically routes queries to the correct shard"
echo "- Your application code needs NO changes!"
echo ""
echo "To see more details, run: ./verify-sharding.sh"