from pymongo import MongoClient
from pymongo.errors import PyMongoError
from typing import Optional, List, Dict, Union
import time
from bot import Vars, Bot

class Database:
    def __init__(self):
        self.client = MongoClient(Vars.DB_URL)
        self.db = self.client[Vars.DB_NAME]
        self.subs = self.db["subs"]
        self.users = self.db["users"]
        self.premium = self.db['premium']
        
        # Initialize collections if they don't exist
        self._initialize_collections()
    
    def _initialize_collections(self):
        """Ensure required documents exist in collections"""
        try:
            if not self.subs.find_one({"_id": "data"}):
                self.subs.insert_one({"_id": "data"})
            
            if not self.users.find_one({"_id": Vars.DB_NAME}):
                self.users.insert_one({"_id": Vars.DB_NAME})
        except PyMongoError as e:
            print(f"Error initializing collections: {e}")

    async def add_premium(self, user_id: int, time_limit_days: int) -> bool:
        """Add premium status to a user with expiration"""
        try:
            expiration_timestamp = int(time.time()) + time_limit_days * 24 * 60 * 60
            premium_data = {
                "user_id": user_id,
                "expiration_timestamp": expiration_timestamp,
                "added_at": int(time.time())
            }
            
            # Update if exists, insert if not
            result = self.premium.update_one(
                {"user_id": user_id},
                {"$set": premium_data},
                upsert=True
            )
            return result.acknowledged
        except PyMongoError as e:
            print(f"Error adding premium: {e}")
            return False

    async def remove_premium(self, user_id: int) -> bool:
        """Remove premium status from a user"""
        try:
            result = self.premium.delete_one({"user_id": user_id})
            return result.deleted_count > 0
        except PyMongoError as e:
            print(f"Error removing premium: {e}")
            return False

    async def remove_expired_users(self) -> int:
        """Remove expired premium users and return count removed"""
        try:
            current_timestamp = int(time.time())
            result = self.premium.delete_many(
                {"expiration_timestamp": {"$lte": current_timestamp}}
            )
            return result.deleted_count
        except PyMongoError as e:
            print(f"Error removing expired users: {e}")
            return 0

    async def is_premium(self, user_id: int) -> bool:
        """Check if user has active premium"""
        try:
            current_timestamp = int(time.time())
            user = self.premium.find_one({
                "user_id": user_id,
                "expiration_timestamp": {"$gt": current_timestamp}
            })
            return user is not None
        except PyMongoError as e:
            print(f"Error checking premium status: {e}")
            return False

    def get_users(self) -> List[int]:
        """Get all user IDs from database"""
        try:
            users_id = []
            for doc in self.users.find():
                for key in doc:
                    if key != "_id":  # Skip the _id field
                        try:
                            users_id.append(int(key))
                        except (ValueError, TypeError):
                            continue
            return users_id
        except PyMongoError as e:
            print(f"Error getting users: {e}")
            return []

    def add_sub(self, user_id: Union[int, str], manga_url: str, chapter: Optional[str] = None) -> bool:
        """Add a subscription for a user"""
        try:
            user_id = str(user_id)
            
            # Update subs collection
            subs_update = {
                "$addToSet": {f"{manga_url}.users": user_id}
            }
            self.subs.update_one({"_id": "data"}, subs_update, upsert=True)
            
            # Update users collection
            users_update = {
                "$addToSet": {f"{user_id}.subs": manga_url}
            }
            self.users.update_one({"_id": Vars.DB_NAME}, users_update, upsert=True)
            
            return True
        except PyMongoError as e:
            print(f"Error adding subscription: {e}")
            return False

    def get_subs(self, user_id: Union[int, str], manga_url: Optional[str] = None) -> Union[bool, List[str], None]:
        """Get subscriptions for a user or check specific subscription"""
        try:
            user_id = str(user_id)
            user_data = self.users.find_one({"_id": Vars.DB_NAME})
            
            if not user_data or user_id not in user_data:
                return None if manga_url else []
            
            user_subs = user_data.get(user_id, {}).get("subs", [])
            
            if manga_url:
                return manga_url in user_subs
            return user_subs
        except PyMongoError as e:
            print(f"Error getting subscriptions: {e}")
            return None if manga_url else []

    def delete_sub(self, user_id: Union[int, str], manga_url: str) -> bool:
        """Delete a subscription for a user"""
        try:
            user_id = str(user_id)
            
            # Remove from subs collection
            self.subs.update_one(
                {"_id": "data"},
                {"$pull": {f"{manga_url}.users": user_id}}
            )
            
            # Remove from users collection
            self.users.update_one(
                {"_id": Vars.DB_NAME},
                {"$pull": {f"{user_id}.subs": manga_url}}
            )
            
            return True
        except PyMongoError as e:
            print(f"Error deleting subscription: {e}")
            return False

# Initialize database instance
db = Database()
