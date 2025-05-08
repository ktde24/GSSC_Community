import streamlit as st
st.set_page_config(page_title="Mentor Service Platform", layout="wide")

import pandas as pd
import sounddevice as sd
import os
from datetime import datetime

from task_recommendation import task_recommendation_ui
from sound import RealTimeTranslator
from threading import Thread
import time
import sys
from queue import Queue
from streamlit_autorefresh import st_autorefresh


if sys.version_info >= (3, 10):
    import collections.abc
    import collections
    collections.MutableMapping = collections.abc.MutableMapping
    collections.Sequence = collections.abc.Sequence
    collections.Mapping = collections.abc.Mapping

import asyncio
try:
    asyncio.get_running_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())

# ---------- 파일 경로 ----------
MENTOR_CHAT_CSV = "data/mentor_chats.csv"
ITEM_COMMUNITY_CSV = "data/item_community.csv"
MENTOR_REVIEW_CSV = "data/mentor_reviews.csv"

# ---------- 멘토 더미 데이터 ----------
MENTORS = [
    {"id": "mentor_001", "name": "Alice Kim", "expertise": "Business Strategy", "style": "Analytical"},
    {"id": "mentor_002", "name": "David Lee", "expertise": "Legal Support", "style": "Direct"},
    {"id": "mentor_003", "name": "Sophie Park", "expertise": "Marketing & Branding", "style": "Empathetic"}
]

# ---------- CSV 로딩 ----------
def safe_load_csv(path):
    try:
        if not os.path.exists(path) or os.path.getsize(path) == 0:
            return []
        df = pd.read_csv(path)
        return df.to_dict("records")
    except Exception:
        return []
    

# ---------- 공통 스타일 ----------
st.markdown("""
<style>
body, div, textarea, input, button {
    font-family: 'Pretendard', 'Noto Sans KR', sans-serif !important;
}
.stButton>button {
    background: #4f8bf9 !important;
    color: #fff !important;
    border-radius: 9px !important;
    font-weight: bold !important;
    font-size: 16px !important;
    box-shadow: 0 1px 4px rgba(0,0,0,0.08) !important;
}
.stTextInput>div>input, .stTextArea textarea {
    border-radius: 8px !important;
    border: 1.5px solid #dbeafe !important;
    background: #f7fafd !important;
}
.chat-bubble {
    display: inline-block;
    max-width: 350px;
    min-width: 60px;
    padding: 12px 18px;
    border-radius: 18px;
    margin-bottom: 12px;
    word-break: break-word;
    box-shadow: 0 2px 8px rgba(79,139,249,0.08);
    font-size: 15px;
    color: #222;
    position: relative;
}
.chat-bubble.user {
    background: #fbe54d;
    margin-left: auto;
    margin-right: 0;
}
.chat-bubble.mentor {
    background: #f2f2f2;
    margin-right: auto;
    margin-left: 0;
}
.chat-timestamp {
    font-size: 11px;
    color: #888;
    text-align: right;
    margin-top: 4px;
}
.comment-card {
    background: #fff;
    border-radius: 13px;
    box-shadow: 0 2px 8px rgba(79,139,249,0.08);
    border: 1.5px solid #e5eafe;
    margin-bottom: 16px;
    padding: 13px 18px 9px 18px;
}
.comment-header {
    display: flex;
    align-items: center;
    margin-bottom: 2px;
}
.comment-user {
    color: #4f8bf9;
    font-weight: 600;
    font-size: 1.06em;
}
.comment-time {
    font-size: 11px;
    color: #888;
    margin-left: 10px;
}
.comment-content {
    font-size: 1.09em;
    color: #222;
    line-height: 1.6;
    margin-top: 2px;
    word-break: break-word;
}
</style>
""", unsafe_allow_html=True)

