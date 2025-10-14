from motor.motor_asyncio import AsyncIOMotorClient
import os

MONGO_URI = os.getenv("MONGO_URI", "mongodb://mongos:27017/banking")
client = AsyncIOMotorClient(MONGO_URI)
db = client.get_database("banking")
users = db.users
