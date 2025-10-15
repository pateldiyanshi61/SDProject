#!/bin/bash

echo "======================================"
echo "Banking System - Clean Restart Script"
echo "======================================"
echo ""

# Stop all containers
echo "Step 1: Stopping all containers..."
docker-compose down

# Remove volumes to start fresh
echo "Step 2: Removing all volumes..."
docker-compose down -v

# Remove orphan containers
echo "Step 3: Cleaning orphan containers..."
docker-compose down --remove-orphans

# Prune docker system
echo "Step 4: Pruning Docker system..."
docker system prune -f

# Build services
echo "Step 5: Building services..."
docker-compose build --no-cache

echo ""
echo "======================================"
echo "Starting services..."
echo "======================================"
echo ""

# Start MongoDB infrastructure first
echo "Starting MongoDB infrastructure..."
docker-compose up -d configsvr shard1 shard2

echo "Waiting 30 seconds for MongoDB instances to start..."
sleep 30

# Initialize replica sets
echo "Initializing replica sets..."
docker-compose up init-replica-sets

echo "Waiting 20 seconds for replica sets to stabilize..."
sleep 20

# Start mongos
echo "Starting mongos router..."
docker-compose up -d mongos

echo "Waiting 20 seconds for mongos..."
sleep 20

# Initialize sharding
echo "Initializing sharding..."
docker-compose up init-sharding

echo "Waiting 10 seconds..."
sleep 10

# Start RabbitMQ
echo "Starting RabbitMQ..."
docker-compose up -d rabbitmq

echo "Waiting 15 seconds for RabbitMQ..."
sleep 15

# Start all microservices
echo "Starting microservices..."
docker-compose up -d auth-service account-service transaction-service notification-service

echo ""
echo "======================================"
echo "Deployment Status"
echo "======================================"
echo ""

# Wait for services to be ready
sleep 10

# Show status
docker-compose ps

echo ""
echo "======================================"
echo "Checking Service Health"
echo "======================================"
echo ""

# Check each service
echo "Checking Auth Service..."
curl -f http://localhost:8000/ 2>/dev/null && echo "✓ Auth Service OK" || echo "✗ Auth Service NOT responding"

echo "Checking Account Service..."
curl -f http://localhost:8001/ 2>/dev/null && echo "✓ Account Service OK" || echo "✗ Account Service NOT responding"

echo "Checking Transaction Service..."
curl -f http://localhost:8002/ 2>/dev/null && echo "✓ Transaction Service OK" || echo "✗ Transaction Service NOT responding"

echo "Checking Notification Service..."
curl -f http://localhost:8003/ 2>/dev/null && echo "✓ Notification Service OK" || echo "✗ Notification Service NOT responding"

echo ""
echo "======================================"
echo "MongoDB Sharding Status"
echo "======================================"
echo ""

docker exec mongos mongosh --quiet --eval "sh.status()" 2>/dev/null || echo "Mongos not ready yet"

echo ""
echo "======================================"
echo "Deployment Complete!"
echo "======================================"
echo ""
echo "Services:"
echo "  - Auth Service:         http://localhost:8000"
echo "  - Account Service:      http://localhost:8001"
echo "  - Transaction Service:  http://localhost:8002"
echo "  - Notification Service: http://localhost:8003"
echo "  - RabbitMQ Management:  http://localhost:15672 (guest/guest)"
echo "  - MongoDB:              mongodb://localhost:27017"
echo ""
echo "To view logs:"
echo "  docker-compose logs -f [service-name]"
echo ""
echo "To stop all services:"
echo "  docker-compose down"
echo ""