# ---------- 멘토 프로필 및 리뷰 ----------
def mentor_profile_ui():
    st.title("🧑‍🏫 Mentor Profile")
    selected_mentor = st.selectbox("Select a Mentor to rate:", MENTORS, format_func=lambda x: x["name"])

    # 프로필 사진 + 정보 한 줄에
    st.markdown(f"""
    <div style='
        display: flex;
        align-items: center;
        gap: 18px;
        margin: 10px 0 18px 0;
    '>
        <img src="https://cdn-icons-png.flaticon.com/512/3135/3135715.png"
             width="70"
             style="border-radius: 50%; border: 2px solid #e5eafe; margin: 0;">
        <div>
            <div style='font-size:1.18em; font-weight:700; color:#222; margin-bottom:3px;'>{selected_mentor['name']}</div>
            <div style='color:#555; margin-bottom:1px;'><b>Expertise:</b> {selected_mentor['expertise']}</div>
            <div style='color:#888;'><b>Style:</b> {selected_mentor['style']}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    with st.expander("⭐ Write a Review", expanded=True):
        stars = st.radio("Rating", [1, 2, 3, 4, 5], horizontal=True, format_func=lambda x: "★" * x)
        review_text = st.text_area("Write your feedback")
        if st.button("Submit", key="submit_review"):
            new_review = {
                "mentor_id": selected_mentor['id'],
                "user_id": "user_temp",
                "rating": stars,
                "review": review_text,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            try:
                df = pd.read_csv(MENTOR_REVIEW_CSV)
                df = pd.concat([df, pd.DataFrame([new_review])], ignore_index=True)
            except FileNotFoundError:
                df = pd.DataFrame([new_review])
            df.to_csv(MENTOR_REVIEW_CSV, index=False)
            st.success("✅ Thank you! Your review has been submitted.")

    st.subheader("📄 Recent Reviews")
    try:
        reviews = pd.read_csv(MENTOR_REVIEW_CSV)
        filtered = reviews[reviews["mentor_id"] == selected_mentor["id"]].sort_values(by="timestamp", ascending=False).head(5)
        for _, row in filtered.iterrows():
            stars = "★" * int(row["rating"])
            st.markdown(f"""
            <div class='comment-card'>
                <div class='comment-header'>
                    <span class='comment-user'>Anonymous</span>
                    <span class='comment-time'>{row['timestamp']}</span>
                </div>
                <div class='comment-content'>{stars} <span style='color:#999; font-size:0.97em;'>({row['rating']}/5)</span> {row['review']}</div>
            </div>
            """, unsafe_allow_html=True)
    except FileNotFoundError:
        st.info("No reviews available yet.")

# ---------- 멘토-멘티 채팅방 ----------
def mentor_chat_ui():
    
    # 세션 상태 초기화
    if "translation_running" not in st.session_state:
        st.session_state.translation_running = False
    if "translation_placeholder" not in st.session_state:
        st.session_state.translation_placeholder = st.empty()
    if "translator" not in st.session_state:
        st.session_state.translator = RealTimeTranslator()
    if "last_translation" not in st.session_state:
        st.session_state['last_translation'] = "번역 결과가 여기에 표시됩니다."

    #st_autorefresh(interval=2000, key="translationrefresh")

    # Google Meet 섹션 UI
    st.markdown("""
    <div style='background-color:#e6f2ff; padding:22px 30px; border-radius:18px; margin-bottom:28px;'>
        <h2 style='margin:0 0 8px 0;'>👥 Mentor-Mentee Chatroom</h2>
        <span style='font-size:16px;'>Chat with your mentor in real time.<br><b>Google Meet</b> video call available.</span><br>
        <a href='https://meet.google.com/new' target='_blank'
            style='display:inline-block; margin-top:14px; background:#34a853; color:white; padding:10px 28px; border-radius:9px; text-decoration:none; font-weight:bold; font-size:16px;'>
            📹 Start Google Meet
        </a>
    </div>
    """, unsafe_allow_html=True)

    # 번역 버튼
    col1, col2, _ = st.columns([1,1,6])
    with col1:
        if st.button("🎤 번역 시작", key="start_translation", use_container_width=True):
            start_translation()
    with col2:
        if st.button("⏹️ 번역 중지", key="stop_translation", use_container_width=True):
            stop_translation()

    # 번역 자막 영역
    translation_container = st.container()
    with translation_container:
        st.markdown(
            f"""<div style='background:#f0f2f6; padding:12px 16px; border-radius:8px; margin:10px 0;'>
            {st.session_state.get('last_translation','번역 결과가 여기에 표시됩니다.')}
            </div>""",
            unsafe_allow_html=True
        )

    # 채팅 UI
    if "mentor_chat_history" not in st.session_state:
        chats = safe_load_csv(MENTOR_CHAT_CSV)
        chat_log = []
        if chats:
            try:
                chat_log = eval(chats[0].get("messages", "[]"))
            except:
                chat_log = []
        st.session_state.mentor_chat_history = chat_log

    st.markdown("""
    <hr style='border: 0; border-top: 2px solid #e0e0e0; margin: 24px 0 12px 0;'>
    <h4 style='margin-bottom: 12px; color:#2a2a2a;'>💬 Conversation History</h4>
    """, unsafe_allow_html=True)
    for msg in st.session_state.mentor_chat_history:
        is_user = (msg.get("role", "user") == "user")
        align = 'flex-end' if is_user else 'flex-start'
        bubble_class = "user" if is_user else "mentor"
        st.markdown(f"""
        <div style='width:100%; display:flex; justify-content:{align};'>
            <div class='chat-bubble {bubble_class}'>
                {msg['content']}
                <div style="font-size: 0.8rem; color: #666; margin-top: 4px;">
                    {msg.get('timestamp', '')}
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # 입력 폼
    with st.form("mentor_chat_form", clear_on_submit=True):
        input_col, btn_col = st.columns([5, 1])
        with input_col:
            prompt = st.text_input("Type your message...", label_visibility="collapsed", placeholder="Write a message...")
        with btn_col:
            submitted = st.form_submit_button("Send", use_container_width=True)
        if submitted and prompt:
            now = datetime.now().strftime("%Y-%m-%d %H:%M")
            st.session_state.mentor_chat_history.append({
                "role": "user",
                "content": prompt,
                "timestamp": now
            })
            pd.DataFrame([{"messages": str(st.session_state.mentor_chat_history)}]).to_csv(MENTOR_CHAT_CSV, index=False)
            st.rerun()

def start_translation():
    if not st.session_state.translation_running:
        st.session_state.translation_running = True
        st.session_state.translator.running = True
        try:
            device_idx = st.session_state.translator.find_virtual_device()
            st.session_state.translator.stream = sd.InputStream(
                samplerate=16000,
                channels=1,
                dtype='float32',
                callback=st.session_state.translator.audio_callback,
                device=device_idx
            )
            st.session_state.translator.stream.start()

            def thread_func(translator):
                is_running = True
                while is_running:
                    try:
                        is_running = translator.running
                        translated = translator.process_audio()
                        if translated:
                            st.session_state['last_translation'] = translated
                        time.sleep(0.1)
                    except Exception as e:
                        print(f"Thread error: {e}")
                        time.sleep(0.1)

            Thread(
                target=thread_func,
                args=(st.session_state.translator,),
                daemon=True
            ).start()

        except Exception as e:
            st.error(f"번역 시작 오류: {e}")
            st.session_state.translation_running = False
            st.session_state.translator.running = False

def stop_translation():
    st.session_state.translation_running = False
    st.session_state.translator.running = False
    st.session_state['last_translation'] = "번역이 중지되었습니다."
    if hasattr(st.session_state.translator, 'stream') and st.session_state.translator.stream:
        try:
            st.session_state.translator.stream.stop()
            st.session_state.translator.stream.close()
        except:
            pass
    st.session_state.translation_placeholder.empty()
    
# ---------- 아이템 커뮤니티 ----------
def item_community_ui():
    st.markdown("""
    <h1 style='margin-bottom:10px;'>🗂️ Item Community</h1>
    <p style='font-size:1.1em; color:#444;'>Browse items, expand to see details and comments, and join the discussion.</p>
    """, unsafe_allow_html=True)

    items = [
        {"id": "1", "title": "Body Lotion", "desc": "Lotion suitable for all skin types.", "percent": 40.0},
        {"id": "2", "title": "Hair Loss Shampoo", "desc": "Shampoo for preventing hair loss.", "percent": 45.0},
        {"id": "3", "title": "Kids Lip Balm", "desc": "Safe lip balm for children.", "percent": 50.0},
    ]

    dummy_comments = {
        "1": [
            {"user": "Alice", "content": "Great idea!", "timestamp": "2025-04-19 10:00"},
            {"user": "Bob", "content": "Is it hypoallergenic?", "timestamp": "2025-04-19 10:05"},
        ],
        "2": [
            {"user": "Chris", "content": "Is it suitable for sensitive scalp?", "timestamp": "2025-04-19 09:50"},
        ],
        "3": [
            {"user": "Daisy", "content": "Kids will love this!", "timestamp": "2025-04-19 09:40"}
        ]
    }

    if "item_comments" not in st.session_state:
        st.session_state.item_comments = {}
        comments = safe_load_csv(ITEM_COMMUNITY_CSV)
        for item in items:
            item_id = item["id"]
            found = False
            for row in comments:
                if str(row.get("item_id")) == str(item_id):
                    try:
                        st.session_state.item_comments[item_id] = eval(row.get("comments", "[]"))
                    except:
                        st.session_state.item_comments[item_id] = []
                    found = True
                    break
            if not found:
                st.session_state.item_comments[item_id] = dummy_comments[item_id]

    for item in items:
        with st.expander(f"**{item['title']}**  |  Equity: {item['percent']}%", expanded=False):
            st.markdown(f"""
            <div style='margin-bottom:10px; color:#333; font-size:1.08em;'>{item['desc']}</div>
            <div style='margin-bottom:10px;'><b>Comments</b></div>
            """, unsafe_allow_html=True)
            item_id = item["id"]
            if st.session_state.item_comments[item_id]:
                for c in st.session_state.item_comments[item_id]:
                    st.markdown(f"""
                    <div class='comment-card'>
                        <div class='comment-header'>
                            <span class='comment-user'>{c.get('user', 'Anonymous')}</span>
                            <span class='comment-time'>{c.get('timestamp','')}</span>
                        </div>
                        <div class='comment-content'>{c.get('content','')}</div>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.markdown("<div style='color:#bbb; margin-bottom:10px;'>No comments yet. Be the first to comment!</div>", unsafe_allow_html=True)
            with st.form(f"comment_form_{item_id}", clear_on_submit=True):
                content = st.text_area("Add a comment as Anonymous", key=f"comment_input_{item_id}")
                submitted = st.form_submit_button("Submit", use_container_width=True)
                if submitted and content:
                    now = datetime.now().strftime("%Y-%m-%d %H:%M")
                    st.session_state.item_comments[item_id].append({
                        "user": "Anonymous",
                        "content": content,
                        "timestamp": now
                    })
                    comments = safe_load_csv(ITEM_COMMUNITY_CSV)
                    updated = False
                    for idx, row in enumerate(comments):
                        if str(row.get("item_id")) == str(item_id):
                            comments[idx]["comments"] = str(st.session_state.item_comments[item_id])
                            updated = True
                            break
                    if not updated:
                        comments.append({
                            "item_id": item_id,
                            "comments": str(st.session_state.item_comments[item_id])
                        })
                    pd.DataFrame(comments).to_csv(ITEM_COMMUNITY_CSV, index=False)
                    st.success("Comment submitted!")
                    st.rerun()

# ---------- 가격 탭 -----------
def pricing_ui():
    st.title("💵 Service Pricing")
    pricing = [
        {"time": "30 minutes (Google Meet)", "price": "$3"},
        {"time": "60 minutes (Google Meet)", "price": "$5"},
        {"time": "90 minutes (Google Meet)", "price": "$7"},
    ]

    for item in pricing:
        st.markdown(f"""
        <div style='
            background: #fff;
            border: 1.5px solid #e5eafe;
            border-radius: 13px;
            padding: 18px 24px;
            margin-bottom: 18px;
            box-shadow: 0 2px 8px rgba(79,139,249,0.08);
        '>
            <div style='font-size:1.2em; font-weight:bold; color:#333;'>{item['time']}</div>
            <div style='font-size:1.5em; font-weight:bold; color:#4f8bf9; margin-top:8px;'>{item['price']}</div>
        </div>
        """, unsafe_allow_html=True)


# ---------- 메인 화면 ----------
tab1, tab2, tab3, tab4, tab5 = st.tabs(["🧑‍🏫 Mentor Profile", "💬 Chatroom", "📄 Community", "💵 Pricing", "🎯 Role Recommendation"])

with tab1:
    mentor_profile_ui()
with tab2:
    mentor_chat_ui()
with tab3:
    item_community_ui()
with tab4:
    pricing_ui()
with tab5:
    task_recommendation_ui()