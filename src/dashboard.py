import streamlit as st
import time
import pandas as pd
from backend import get_feed_mongo, get_feed_redis, get_metrics, get_leaderboard, db

st.set_page_config(
    page_title="BDNSV Proiect",
    layout="wide"
)

st.markdown("""
<style>
    .metric-card {
        background-color: #0e1117;
        border: 1px solid #303030;
        padding: 20px;
        border-radius: 10px;
        margin-bottom: 10px;
    }
    .stSuccess {
        background-color: rgba(0, 200, 5, 0.1) !important;
    }
</style>
""", unsafe_allow_html=True)

st.title("Social Media Feed - MongoDB vs Redis performance comparison")
st.markdown("O comparatie cu suport vizual intre modelele Pull si Push pentru un feed de social media")

st.sidebar.header("Controls")

if "current_user_id" not in st.session_state:
    # luam un user random care urmareste pe cineva
    sample_user = db.users.find_one({"following": {"$not": {"$size": 0}}})
    if sample_user:
        st.session_state["current_user_id"] = str(sample_user["_id"])
        st.session_state["current_username"] = sample_user["username"]
    else:
        st.error("error: seed the db first")

if st.sidebar.button("Get random user"):
    pipeline = [{"$match": {"following": {"$not": {"$size": 0}}}}, {"$sample": {"size": 1}}]
    user = list(db.users.aggregate(pipeline))[0]
    st.session_state["current_user_id"] = str(user["_id"])
    st.session_state["current_username"] = user["username"]

current_uid = st.session_state["current_user_id"]
st.sidebar.info(f"User curent: **{st.session_state.get('current_username', 'unknown_user')}**")

limit = st.sidebar.slider("Posts count in feed", 10, 100, 20)
auto_refresh = st.sidebar.checkbox("Auto refresh", value=False)

st.sidebar.markdown("---")

st.sidebar.subheader("Cache performance")
hit_ratio, total_req, hits, misses = get_metrics()

col_m1, col_m2 = st.sidebar.columns(2)
col_m1.metric("Hit Rate", f"{hit_ratio:.1f}%")
col_m2.metric("Total Req", total_req)
st.sidebar.text(f"Hits: {hits} | Misses: {misses}")

st.sidebar.markdown("---")
st.sidebar.subheader("Top Active Users")
leaderboard = get_leaderboard()
if leaderboard:
    for rank, (user, score) in enumerate(leaderboard, 1):
        st.sidebar.text(f"{rank}. {user} - {int(score)} posts")
else:
    st.sidebar.caption("No data in leaderboard")

col1, col2 = st.columns(2)

with col1:
    st.header("MongoDB")
    st.caption("Pull Model: Aggregare la cerere (de pe disk)")
    
    try:
        posts_mongo, time_mongo = get_feed_mongo(current_uid, limit)
        
        st.metric(label="Latency (Disk)", value=f"{time_mongo:.4f} s")
                
    except Exception as e:
        st.error(f"eroare mongo: {e}")

with col2:
    st.header("Redis")
    st.caption("Push Model: List pre-calculata + hashes din memorie direct")
    
    try:
        posts_redis, time_redis = get_feed_redis(current_uid, limit)
        
        # speedup metric
        speedup = time_mongo / time_redis if time_redis > 0 else 0
        
        st.metric(
            label="Latency (Memory)", 
            value=f"{time_redis:.4f} s", 
            delta=f"{speedup:.1f}x faster",
            delta_color="normal"
        )
            
    except Exception as e:
        st.error(f"eroare redis: {e}")

st.divider()
st.subheader("Real-time latency comparison chart")

if "history" not in st.session_state:
    st.session_state["history"] = []

if len(posts_mongo) > 0:
    st.session_state["history"].append({
        "Index": len(st.session_state["history"]),
        "MongoDB": time_mongo,
        "Redis": time_redis
    })

# doar ultimele 30 de puncte ca sa nu aglomeram
if len(st.session_state["history"]) > 30:
    st.session_state["history"].pop(0)

# folosim pandas pentru chart
chart_data = pd.DataFrame(st.session_state["history"])
if not chart_data.empty:
    st.line_chart(
        chart_data, 
        x="Index", 
        y=["MongoDB", "Redis"], 
        color=["#FF4B4B", "#00C805"]
    )

if auto_refresh:
    time.sleep(1.5) # refresh la 1.5 sec
    st.rerun()