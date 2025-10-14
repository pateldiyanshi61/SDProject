// init-sharding.js
print("Initializing MongoDB sharding...");

sh.addShard("shard1ReplSet/shard1:27018");
sh.addShard("shard2ReplSet/shard2:27018");

sh.enableSharding("banking");
sh.shardCollection("banking.accounts", { accountNumber: "hashed" });

print("✅ Sharding initialized successfully");
