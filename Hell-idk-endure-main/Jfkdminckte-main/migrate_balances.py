#!/usr/bin/env python3
"""
Migration script: Convert old balance system to separated balances
- Moves existing 'balance' to 'deposit_balance'
- Initializes 'promo_balance' to 0
- Adds 'promo_withdrawal_limit' = 300
"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os

async def migrate():
    mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
    client = AsyncIOMotorClient(mongo_url)
    db = client[os.environ.get('DB_NAME', 'easymoney')]
    
    print("🔄 Starting balance migration...")
    
    # Find users without deposit_balance field
    users_to_migrate = []
    async for user in db.users.find({"deposit_balance": {"$exists": False}}):
        users_to_migrate.append(user)
    
    print(f"📊 Found {len(users_to_migrate)} users to migrate")
    
    migrated = 0
    for user in users_to_migrate:
        old_balance = user.get("balance", 0)
        
        # Move balance to deposit_balance
        await db.users.update_one(
            {"id": user["id"]},
            {"$set": {
                "deposit_balance": old_balance,
                "promo_balance": 0,
                "promo_withdrawal_limit": 300
            }}
        )
        migrated += 1
        
        if migrated % 100 == 0:
            print(f"  ... migrated {migrated} users")
    
    print(f"✅ Migration complete! Migrated {migrated} users")
    
    # Verify
    total_users = await db.users.count_documents({})
    users_with_new_fields = await db.users.count_documents({"deposit_balance": {"$exists": True}})
    
    print(f"\n📊 Verification:")
    print(f"  Total users: {total_users}")
    print(f"  Users with new balance system: {users_with_new_fields}")
    
    client.close()

if __name__ == "__main__":
    asyncio.run(migrate())
