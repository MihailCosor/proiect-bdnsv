import random
from faker import Faker
from db import get_mongo_db
from pymongo import UpdateOne

fake = Faker()
db = get_mongo_db()

BULK = 1_00_000
RELATIONS = (50, 300)
PROGRESS_INTERVAL = 10_000

def seed_users(n=BULK):
    if db is None:
        return

    print(f"generating {n} users...")
    
    users_collection = db["users"]
    users_collection.drop() 
    
    users = [
        {
            "username": fake.user_name(),
            "email": fake.email(),
            "name": fake.name(),
            "avatar": fake.image_url(),
            "followers": [],
            "following": []
        }
        for _ in range(n)
    ]
    
    # save as bulk ca sa mergem repede
    result = users_collection.insert_many(users, ordered=False)
    user_ids = result.inserted_ids
    print(f"inserted into mongodb")

    print("generating follow relationships...")
    
    user_ids_list = list(user_ids)
    followers_map = {}
    
    bulk_operations = []
    
    for idx, uid in enumerate(user_ids):
        if (idx + 1) % PROGRESS_INTERVAL == 0:
            print(f"->progress {idx + 1}/{n} users...")
        
        num_targets = random.randint(RELATIONS[0], RELATIONS[1])
        targets = random.sample(user_ids_list, k=num_targets)
        
        # ensure user doesnt follow himself
        if uid in targets:
            targets.remove(uid)
        
        # construim followers map pentru update
        for target in targets:
            if target not in followers_map:
                followers_map[target] = []
            followers_map[target].append(uid)
        
        # prepare update pentru operatia in bulk
        bulk_operations.append(
            UpdateOne(
                {"_id": uid},
                {"$set": {
                    "following": targets,
                    "followers": followers_map.get(uid, [])
                }}
            )
        )
    
    print("executing bulk update...")
    
    BATCH_SIZE = 50_000
    for i in range(0, len(bulk_operations), BATCH_SIZE):
        batch = bulk_operations[i:i + BATCH_SIZE]
        users_collection.bulk_write(batch, ordered=False)
        print(f"->processed batch {i//BATCH_SIZE + 1}/{(len(bulk_operations) + BATCH_SIZE - 1)//BATCH_SIZE}")

    print("database seeding complete")

if __name__ == "__main__":
    seed_users(BULK)