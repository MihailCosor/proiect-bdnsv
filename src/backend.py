import time
from datetime import datetime
from bson.objectid import ObjectId
from db import get_mongo_db, get_redis_client

# init mongo si redis
db = get_mongo_db()
cache = get_redis_client()

metrics = {
    "hits": 0,
    "misses": 0
}

def get_metrics():
    total = metrics["hits"] + metrics["misses"]
    ratio = (metrics["hits"] / total * 100) if total > 0 else 0
    return ratio, total, metrics["hits"], metrics["misses"]

def get_leaderboard(top_n=5):
    # zrevrange va returna userii cu cele mai mari scoruri
    return cache.zrevrange("leaderboard:active_users", 0, top_n - 1, withscores=True)


def create_post_mongo(user_id, content, username):
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
    # salvam in mongo
    post_id = create_post_mongo(user_id, content, username)
    str_post_id = str(post_id)
    
    # cream obiectul post pentru redis
    post_data = {
        "id": str_post_id,
        "username": username,
        "content": content,
        "timestamp": str(datetime.utcnow())
    }
    # hset pentru a salva post ca hash in redis
    cache.hset(f"post:{str_post_id}", mapping=post_data)
    # setam ttl pentru 1h
    cache.expire(f"post:{str_post_id}", 3600) 

    # fan out: catre followeri 
    user = db.users.find_one({"_id": ObjectId(user_id)})
    followers = user.get("followers", [])
    
    pipe = cache.pipeline()
    
    # adaugam post in timeline-ul fiecarui follower
    for follower_id in followers:
        key = f"timeline:{follower_id}"
        pipe.lpush(key, str_post_id)
        # tinem doar last 100 posts
        pipe.ltrim(key, 0, 99)
    
    # update leaderboard
    pipe.zincrby("leaderboard:active_users", 1, username)
    
    pipe.execute()
    return post_id

def delete_post(post_id, user_id):
    str_post_id = str(post_id)
    
    db.posts.delete_one({"_id": ObjectId(post_id)})
    
    # invalidam cache-ul
    cache.delete(f"post:{str_post_id}")
    
    # curatam referintele din timeline al followers
    # operatie grea dar necesara
    user = db.users.find_one({"_id": ObjectId(user_id)})
    if user:
        followers = user.get("followers", [])
        pipe = cache.pipeline()
        for follower_id in followers:
            # lrem pentru a sterge toate aparitiile postului
            pipe.lrem(f"timeline:{follower_id}", 0, str_post_id)
        pipe.execute()
        
    print(f"Post {post_id} deleted and cache invalidated")

def get_feed_redis(user_id, limit=10):
    start_time = time.time()
    
    post_ids = cache.lrange(f"timeline:{user_id}", 0, limit - 1)
    
    posts = []
    # luam datele din cache folosind pipeline pentru eficienta
    pipe = cache.pipeline()
    for pid in post_ids:
        pipe.hgetall(f"post:{pid}")
    
    results = pipe.execute()
    
    # procesam si tinem cont de hits/misses
    for i, data in enumerate(results):
        if data:
            posts.append(data)
            metrics["hits"] += 1
        else:
            # date expirate sau sterse
            metrics["misses"] += 1
            
    duration = time.time() - start_time
    return posts, duration