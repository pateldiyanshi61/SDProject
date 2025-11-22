// init-sharding.js - Optimized for banking system with notifications sharding
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
                if (shards[i]._id === "shard1Repl") {
                    shard1Exists = true;
                    break;
                }
            }
        }

        if (!shard1Exists) {
            sh.addShard("shard1Repl/shard1a:27017,shard1b:27017,shard1c:27017");
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
                if (shards[i]._id === "shard2Repl") {
                    shard2Exists = true;
                    break;
                }
            }
        }

        if (!shard2Exists) {
            sh.addShard("shard2Repl/shard2a:27017,shard2b:27017,shard2c:27017");
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

// Add Shard3
safeExecute("Adding Shard3", function () {
    try {
        var shards = sh.status().shards;
        var shard3Exists = false;

        if (shards) {
            for (var i = 0; i < shards.length; i++) {
                if (shards[i]._id === "shard3Repl") {
                    shard3Exists = true;
                    break;
                }
            }
        }

        if (!shard3Exists) {
            sh.addShard("shard3Repl/shard3a:27017,shard3b:27017,shard3c:27017");
            return "Shard3 added successfully";
        } else {
            return "Shard3 already exists";
        }
    } catch (e) {
        if (e.message.includes("already") || e.codeName === "AlreadyInitialized") {
            return "Shard3 already exists";
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

// Shard the accounts collection (by accountNumber)
safeExecute("Sharding 'accounts' collection", function () {
    try {
        sh.shardCollection("banking.accounts", { accountNumber: "hashed" });
        return "Accounts collection sharded by accountNumber (hashed)";
    } catch (e) {
        if (e.message.includes("already sharded") || e.codeName === "AlreadyInitialized") {
            return "Accounts collection already sharded";
        }
        throw e;
    }
});

// Shard the transactions collection (by txId)
safeExecute("Sharding 'transactions' collection", function () {
    try {
        sh.shardCollection("banking.transactions", { txId: "hashed" });
        return "Transactions collection sharded by txId (hashed)";
    } catch (e) {
        if (e.message.includes("already sharded") || e.codeName === "AlreadyInitialized") {
            return "Transactions collection already sharded";
        }
        throw e;
    }
});

// OPTIONAL: Shard the notifications collection (by userId)
// This distributes user notifications across shards for better scalability
safeExecute("Sharding 'notifications' collection", function () {
    try {
        sh.shardCollection("banking.notifications", { userId: "hashed" });
        return "Notifications collection sharded by userId (hashed)";
    } catch (e) {
        if (e.message.includes("already sharded") || e.codeName === "AlreadyInitialized") {
            return "Notifications collection already sharded";
        }
        throw e;
    }
});

print("=== Creating Database Indexes ===\n");

db = db.getSiblingDB("banking");

// Pre-create collections that don't exist yet
print("Pre-creating collections...");
try {
    db.createCollection("users");
    print("✓ Created users collection");
} catch (e) {
    if (e.codeName === "NamespaceExists") {
        print("  Users collection already exists");
    }
}

try {
    db.createCollection("notifications");
    print("✓ Created notifications collection");
} catch (e) {
    if (e.codeName === "NamespaceExists") {
        print("  Notifications collection already exists");
    }
}

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
createIndexSafely("accounts", { "createdAt": -1 }, {}, "createdAt");

// Transaction indexes
createIndexSafely("transactions", { "fromAccount": 1, "createdAt": -1 }, {}, "fromAccount_createdAt");
createIndexSafely("transactions", { "toAccount": 1, "createdAt": -1 }, {}, "toAccount_createdAt");
createIndexSafely("transactions", { "txId": 1 }, { unique: true }, "txId_unique");
createIndexSafely("transactions", { "status": 1 }, {}, "status");
createIndexSafely("transactions", { "createdAt": -1 }, {}, "createdAt");

// Notification indexes (optimized for sharded queries)
createIndexSafely("notifications", { "userId": 1, "createdAt": -1 }, {}, "userId_createdAt");
createIndexSafely("notifications", { "userId": 1, "delivered": 1 }, {}, "userId_delivered");
createIndexSafely("notifications", { "userId": 1, "type": 1 }, {}, "userId_type");
createIndexSafely("notifications", { "delivered": 1 }, {}, "delivered");

print("\n=== Sharding Configuration Summary ===");
print("┌─────────────────────────────────────────────────────┐");
print("│ CLUSTER TOPOLOGY                                    │");
print("├─────────────────────────────────────────────────────┤");
print("│ Config Servers: 3 replicas                          │");
print("│   - config1, config2, config3                       │");
print("│                                                     │");
print("│ Shards: 3 replica sets (9 nodes total)             │");
print("│   - Shard1: shard1a, shard1b, shard1c              │");
print("│   - Shard2: shard2a, shard2b, shard2c              │");
print("│   - Shard3: shard3a, shard3b, shard3c              │");
print("└─────────────────────────────────────────────────────┘");
print("");
print("┌─────────────────────────────────────────────────────┐");
print("│ SHARDED COLLECTIONS                                 │");
print("├─────────────────────────────────────────────────────┤");
print("│ banking.accounts                                    │");
print("│   Shard Key: { accountNumber: 'hashed' }           │");
print("│   Purpose: Distribute accounts evenly               │");
print("│                                                     │");
print("│ banking.transactions                                │");
print("│   Shard Key: { txId: 'hashed' }                    │");
print("│   Purpose: Distribute transactions evenly           │");
print("│                                                     │");
print("│ banking.notifications                               │");
print("│   Shard Key: { userId: 'hashed' }                  │");
print("│   Purpose: Keep user notifications together         │");
print("└─────────────────────────────────────────────────────┘");
print("");
print("┌─────────────────────────────────────────────────────┐");
print("│ NON-SHARDED COLLECTIONS (Primary Shard)             │");
print("├─────────────────────────────────────────────────────┤");
print("│ banking.users                                       │");
print("│   Reason: Small dataset, frequently joined          │");
print("└─────────────────────────────────────────────────────┘");
print("\n=== Initialization Complete! ===\n");

quit(0);