import os
from motor.motor_asyncio import AsyncIOMotorClient

MONGO_URI = os.getenv("MONGO_URI","mongodb://mongo-db:27017")
client = AsyncIOMotorClient(MONGO_URI)
db = client.get_database("banking")
accounts = db.accounts
transactions = db.transactions
