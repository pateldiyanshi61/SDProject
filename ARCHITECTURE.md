# System Architecture and Detailed Explanation

## 1. Overview

The system is a scalable microservices-based banking platform with the following core components:

- **MongoDB Sharded Cluster:** Distributed database system handling high-volume data storage with sharding and replication.
- **API Gateway:** Centralized entry point routing client requests to microservices.
- **Microservices:** Independent services handling specific business domains (Account Service, Auth Service, Transaction Service, Notification Service).
- **NGINX Load Balancer:** Manages request rate limiting and load balancing for incoming API traffic.
- **Redis Cache:** Caches frequently accessed data to improve API response times.
- **Message Queue (e.g., RabbitMQ):** Supports asynchronous communication in notification handling.
- **Frontend:** React-based banking user interface communicating with backend via APIs.

---

## 2. Architecture Diagram

```plaintext
+------------------+ 
|     Frontend     |  
|  (React App)     |  
+--------+---------+  
         | HTTP/HTTPS
         v           
+--------+---------+         +------------+     +-------------+
|      NGINX       |-------->| API Gateway|---->| AuthService |
|  Load Balancer   |         |  (Routing) |     +-------------+
| - Rate Limiting  |         +------------+     +--------------+
+--------+---------+                          | AccountService |
         |                                    +--------------+
         |                                    +-----------------+
         |                                    | TransactionService|
         |                                    +-----------------+
         |                                    +---------------------+
         |                                    | Notification Service |
         |                                    +---------------------+
         |
         |                                +-------------------------+
         +------------------------------->|  MongoDB Sharded Cluster  |
                                        |  - Shard 1 (Replica set)   |
                                        |  - Shard 2 (Replica set)   |
                                        |  - Shard 3 (Replica set)   |
                                        +-------------------------+
                                        +----------------+
                                        | Redis Cache    | <-- Used for caching notifications, rate limits, etc.
                                        +----------------+

```

---

## 3. Detailed Component Explanation

### a. MongoDB Sharded Cluster
- **Sharding**: Database is horizontally partitioned to distribute data across multiple nodes.
- **Shards**: Three shards (Shard1, Shard2, Shard3), each a replica set of three nodes for fault tolerance.
- **Sharded Collections**:
  - `banking.accounts` sharded by `accountNumber` (hashed key).
  - `banking.transactions` sharded by `txId` (hashed key).
  - `banking.notifications` sharded by `userId` (hashed key).
- **Non-sharded collections** like users are hosted on the primary shard for efficient joins.

### b. API Gateway
- Centralized routing for all API requests.
- Provides authentication token validation.
- Acts as security, rate limiting, and orchestration layer to invoke appropriate service.

### c. NGINX Load Balancer
- Fronts all incoming HTTP requests on port 80.
- Implements IP-based rate limiting:
  - API Gateway: 60 requests per minute.
  - Authentication endpoint: 10 requests per minute.
- Proxies requests with headers preserving real IP and protocol.
- Improves availability by distributing request load.

### d. Microservices
- Separate independently deployable services with isolated business logic.
- **Account Service**: Handles user accounts, balances.
- **Auth Service**: Manages authentication, token issuance.
- **Transaction Service**: Processes banking transactions, publishes notifications.
- **Notification Service**: Manages user notifications, consumer for message queues.

### e. Redis Cache
- Caches commonly accessed data like notifications, rate limits.
- Reduces MongoDB query load.
- TTL based cache invalidation ensures data freshness.

### f. Notifications and Messaging
- Notifications stored in MongoDB, sharded by userId.
- Published asynchronously via message queue.
- Notification service consumes queue for reliable processing.
- API endpoints support fetching, marking delivered/read, deletion.

### g. API Rate Limiter
- Two-tiered rate limiting:
  - NGINX controls request bursts at network edge.
  - Microservices enforce finer-grain limits using `slowapi`.

---

## 4. How It Works Together

1. User interacts via React frontend sending HTTPS requests.
2. Requests hit NGINX, which limits rate & routes to API Gateway.
3. API Gateway validates tokens, forwards requests to microservices.
4. Microservices query/modify MongoDB sharded collections.
5. Transaction service publishes notifications to message queue.
6. Notification service consumes queue, stores notifications.
7. Notification caching in Redis accelerates repeated fetches.
8. Client polls or requests notifications APIs for real-time updates.

---

This system design enables scalable, reliable, and performant banking operations with advanced sharding, caching, messaging, and rate limiting mechanisms.

If you would like, I can create a visual diagram image of this architecture or prepare additional detailed design documents.
