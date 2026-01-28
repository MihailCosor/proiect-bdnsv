import random
from db import get_mongo_db
from backend import create_post_mongo, create_post_redis, get_feed_mongo, get_feed_redis

db = get_mongo_db()

NUM_POSTS = 2000
MIN_FOLLOWING = 100
LIMIT_FEED = 100

def run_test():
    print("=" * 60)
    print("BENCHMARK: MongoDB vs Redis")
    print("=" * 60)
    
    # alegem un user care urmareste pe minim MIN_FOLLOWING
    reader = db.users.find_one(
        {"$expr": {"$gte": [{"$size": "$following"}, MIN_FOLLOWING]}}
    )
    
    if not reader:
        print(f"error: no users found, seed db first")
        return
    
    reader_id = reader["_id"]
    following = reader["following"]
    print(f"selected {reader['username']} with {len(following)} following")

    print(f"\ngenerating {NUM_POSTS} MongoDB posts with pull model...")
    mongo_authors = random.choices(following, k=NUM_POSTS)
    
    for idx, author_id in enumerate(mongo_authors, 1):
        if idx % 500 == 0:
            print(f"->{idx}/{NUM_POSTS} posts created")
        
        author = db.users.find_one({"_id": author_id}, {"username": 1})
        create_post_mongo(author_id, f"Mongo post #{idx}", author['username'])
    
    print(f"{NUM_POSTS} MongoDB posts created succ")

    # masuram timpul pentru feed
    feed_mongo, time_mongo = get_feed_mongo(reader_id, limit=LIMIT_FEED)
    print(f"MongoDB: {time_mongo:.4f}s | Posts retrieved: {len(feed_mongo)}")

    print(f"\ngenerating {NUM_POSTS} Redis posts with push model...")
    redis_authors = random.choices(following, k=NUM_POSTS)
    
    for idx, author_id in enumerate(redis_authors, 1):
        if idx % 500 == 0:
            print(f"->{idx}/{NUM_POSTS} posts created with push model")
        
        author = db.users.find_one({"_id": author_id}, {"username": 1})
        create_post_redis(author_id, f"Redis post #{idx}", author['username'])
    
    print(f"{NUM_POSTS} Redis posts created succ")

    feed_redis, time_redis = get_feed_redis(reader_id, limit=LIMIT_FEED)
    print(f"Redis: {time_redis:.4f}s | Posts retrieved: {len(feed_redis)}")

    print("\n" + "=" * 60)
    print("BENCHMARK RESULTS")
    print("=" * 60)
    print(f"Posts generated:   {NUM_POSTS}")
    print(f"MongoDB (Pull):    {time_mongo:.4f}s")
    print(f"Redis (Push):      {time_redis:.4f}s")
    
    if time_redis == 0:
        print("\nredis either returned instant or error occurred")
        return

    speedup = time_mongo / time_redis
    print(f"\nSpeedup: {speedup:.2f}x faster")
    print(f"Time saved: {(time_mongo - time_redis):.4f}s")
    
    if len(feed_redis) == 0:
        print("\nerror: redis feed is empty")
    
    print("=" * 60)

if __name__ == "__main__":
    run_test()