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
import webbrowser

# HTML 파일 열기
if "html_opened" not in st.session_state:
    file_path = os.path.abspath("translated_output.html")
    webbrowser.open(f"file://{file_path}")
    st.session_state.html_opened = True

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
    {
        "id": "mentor_001",
        "name": "Alice Kim",
        "expertise": "Business Strategy",
        "style": "Analytical",
        "strengths": ["Strategic Planning", "Growth Mindset", "Balanced Perspective"],
        "leadership": "Collaborative",
        "bio": "Former CEO with 20+ years in scaling online businesses. Passionate about sustainable growth and mentoring future leaders."
    },
    {
        "id": "mentor_002",
        "name": "David Lee",
        "expertise": "Legal Support",
        "style": "Direct",
        "strengths": ["Risk Management", "Protective Guidance", "Honest Feedback"],
        "leadership": "Formal",
        "bio": "Legal advisor specializing in fintech and startup law. Known for clear communication and decisive support.",
        "tags": ["legal", "compliance", "contract", "startup", "fintech", "law", "chatbot"]
    },
    {
        "id": "mentor_003",
        "name": "Sophie Park",
        "expertise": "Marketing & Branding",
        "style": "Empathetic",
        "strengths": ["Active Listening", "Creative Problem Solving", "Nurturing"],
        "leadership": "Psychosocial",
        "bio": "Brand strategist with global agency experience. Focuses on personal branding and inclusive leadership."
    },
    {
        "id": "mentor_004",
        "name": "Paul Zahra",
        "expertise": "Retail & Digital Transformation",
        "style": "Collaborative",
        "strengths": ["Personal Branding", "Growth Mindset", "Inclusive Leadership"],
        "leadership": "Career-focused",
        "bio": "Ex-CEO of major retail brands. Expert in digital transformation and building resilient organizations."
    },
    {
        "id": "mentor_005",
        "name": "Tony Nash",
        "expertise": "E-commerce & Innovation",
        "style": "Career-focused",
        "strengths": ["Innovation", "Customer Engagement", "Sustainable Growth"],
        "leadership": "Reverse",
        "bio": "Founder of a leading online bookstore. Renowned for innovative strategies and peer learning.",
        "tags": ["ai", "chatbot", "nlp", "customer", "startup"]
    },
    {
        "id": "mentor_003",
        "name": "Sophie Park",
        "expertise": "Marketing & Branding",
        "style": "Empathetic",
        "strengths": ["Active Listening", "Creative Problem Solving", "Nurturing"],
        "leadership": "Psychosocial",
        "bio": "Brand strategist with global agency experience. Focuses on personal branding and inclusive leadership.",
        "tags": ["branding", "communication", "nlp", "ui", "startup"]
        }
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

# ---------- 멘토-팀 매칭 시각화 ----------
def mentor_team_matching_visualization():
    st.title("🔗 Mentor-Team Matching")
    st.markdown("""
    <div style='font-size:1.1em; color:#444; margin-bottom:18px;'>
        Enter your team's characteristics and see which mentors best match your needs!
    </div>
    """, unsafe_allow_html=True)

    # 예시 멘토 풀 (기존 MENTORS 사용)
    mentor_pool = MENTORS

    # 사용자 입력 폼
    with st.form("team_input_form", clear_on_submit=True):
        team_name = st.text_input("Team Name", value="", placeholder="e.g. Team Alpha")
        team_topic = st.text_input("Project Topic", value="", placeholder="e.g. AI Service, Branding, Legal Advice")
        team_tags = st.text_input("Team Keywords (comma separated)", value="", placeholder="e.g. AI, 창업, Python")
        desired_mentor_style = st.selectbox("Desired Mentor Style", ["Any", "Analytical", "Direct", "Empathetic"])
        submitted = st.form_submit_button("Show Top 3 Mentors")
    
    if submitted:
        # 입력값 정리
        input_tags = [t.strip().lower() for t in team_tags.split(",") if t.strip()]
        style = desired_mentor_style if desired_mentor_style != "Any" else None

        # 간단한 매칭 점수: 태그 겹침 개수 + 스타일 일치(가산)
        scored = []
        for m in mentor_pool:
            mentor_tags = [tag.lower() for tag in m.get("tags",[])]
            tag_score = len(set(mentor_tags) & set(input_tags))
            style_score = 1 if (style and m.get("style") == style) else 0
            total_score = tag_score + style_score
            scored.append({**m, "score": total_score, "tag_score": tag_score, "style_score": style_score})
        top3 = sorted(scored, key=lambda x: -x["score"])[:3]

        st.markdown(f"### 🏅 Top 3 Mentor Matches for **{team_name or 'Your Team'}**")
        for idx, mentor in enumerate(top3, 1):
            st.markdown(f"""
            <div style='margin:15px 0; padding:16px 22px; background:#f7fafd; border-radius:13px; border:1.5px solid #e5eafe;'>
                <b>{idx}. {mentor['name']}</b> <span style='color:#888;'>({mentor['expertise']})</span><br>
                <b>Style:</b> {mentor.get('style','-')}<br>
                <b>Score:</b> {mentor['score']} 
                <span style='color:#aaa;'>(Tag: {mentor['tag_score']}, Style: {mentor['style_score']})</span><br>
                <b>Tags:</b> {', '.join(mentor.get('tags',[]))}
            </div>
            """, unsafe_allow_html=True)
        if not top3 or all(m["score"] == 0 for m in top3):
            st.info("No suitable mentors found. Try adjusting your keywords or style.")

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
        if st.button("🎤 Start translation", key="start_translation", use_container_width=True):
            start_translation()
    with col2:
        if st.button("⏹️ Stop", key="stop_translation", use_container_width=True):
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

