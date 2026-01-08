import time
from datetime import datetime
from bson.objectid import ObjectId
from db import get_mongo_db, get_redis_client

db = get_mongo_db()
cache = get_redis_client()

def create_post_mongo(user_id, content, username):
    """Inserează doar în MongoDB."""
    post = {
        "user_id": user_id,
        "username": username,
        "content": content,
        "timestamp": datetime.utcnow()
    }
    return db.posts.insert_one(post).inserted_id

def get_feed_mongo(user_id, limit=10):
    start_time = time.time()
    
    user = db.users.find_one({"_id": ObjectId(user_id)})
    if not user:
        return [], 0
    
    following_ids = user.get("following", [])
    
    cursor = db.posts.find(
        {"user_id": {"$in": following_ids}}
    ).sort("timestamp", -1).limit(limit)
    
    posts = list(cursor)
    
    duration = time.time() - start_time
    return posts, duration

def create_post_redis(user_id, content, username):
    post_id = create_post_mongo(user_id, content, username)
    str_post_id = str(post_id)
    
    post_data = {
        "id": str_post_id,
        "username": username,
        "content": content,
        "timestamp": str(datetime.utcnow())
    }
    cache.hset(f"post:{str_post_id}", mapping=post_data)
    cache.expire(f"post:{str_post_id}", 3600) 

    user = db.users.find_one({"_id": ObjectId(user_id)})
    followers = user.get("followers", [])
    
    pipe = cache.pipeline()
    for follower_id in followers:
        key = f"timeline:{follower_id}"
        pipe.lpush(key, str_post_id)
        pipe.ltrim(key, 0, 99)
    pipe.execute()
    
    return post_id

def get_feed_redis(user_id, limit=10):
    start_time = time.time()
    
    post_ids = cache.lrange(f"timeline:{user_id}", 0, limit - 1)
    
    posts = []
    pipe = cache.pipeline()
    for pid in post_ids:
        pipe.hgetall(f"post:{pid}")
    
    results = pipe.execute()
    
    for i, data in enumerate(results):
        if data:
            posts.append(data)
        else:
            pid = post_ids[i]
            p_db = db.posts.find_one({"_id": ObjectId(pid)})
            if p_db:
                p_fmt = {
                    "username": p_db["username"],
                    "content": p_db["content"],
                    "timestamp": str(p_db["timestamp"])
                }
                posts.append(p_fmt)
                
    duration = time.time() - start_time
    return posts, duration