from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import IndexModel, ASCENDING
from .config import settings
import logging

logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        self.client = None
        self.db = None

database = Database()

async def connect_to_mongo():
    """Create database connection"""
    database.client = AsyncIOMotorClient(settings.mongodb_url)
    if database.client:
        database.db = database.client[settings.database_name]
    
    # Create indexes for better performance
    await create_indexes()
    logger.info("Connected to MongoDB")

async def close_mongo_connection():
    """Close database connection"""
    if database.client:
        database.client.close()
    logger.info("Disconnected from MongoDB")

async def create_indexes():
    """Create database indexes for optimal performance"""
    if database.db is None:
        logger.error("Database not connected")
        return
        
    try:
        # Doctors collection indexes
        doctors_collection = database.db.doctors
        await doctors_collection.create_index("phone", unique=True)
        await doctors_collection.create_index("isBlocked")
        
        # Patients collection indexes
        patients_collection = database.db.patients
        await patients_collection.create_index("phone", unique=True)
        
        # Visits collection indexes
        visits_collection = database.db.visits
        await visits_collection.create_index([("doctorId", ASCENDING), ("date", ASCENDING)])
        await visits_collection.create_index("patientId")
        await visits_collection.create_index("date")
        
        logger.info("Database indexes created successfully")
    except Exception as e:
        logger.error(f"Error creating indexes: {e}")

def get_database():
    return database.db 