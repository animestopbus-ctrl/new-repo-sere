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
            'premium_expiry': None,
            'daily_usage': 0,
            'limit_reset_time': None,
            'is_banned': False
        }

    async def add_user(self, id, name, username):
        user = await self.col.find_one({'id': int(id)})
        if not user:
            await self.col.insert_one(self.new_user(id, name, username))
            logger.info(f"🆕 New user added to DB: {id} - {name}")
            return True
        return False

    async def get_all_users(self):
        """Yields all users for Broadcasting"""
        return self.col.find({})

    # ================= LIMITS & PREMIUM =================
    async def check_premium_status(self, id):
        user = await self.col.find_one({'id': int(id)})
        if not user or not user.get('is_premium'): return False
        
        expiry = user.get('premium_expiry')
        if expiry and datetime.datetime.now() > expiry:
            await self.col.update_one({'id': int(id)}, {'$set': {'is_premium': False, 'premium_expiry': None}})
            return False
        return True

    async def check_limit(self, id):
        user = await self.col.find_one({'id': int(id)})
        if not user: return False
        if await self.check_premium_status(id): return False 
            
        now = datetime.datetime.now()
        reset_time = user.get('limit_reset_time')

        if reset_time is None or now >= reset_time:
            await self.col.update_one({'id': int(id)}, {'$set': {'daily_usage': 0, 'limit_reset_time': None}})
            return False 

        if user.get('daily_usage', 0) >= 10: return True 
        return False

    async def add_traffic(self, id):
        user = await self.col.find_one({'id': int(id)})
        if not user or user.get('is_premium'): return

        now = datetime.datetime.now()
        reset_time = user.get('limit_reset_time')

        if reset_time is None or now >= reset_time:
            new_reset = now + datetime.timedelta(hours=24)
            await self.col.update_one({'id': int(id)}, {'$set': {'daily_usage': 1, 'limit_reset_time': new_reset}, '$inc': {'files_processed': 1}})
        else:
            await self.col.update_one({'id': int(id)}, {'$inc': {'daily_usage': 1, 'files_processed': 1}})

    # ================= CUSTOM CAPTIONS =================
    async def set_caption(self, id, caption):
        await self.col.update_one({'id': int(id)}, {'$set': {'caption': caption}})

    async def get_caption(self, id):
        user = await self.col.find_one({'id': int(id)})
        return user.get('caption', None) if user else None

    async def del_caption(self, id):
        await self.col.update_one({'id': int(id)}, {'$unset': {'caption': ""}})

    # ================= ADMIN TOOLS =================
    async def grant_premium(self, id, days):
        expiry = datetime.datetime.now() + datetime.timedelta(days=days)
        await self.col.update_one({'id': int(id)}, {'$set': {'is_premium': True, 'premium_expiry': expiry, 'daily_usage': 0, 'limit_reset_time': None}})

    async def revoke_premium(self, id):
        await self.col.update_one({'id': int(id)}, {'$set': {'is_premium': False, 'premium_expiry': None}})

    async def ban_user(self, id):
        await self.col.update_one({'id': int(id)}, {'$set': {'is_banned': True}})

    async def unban_user(self, id):
        await self.col.update_one({'id': int(id)}, {'$set': {'is_banned': False}})

    async def is_banned(self, id):
        user = await self.col.find_one({'id': int(id)})
        return user.get('is_banned', False) if user else False

    async def get_users_page(self, skip=0, limit=10):
        cursor = self.col.find({}).skip(skip).limit(limit)
        return await cursor.to_list(length=limit)

    async def total_users_count(self):
        return await self.col.count_documents({})

    async def get_db_stats(self):
        try:
            stats = await self.db.command("dbstats")
            return f"{(stats.get('storageSize', 0) / (1024 * 1024)):.2f} MB"
        except Exception: return "Unknown"

db = Database(secret.MONGO_URI, "TitaniumDB")
