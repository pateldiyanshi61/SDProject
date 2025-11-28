#!/bin/bash

echo "=========================================="
echo "  Banking Microservices Deployment"
echo "  Redis + Rate Limiting + Nginx"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Step 1: Copy cache.py to all services
echo -e "${YELLOW}[1/6] Copying cache.py to all services...${NC}"
for service in auth-service account-service transaction-service notification-service; do
    if [ -f "cache.py" ]; then
        cp cache.py $service/app/cache.py
        echo -e "${GREEN}✓${NC} Copied to $service/app/"
    else
        echo -e "${RED}✗${NC} cache.py not found! Please create it first."
        exit 1
    fi
done

# Step 2: Backup existing docker-compose.yml
echo ""
echo -e "${YELLOW}[2/6] Backing up existing docker-compose.yml...${NC}"
if [ -f "docker-compose.yml" ]; then
    cp docker-compose.yml docker-compose.yml.backup
    echo -e "${GREEN}✓${NC} Backup created: docker-compose.yml.backup"
else
    echo -e "${RED}✗${NC} docker-compose.yml not found!"
    exit 1
fi

# Step 3: Check if nginx.conf exists
echo ""
echo -e "${YELLOW}[3/6] Checking nginx.conf...${NC}"
if [ -f "nginx.conf" ]; then
    echo -e "${GREEN}✓${NC} nginx.conf found"
else
    echo -e "${RED}✗${NC} nginx.conf not found! Please create it first."
    exit 1
fi

# Step 4: Stop existing containers
echo ""
echo -e "${YELLOW}[4/6] Stopping existing containers...${NC}"
docker-compose down
echo -e "${GREEN}✓${NC} Containers stopped"

# Step 5: Build with new dependencies
echo ""
echo -e "${YELLOW}[5/6] Building services with new dependencies...${NC}"
echo "This may take a few minutes..."
docker-compose build --no-cache

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓${NC} Build successful"
else
    echo -e "${RED}✗${NC} Build failed!"
    exit 1
fi

# Step 6: Start services
echo ""
echo -e "${YELLOW}[6/6] Starting services...${NC}"
docker-compose up -d

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓${NC} Services started"
else
    echo -e "${RED}✗${NC} Failed to start services!"
    exit 1
fi

# Wait for services to be ready
echo ""
echo -e "${YELLOW}Waiting for services to be ready...${NC}"
sleep 10

# Health checks
echo ""
echo "=========================================="
echo "  Health Checks"
echo "=========================================="

# Check Redis
echo -n "Redis: "
if docker exec redis-cache redis-cli ping > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Connected${NC}"
else
    echo -e "${RED}✗ Disconnected${NC}"
fi

# Check Nginx
echo -n "Nginx: "
if curl -s http://localhost/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Running${NC}"
else
    echo -e "${RED}✗ Not responding${NC}"
fi

# Check services
for port in 8000 8001 8002 8003; do
    service_name=""
    case $port in
        8000) service_name="Auth Service" ;;
        8001) service_name="Account Service" ;;
        8002) service_name="Transaction Service" ;;
        8003) service_name="Notification Service" ;;
    esac
    
    echo -n "$service_name: "
    if curl -s http://localhost:$port/ > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Running${NC}"
    else
        echo -e "${RED}✗ Not responding${NC}"
    fi
done

echo ""
echo "=========================================="
echo "  Deployment Summary"
echo "=========================================="
echo ""
echo "Services are accessible at:"
echo "  - Nginx Proxy:        http://localhost"
echo "  - Auth Service:       http://localhost:8000"
echo "  - Account Service:    http://localhost:8001"
echo "  - Transaction Service: http://localhost:8002"
echo "  - Notification Service: http://localhost:8003"
echo "  - RabbitMQ Management: http://localhost:15672"
echo ""
echo "Redis Cache:"
echo "  - Host: redis-cache"
echo "  - Port: 6379"
echo "  - Max Memory: 10MB (LRU)"
echo ""
echo "Rate Limits:"
echo "  - Auth endpoints: 10 requests/minute"
echo "  - API endpoints: 60 requests/minute"
echo ""
echo "To view logs:"
echo "  docker-compose logs -f [service-name]"
echo ""
echo "To check Redis cache:"
echo "  docker exec -it redis-cache redis-cli"
echo ""
echo -e "${GREEN}✓ Deployment complete!${NC}"