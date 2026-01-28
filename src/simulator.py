import time
import random
import sys
from db import get_mongo_db
from backend import create_post_redis

db = get_mongo_db()

def simulate_traffic():
    print("starting traffic")
    
    # incarcam 5000 de useri activi pentru proof of concept
    print("loading users")
    active_users = list(db.users.find().limit(5000))
    active_user_ids = [u["_id"] for u in active_users]
    
    if not active_user_ids:
        print("error: no users found in db")
        return

    post_count = 0
    
    try:
        while True:
            # random user
            user = random.choice(active_users)
            user_id = user["_id"]
            username = user.get("username", "unknown_user")
            
            # generate content
            content = f"Post #{post_count} generated for {username}"
            
            create_post_redis(user_id, content, username)
            post_count += 1
            
            # log every 10 psots
            if post_count % 10 == 0:
                sys.stdout.write(f"\rtraffic generated: {post_count} posts")
                sys.stdout.flush()
            
            # small pause
            # sa nu omoram cpu ul de tot
            time.sleep(0.05) 
            
    except KeyboardInterrupt:
        print("\ntraffic simulation stopped")

if __name__ == "__main__":
    simulate_traffic()