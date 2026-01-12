import streamlit as st
import pickle
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ------------------------------
# 1. Cấu hình trang
# ------------------------------
st.set_page_config(
    page_title="Movie Magic Recommender",
    page_icon="🍿",
    layout="wide"
)

# ------------------------------
# 2. Khởi tạo Session State (Lưu trạng thái ứng dụng)
# ------------------------------
if "history" not in st.session_state:
    st.session_state.history = []
if "mode" not in st.session_state:
    st.session_state.mode = None
if "selected_movie" not in st.session_state:
    st.session_state.selected_movie = None
if "random_movie" not in st.session_state:
    st.session_state.random_movie = None

# ------------------------------
# 3. TMDB API & Helper Functions
# ------------------------------
TMDB_API_KEY = "8265bd1679663a7ea12ac168da84d2e8"

def requests_retry_session(retries=5, backoff_factor=1, status_forcelist=(500, 502, 504)):
    session = requests.Session()
    retry = Retry(
        total=retries,
        read=retries,
        connect=retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session

def fetch_poster(movie_id):
    try:
        url = f"https://api.themoviedb.org/3/movie/{movie_id}?api_key={TMDB_API_KEY}"
        response = requests_retry_session().get(url)
        if response.status_code == 200:
            data = response.json()
            path = data.get("poster_path")
            return f"https://image.tmdb.org/t/p/w500{path}" if path else None
    except: return None

def fetch_trailer(movie_id):
    try:
        url = f"https://api.themoviedb.org/3/movie/{movie_id}/videos?api_key={TMDB_API_KEY}"
        response = requests_retry_session().get(url)
        if response.status_code == 200:
            for v in response.json().get("results", []):
                if v.get("type") == "Trailer" and v.get("site") == "YouTube":
                    return f"https://youtu.be/{v['key']}"
    except: return None

def get_movie_details(movie_id):
    try:
        url = f"https://api.themoviedb.org/3/movie/{movie_id}?api_key={TMDB_API_KEY}&append_to_response=credits"
        res = requests_retry_session().get(url)
        if res.status_code == 200:
            data = res.json()
            return {
                "rating": round(data.get("vote_average", 0), 1),
                "runtime": data.get("runtime"),
                "tagline": data.get("tagline"),
                "overview": data.get("overview"),
                "genres": ", ".join([g["name"] for g in data.get("genres", [])]),
                "director": ", ".join([c["name"] for c in data.get("credits", {}).get("crew", []) if c.get("job") == "Director"]),
                "cast": data.get("credits", {}).get("cast", [])[:5]
            }
    except: return None

def recommend(movie_title):
    idx = movies[movies["title"] == movie_title].index[0]
    distances = sorted(list(enumerate(similarity[idx])), reverse=True, key=lambda x: x[1])
    recs = []
    for i in distances[1:6]:
        m_id = movies.iloc[i[0]].movie_id
        recs.append({
            "title": movies.iloc[i[0]].title,
            "poster": fetch_poster(m_id),
            "trailer": fetch_trailer(m_id)
        })
    return recs

# ------------------------------
# 4. Load Data
# ------------------------------
import os
import pickle

base_path = "/content" # Đường dẫn mặc định của Colab

try:
    # Đảm bảo dùng 'rb' (read binary)
    with open(os.path.join(base_path, "movie_list.pkl"), 'rb') as f:
        movies = pickle.load(f)
    with open(os.path.join(base_path, "similarity.pkl"), 'rb') as f:
        similarity = pickle.load(f)
except Exception as e:
    st.error(f"Lỗi đọc file: {e}")
    st.stop()
# ------------------------------
# 5. Giao diện chính (UI)
# ------------------------------
st.markdown("<h1 style='text-align: center; color: #FF4B4B;'>🎬 Movie Magic Recommender</h1>", unsafe_allow_html=True)

# Tìm kiếm & Surprise
col1, col2 = st.columns([3, 1])
with col1:
    selected = st.selectbox("Tìm kiếm phim bạn yêu thích:", movies["title"].values)
    if st.button("Xem chi tiết & Gợi ý"):
        st.session_state.mode = "search"
        st.session_state.selected_movie = selected
with col2:
    if st.button("🎭 Ngẫu nhiên"):
        random_m = movies.sample(1).iloc[0]
        st.session_state.mode = "surprise"
        st.session_state.selected_movie = random_m["title"]

# Hiển thị nội dung
if st.session_state.selected_movie:
    title = st.session_state.selected_movie
    movie_id = movies[movies["title"] == title].iloc[0].movie_id

    # Lưu lịch sử
    if not st.session_state.history or st.session_state.history[-1] != movie_id:
        st.session_state.history.append(movie_id)

    details = get_movie_details(movie_id)
    st.markdown("---")

    d_col1, d_col2 = st.columns([1, 2])
    with d_col1:
        poster = fetch_poster(movie_id)
        if poster: st.image(poster, use_container_width=True)
    with d_col2:
        st.header(title)
        if details:
            st.write(f"⭐ **Đánh giá:** {details['rating']}/10 | 🕒 **Thời lượng:** {details['runtime']} phút")
            st.write(f"🎭 **Thể loại:** {details['genres']}")
            st.info(details['tagline'] if details['tagline'] else "No tagline")
            st.write(f"📖 **Nội dung:** {details['overview']}")
            st.write(f"🎬 **Đạo diễn:** {details['director']}")

            trailer = fetch_trailer(movie_id)
            if trailer: st.video(trailer)

    # Gợi ý phim tương tự
    st.subheader("🚀 Phim tương tự có thể bạn sẽ thích")
    recommendations = recommend(title)
    rec_cols = st.columns(5)
    for i, r in enumerate(recommendations):
        with rec_cols[i]:
            if r["poster"]: st.image(r["poster"], use_container_width=True)
            st.caption(r["title"])

# Sidebar Lịch sử
with st.sidebar:
    st.header("🕒 Đã xem gần đây")
    for h_id in reversed(st.session_state.history[-5:]):
        h_title = movies[movies["movie_id"] == h_id].iloc[0]["title"]
        if st.button(h_title, key=f"h_{h_id}", use_container_width=True):
            st.session_state.selected_movie = h_title
            st.rerun()
