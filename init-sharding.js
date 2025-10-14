// init-sharding.js - Idempotent sharding initialization
print("Initializing MongoDB sharding...");

// Check and add shard1
try {
    let shardStatus = sh.status();
    let shard1Exists = false;
    
    if (shardStatus.shards) {
        shardStatus.shards.forEach(shard => {
            if (shard._id === "shard1ReplSet") {
                shard1Exists = true;
            }
        });
    }
    
    if (!shard1Exists) {
        print("Adding shard1...");
        sh.addShard("shard1ReplSet/shard1:27018");
    } else {
        print("Shard1 already exists");
    }
} catch (e) {
    print("Error checking/adding shard1: " + e);
}

// Check and add shard2
try {
    let shardStatus = sh.status();
    let shard2Exists = false;
    
    if (shardStatus.shards) {
        shardStatus.shards.forEach(shard => {
            if (shard._id === "shard2ReplSet") {
                shard2Exists = true;
            }
        });
    }
    
    if (!shard2Exists) {
        print("Adding shard2...");
        sh.addShard("shard2ReplSet/shard2:27018");
    } else {
        print("Shard2 already exists");
    }
} catch (e) {
    print("Error checking/adding shard2: " + e);
}

// Enable sharding on banking database
try {
    print("Enabling sharding on 'banking' database...");
    sh.enableSharding("banking");
} catch (e) {
    if (e.codeName === "AlreadyInitialized" || e.message.includes("already enabled")) {
        print("Sharding already enabled on 'banking' database");
    } else {
        print("Error enabling sharding: " + e);
    }
}

// Shard the accounts collection
try {
    print("Sharding 'accounts' collection...");
    sh.shardCollection("banking.accounts", { accountNumber: "hashed" });
} catch (e) {
    if (e.codeName === "AlreadyInitialized" || e.message.includes("already sharded")) {
        print("'accounts' collection already sharded");
    } else {
        print("Error sharding accounts: " + e);
    }
}

// Shard the transactions collection
try {
    print("Sharding 'transactions' collection...");
    sh.shardCollection("banking.transactions", { txId: "hashed" });
} catch (e) {
    if (e.codeName === "AlreadyInitialized" || e.message.includes("already sharded")) {
        print("'transactions' collection already sharded");
    } else {
        print("Error sharding transactions: " + e);
    }
}

// Create indexes
print("Creating indexes...");
db = db.getSiblingDB("banking");

try {
    db.accounts.createIndex({ "userId": 1 });
    print("Index created: accounts.userId");
} catch (e) {
    if (e.codeName === "IndexOptionsConflict" || e.message.includes("already exists")) {
        print("Index already exists: accounts.userId");
    }
}

try {
    db.accounts.createIndex({ "accountNumber": 1 }, { unique: true });
    print("Index created: accounts.accountNumber (unique)");
} catch (e) {
    if (e.codeName === "IndexOptionsConflict" || e.message.includes("already exists")) {
        print("Index already exists: accounts.accountNumber");
    }
}

try {
    db.accounts.createIndex({ "status": 1 });
    print("Index created: accounts.status");
} catch (e) {
    if (e.codeName === "IndexOptionsConflict" || e.message.includes("already exists")) {
        print("Index already exists: accounts.status");
    }
}

try {
    db.transactions.createIndex({ "fromAccount": 1, "createdAt": -1 });
    print("Index created: transactions.fromAccount + createdAt");
} catch (e) {
    if (e.codeName === "IndexOptionsConflict" || e.message.includes("already exists")) {
        print("Index already exists: transactions.fromAccount + createdAt");
    }
}

try {
    db.transactions.createIndex({ "toAccount": 1, "createdAt": -1 });
    print("Index created: transactions.toAccount + createdAt");
} catch (e) {
    if (e.codeName === "IndexOptionsConflict" || e.message.includes("already exists")) {
        print("Index already exists: transactions.toAccount + createdAt");
    }
}

try {
    db.transactions.createIndex({ "txId": 1 }, { unique: true });
    print("Index created: transactions.txId (unique)");
} catch (e) {
    if (e.codeName === "IndexOptionsConflict" || e.message.includes("already exists")) {
        print("Index already exists: transactions.txId");
    }
}

try {
    db.users.createIndex({ "email": 1 }, { unique: true });
    print("Index created: users.email (unique)");
} catch (e) {
    if (e.codeName === "IndexOptionsConflict" || e.message.includes("already exists")) {
        print("Index already exists: users.email");
    }
}

try {
    db.notifications.createIndex({ "userId": 1, "createdAt": -1 });
    print("Index created: notifications.userId + createdAt");
} catch (e) {
    if (e.codeName === "IndexOptionsConflict" || e.message.includes("already exists")) {
        print("Index already exists: notifications.userId + createdAt");
    }
}

try {
    db.notifications.createIndex({ "delivered": 1 });
    print("Index created: notifications.delivered");
} catch (e) {
    if (e.codeName === "IndexOptionsConflict" || e.message.includes("already exists")) {
        print("Index already exists: notifications.delivered");
    }
}

print("\nSharding initialization complete!");
print("\nCurrent shard status:");
printjson(sh.status());
