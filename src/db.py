import redis
from pymongo import MongoClient

MONGO_URI = "mongodb://admin:secretpassword@localhost:27017/"
REDIS_HOST = "localhost"
REDIS_PORT = 6379

def get_mongo_db():
    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=2000)
        client.server_info()
        return client["social_network"]
    except Exception as e:
        print(f"err: {e}")
        return None

def get_redis_client():
    try:
        r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
        r.ping()
        return r
    except Exception as e:
        print(f"err: {e}")
        return None

if __name__ == "__main__":
    db = get_mongo_db()
    cache = get_redis_client()
    
    if db is not None:
        print("mongo connected!")
    if cache:
        print("redis connected!")