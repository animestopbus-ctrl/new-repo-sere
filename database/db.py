import motor.motor_asyncio
import datetime
import logging
import secret

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, uri, database_name):
        self._client = motor.motor_asyncio.AsyncIOMotorClient(uri)
        self.db = self._client[database_name]
        self.col = self.db.users
        logger.info("✅ MongoDB Connected Successfully!")

    def new_user(self, id, name, username):
        return {
            'id': int(id),
            'name': name,
            'username': username,
            'join_date': datetime.datetime.now().isoformat(),
            'files_processed': 0,
            'is_premium': False,
            'is_banned': False
        }

    async def add_user(self, id, name, username):
        user = await self.col.find_one({'id': int(id)})
        if not user:
            await self.col.insert_one(self.new_user(id, name, username))
            logger.info(f"🆕 New user added to DB: {id} - {name}")
            return True
        return False

    async def total_users_count(self):
        return await self.col.count_documents({})

    async def increment_files(self, id):
        await self.col.update_one({'id': int(id)}, {'$inc': {'files_processed': 1}})

    async def get_db_stats(self):
        """Fetches the actual storage size of the MongoDB Database"""
        try:
            stats = await self.db.command("dbstats")
            storage_size = stats.get("storageSize", 0) / (1024 * 1024) # Convert bytes to MB
            return f"{storage_size:.2f} MB"
        except Exception as e:
            logger.error(f"Error fetching DB stats: {e}")
            return "Unknown"

# 🚀 EXPORT THE DB INSTANCE FOR THE WHOLE BOT TO USE
db = Database(secret.MONGO_URI, "TitaniumDB")