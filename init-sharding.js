// init-sharding.js - Fixed version with better error handling
print("=== Starting MongoDB Sharding Initialization ===\n");

// Function to safely execute and handle errors
function safeExecute(description, fn) {
    try {
        print(`${description}...`);
        var result = fn();
        print(`✓ ${description} completed\n`);
        return result;
    } catch (e) {
        print(`✗ ${description} failed: ${e.message}`);
        if (e.codeName && (e.codeName === "AlreadyInitialized" || e.message.includes("already"))) {
            print(`  (Already configured - continuing)\n`);
            return null;
        }
        throw e;
    }
}

// Wait a bit for mongos to be fully ready
sleep(5000);

// Add Shard1
safeExecute("Adding Shard1", function () {
    try {
        var shards = sh.status().shards;
        var shard1Exists = false;

        if (shards) {
            for (var i = 0; i < shards.length; i++) {
                if (shards[i]._id === "shard1ReplSet") {
                    shard1Exists = true;
                    break;
                }
            }
        }

        if (!shard1Exists) {
            sh.addShard("shard1ReplSet/shard1:27018");
            return "Shard1 added successfully";
        } else {
            return "Shard1 already exists";
        }
    } catch (e) {
        if (e.message.includes("already") || e.codeName === "AlreadyInitialized") {
            return "Shard1 already exists";
        }
        throw e;
    }
});

// Add Shard2
safeExecute("Adding Shard2", function () {
    try {
        var shards = sh.status().shards;
        var shard2Exists = false;

        if (shards) {
            for (var i = 0; i < shards.length; i++) {
                if (shards[i]._id === "shard2ReplSet") {
                    shard2Exists = true;
                    break;
                }
            }
        }

        if (!shard2Exists) {
            sh.addShard("shard2ReplSet/shard2:27018");
            return "Shard2 added successfully";
        } else {
            return "Shard2 already exists";
        }
    } catch (e) {
        if (e.message.includes("already") || e.codeName === "AlreadyInitialized") {
            return "Shard2 already exists";
        }
        throw e;
    }
});

// Enable sharding on banking database
safeExecute("Enabling sharding on 'banking' database", function () {
    try {
        sh.enableSharding("banking");
        return "Sharding enabled on banking database";
    } catch (e) {
        if (e.message.includes("already enabled") || e.codeName === "AlreadyInitialized") {
            return "Sharding already enabled on banking database";
        }
        throw e;
    }
});

// Shard the accounts collection
safeExecute("Sharding 'accounts' collection", function () {
    try {
        sh.shardCollection("banking.accounts", { accountNumber: "hashed" });
        return "Accounts collection sharded";
    } catch (e) {
        if (e.message.includes("already sharded") || e.codeName === "AlreadyInitialized") {
            return "Accounts collection already sharded";
        }
        throw e;
    }
});

// Shard the transactions collection
safeExecute("Sharding 'transactions' collection", function () {
    try {
        sh.shardCollection("banking.transactions", { txId: "hashed" });
        return "Transactions collection sharded";
    } catch (e) {
        if (e.message.includes("already sharded") || e.codeName === "AlreadyInitialized") {
            return "Transactions collection already sharded";
        }
        throw e;
    }
});

print("=== Creating Database Indexes ===\n");

db = db.getSiblingDB("banking");

// Helper function to create index safely
function createIndexSafely(collection, indexSpec, options, indexName) {
    try {
        var existingIndexes = db[collection].getIndexes();
        var indexExists = false;

        for (var i = 0; i < existingIndexes.length; i++) {
            var idx = existingIndexes[i];
            if (JSON.stringify(idx.key) === JSON.stringify(indexSpec)) {
                indexExists = true;
                break;
            }
        }

        if (!indexExists) {
            db[collection].createIndex(indexSpec, options || {});
            print(`✓ Created index on ${collection}: ${indexName}`);
        } else {
            print(`  Index already exists on ${collection}: ${indexName}`);
        }
    } catch (e) {
        if (e.codeName === "IndexOptionsConflict" || e.message.includes("already exists")) {
            print(`  Index already exists on ${collection}: ${indexName}`);
        } else {
            print(`✗ Failed to create index on ${collection}.${indexName}: ${e.message}`);
        }
    }
}

// User indexes
createIndexSafely("users", { "email": 1 }, { unique: true }, "email_unique");
createIndexSafely("users", { "createdAt": -1 }, {}, "createdAt");

// Account indexes
createIndexSafely("accounts", { "userId": 1 }, {}, "userId");
createIndexSafely("accounts", { "accountNumber": 1 }, { unique: true }, "accountNumber_unique");
createIndexSafely("accounts", { "status": 1 }, {}, "status");

// Transaction indexes
createIndexSafely("transactions", { "fromAccount": 1, "createdAt": -1 }, {}, "fromAccount_createdAt");
createIndexSafely("transactions", { "toAccount": 1, "createdAt": -1 }, {}, "toAccount_createdAt");
createIndexSafely("transactions", { "txId": 1 }, { unique: true }, "txId_unique");
createIndexSafely("transactions", { "status": 1 }, {}, "status");

// Notification indexes
createIndexSafely("notifications", { "userId": 1, "createdAt": -1 }, {}, "userId_createdAt");
createIndexSafely("notifications", { "delivered": 1 }, {}, "delivered");

print("\n=== Sharding Initialization Complete! ===\n");
quit(0);