# ---------- 메인 화면 ----------
tab1, tab2, tab3, tab4, tab5, tab6  = st.tabs([ "🔗 Mentor-Team Matching", "🧑‍🏫 Mentor Profile", "💬 Chatroom", "📄 Community", "🎯 Role Recommendation", "📝 Meeting Summary"])

with tab1: 
    mentor_team_matching_visualization()
with tab2:
    mentor_profile_ui()
with tab3:
    mentor_chat_ui()
with tab4:
    item_community_ui()
with tab5:
    task_recommendation_ui()
with tab6:
    st.markdown(
        """
        <style>
        .ms-title {
            font-size: 2.3rem;
            font-weight: 800;
            margin-bottom: 0.7em;
            letter-spacing: -1px;
        }
        .ms-section {
            margin-bottom: 1.6em;
        }
        .ms-section h3 {
            display: flex;
            align-items: center;
            gap: 0.5em;
            font-size: 1.25rem;
            font-weight: 700;
            margin-bottom: 0.2em;
        }
        .ms-box {
            background: #fafbfc;
            border-radius: 10px;
            padding: 1.1em 1.5em 1.1em 1.5em;
            margin-bottom: 0.8em;
        }
        .ms-task-list ol {
            margin-left: 1.1em;
        }
        .ms-task-list li {
            margin-bottom: 0.3em;
        }
        .ms-bullet-list {
            margin-left: 1.1em;
        }
        .ms-bullet-list li {
            margin-bottom: 0.25em;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    st.markdown('<div class="ms-title">📝 Meeting Summary</div>', unsafe_allow_html=True)

    # 상단 정보
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(
            """
            <div class="ms-section">
                <h3>📅 Next Meeting</h3>
                <div class="ms-box">
                    <b>Date & Time:</b> Next Tuesday at 10 AM
                </div>
            </div>
            """, unsafe_allow_html=True
        )
    with col2:
        st.markdown(
            """
            <div class="ms-section">
                <h3>📌 Topic</h3>
                <div class="ms-box">
                    API Risk Insurance Model Design
                </div>
            </div>
            """, unsafe_allow_html=True
        )

    # Task List
    st.markdown(
        """
        <div class="ms-section">
            <h3>✅ Task List</h3>
            <div class="ms-box ms-task-list">
                <ol>
                    <li>Finalize data collection and establish guidelines for API classification.</li>
                    <li>Refine the insurance premium pricing model based on traffic segments.</li>
                    <li>Develop risk scenarios based on recent fintech issues.</li>
                </ol>
            </div>
        </div>
        """, unsafe_allow_html=True
    )

    # 의견/피드백 2컬럼
    col3, col4 = st.columns(2)
    with col3:
        st.markdown(
            """
            <div class="ms-section">
                <h3>💡 Team Members' Opinions</h3>
                <div class="ms-box">
                    <ul class="ms-bullet-list">
                        <li>Data collection is mostly complete, but there are issues with SLA violations and missing data in smaller APIs.</li>
                        <li>The classification of APIs into <b>'major'</b> and <b>'minor'</b> based on call volume and failure rates is a good approach, though more statistical validation is needed.</li>
                        <li>The insurance premium model needs adjustments, particularly for real-time APIs where prediction errors are larger.</li>
                        <li>Risk scenarios are being developed, but there is a need to incorporate more recent fintech-related issues.</li>
                    </ul>
                </div>
            </div>
            """, unsafe_allow_html=True
        )
    with col4:
        st.markdown(
            """
            <div class="ms-section">
                <h3>🧑‍🏫 Mentor Feedback</h3>
                <div class="ms-box">
                    <ul class="ms-bullet-list">
                        <li>Previous scenarios were deemed too general; the team is encouraged to include specific recent incidents, such as authentication API failures leading to payment errors.</li>
                    </ul>
                </div>
            </div>
            """, unsafe_allow_html=True
        )