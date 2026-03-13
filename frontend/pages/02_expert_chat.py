import streamlit as st
import requests
import time
from components.sidebar import render_sidebar

API_BASE_URL = "http://localhost:8000/api/v1"

# ---------------------------------------------------------
# Page Configuration & State
# ---------------------------------------------------------
st.set_page_config(
    page_title="무한상사 회의 거버넌스 시스템 - 하이브리드 검증/자문",
    layout="wide",
    initial_sidebar_state="expanded",
)

if "hybrid_logs" not in st.session_state:
    st.session_state.hybrid_logs = []
if "current_meeting" not in st.session_state:
    st.session_state.current_meeting = None
if "system_mode" not in st.session_state:
    st.session_state.system_mode = "검증 모드"

# ---------------------------------------------------------
# Custom Enterprise CSS (디자인 가독성 강화)
# ---------------------------------------------------------
st.markdown(
    """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;600;700;900&display=swap');
    .stApp { background-color: #0B0F19; font-family: 'Noto Sans KR', sans-serif; color: #F8FAFC; }

    .page-title { font-size: 30px; font-weight: 900; color: #FFFFFF; margin-bottom: 8px; letter-spacing: -0.5px; }
    .subtitle-text { font-size: 14px; color: #94A3B8; margin-bottom: 20px; font-weight: 400; }
    
    div[data-testid="stVerticalBlockBorderWrapper"] {
        background-color: #1E293B !important; border: 1px solid #334155 !important;
        border-radius: 8px !important; padding: 20px 24px !important; 
        margin-bottom: 20px !important; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    div[data-testid="stVerticalBlockBorderWrapper"]:first-of-type { padding: 15px 24px 5px 24px !important; }

    .context-banner { background-color: rgba(37, 99, 235, 0.1); border: 1px solid rgba(37, 99, 235, 0.3); border-radius: 6px; padding: 10px 16px; margin-bottom: 20px; display: flex; align-items: center; justify-content: space-between; }
    .ctx-indicator { display: flex; align-items: center; gap: 8px; font-size: 13px; font-weight: 700; color: #60A5FA; }
    .ctx-pulse { width: 8px; height: 8px; background-color: #3B82F6; border-radius: 50%; box-shadow: 0 0 0 0 rgba(59, 130, 246, 0.7); animation: pulse 2s infinite; }
    @keyframes pulse { 0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(59, 130, 246, 0.7); } 70% { transform: scale(1); box-shadow: 0 0 0 6px rgba(59, 130, 246, 0); } 100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(59, 130, 246, 0); } }

    .panel-title { font-size: 15px; font-weight: 700; color: #FFFFFF; border-bottom: 2px solid #334155; padding-bottom: 10px; margin-bottom: 15px; }
    .ctx-card { background-color: rgba(255,255,255,0.02); border: 1px solid #334155; border-radius: 6px; padding: 15px; margin-bottom: 15px; border-left: 3px solid #475569;}
    .ctx-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; font-size: 12px; font-weight: 700; }
    .ctx-text { font-size: 13px; color: #CBD5E1; line-height: 1.5; margin-top: 8px; }
    .src-badge { padding: 4px 8px; border-radius: 4px; font-size: 11px; font-weight: 700; display: inline-flex; align-items: center; gap: 4px; }

    .stTextInput > label, .stSelectbox > label, .stRadio > label { color: #CBD5E1 !important; font-size: 13px !important; font-weight: 600 !important; }

    @import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@24,400,1,0');
    div[role="radiogroup"] label[data-baseweb="radio"] p { font-weight: 700 !important; color: #F8FAFC !important; font-size: 14px !important; }
    div[role="radiogroup"] label:nth-child(1) p::before { content: "fact_check"; font-family: 'Material Symbols Outlined'; font-size: 20px; margin-right: 8px; color: #4ADE80; vertical-align: middle; }
    div[role="radiogroup"] label:nth-child(2) p::before { content: "school"; font-family: 'Material Symbols Outlined'; font-size: 20px; margin-right: 8px; color: #FBBF24; vertical-align: middle; }
    
    /* [수정 포인트] 채팅 메시지 내부의 모든 요소(리스트 포함) 가독성 강제 적용 */
    .stChatMessage { 
        background-color: rgba(255, 255, 255, 0.05) !important; 
        border-bottom: 1px solid #334155; 
        padding: 15px !important; 
        margin-bottom: 15px !important; 
        border-radius: 10px !important; 
    }
    .stChatMessage p, .stChatMessage li, .stChatMessage span, .stChatMessage div { 
        color: #F8FAFC !important; 
        font-size: 15px !important; 
        line-height: 1.6 !important; 
    }
    .stChatMessage li { margin-bottom: 8px !important; }
</style>
""",
    unsafe_allow_html=True,
)

render_sidebar()


# ---------------------------------------------------------
# Data Fetcher & Streaming Helper
# ---------------------------------------------------------
@st.cache_data(ttl=10)
def get_real_meeting_list():
    """백엔드 API를 호출하여 실제 DB에 저장된 회의 목록을 가져옵니다."""
    try:
        res = requests.get(f"{API_BASE_URL}/chat/meetings")
        if res.status_code == 200:
            meetings = res.json()
            if meetings:
                return {m["display_name"]: m["id"] for m in meetings}
    except Exception as e:
        pass
    return {"저장된 회의록이 없습니다.": None}


def stream_expert_answer(meeting_id: str, mode: str, query: str):
    url = f"{API_BASE_URL}/chat/ask"
    payload = {
        "meeting_id": meeting_id,
        "mode": mode,
        "prompt": query,
        "include_past_db": False,
    }
    try:
        with requests.post(url, json=payload, stream=True) as response:
            response.raise_for_status()
            for chunk in response.iter_content(chunk_size=None, decode_unicode=True):
                if chunk:
                    yield chunk
    except Exception as e:
        yield f"\n\n❌ 백엔드 통신 오류: {str(e)}"


# ---------------------------------------------------------
# Main Content Area
# ---------------------------------------------------------
st.markdown(
    '<div class="page-title">하이브리드 회의 검증 및 전문가 자문 시스템</div>',
    unsafe_allow_html=True,
)
st.markdown(
    '<div class="subtitle-text">공식 의사결정의 엄격한 사실 검증과 도메인 전문가의 다각도 자문을 동시에 지원합니다.</div>',
    unsafe_allow_html=True,
)

# 1️⃣ Top Control Bar (Mode Selector & Context)
with st.container(border=True):
    col_mode, col_meet = st.columns([6.5, 3.5])
    with col_mode:
        selected_mode = st.radio(
            "시스템 작동 모드 선택",
            [
                "공식 검증 모드 (사실 확인 및 근거 추적)",
                "전문가 자문 모드 (개념 학습 및 해결책 제시)",
            ],
            horizontal=True,
            label_visibility="collapsed",
        )
        st.session_state.system_mode = (
            "검증 모드" if "검증" in selected_mode else "자문 모드"
        )

    with col_meet:
        meeting_dict = get_real_meeting_list()
        meeting_options = list(meeting_dict.keys())

        default_index = 0
        if "meeting_id" in st.session_state and st.session_state.meeting_id:
            for i, m_id in enumerate(meeting_dict.values()):
                if m_id == st.session_state.meeting_id:
                    default_index = i
                    break

        selected_title = st.selectbox(
            "기준 대화 맥락 (회의 단위)",
            options=meeting_options,
            index=default_index,
            label_visibility="collapsed",
        )
        current_id = meeting_dict[selected_title]

        if current_id and current_id != st.session_state.current_meeting:
            st.session_state.current_meeting = current_id
            st.session_state.hybrid_logs = []
            st.rerun()

# 5️⃣ Knowledge Continuity Banner
st.markdown(
    f"""
<div class="context-banner">
    <div class="ctx-indicator"><div class="ctx-pulse"></div>현재 대화 맥락 유지 중: <strong>{selected_title}</strong></div>
    <div style="font-size:12px; color:#94A3B8;">DB 연결: 정상 (Vector DB 연동 완료)</div>
</div>
""",
    unsafe_allow_html=True,
)

col_main, col_right = st.columns([6.5, 3.5], gap="large")

with col_main:
    chat_container = st.container(height=500, border=True)

    with chat_container:
        if not st.session_state.hybrid_logs:
            st.markdown(
                """
            <div style="text-align: center; color: #64748B; margin-top: 180px;">
                <h3 style="color: #94A3B8; font-weight: 500;">AI 전문가에게 질문해 보세요.</h3>
                <p style="font-size: 14px;">"이 회의의 핵심 논점은 무엇인가요?"</p>
            </div>
            """,
                unsafe_allow_html=True,
            )

        for log in st.session_state.hybrid_logs:
            with st.chat_message(log["role"]):
                st.markdown(log["content"])

    is_disabled = current_id is None
    prompt = st.chat_input(
        (
            "회의가 없습니다. 영상을 먼저 분석해주세요."
            if is_disabled
            else "질의를 입력하세요"
        ),
        disabled=is_disabled,
    )

    if prompt:
        st.session_state.hybrid_logs.append({"role": "user", "content": prompt})
        with chat_container:
            with st.chat_message("user"):
                st.markdown(prompt)

            with st.chat_message("assistant"):
                stream_gen = stream_expert_answer(
                    st.session_state.current_meeting,
                    st.session_state.system_mode,
                    prompt,
                )
                full_response = st.write_stream(stream_gen)

        st.session_state.hybrid_logs.append(
            {"role": "assistant", "content": full_response}
        )

with col_right:
    st.markdown(
        '<div class="panel-title">참조 데이터 베이스 (RAG Sources)</div>',
        unsafe_allow_html=True,
    )

    with st.container(border=True):
        if len(st.session_state.hybrid_logs) > 0 and current_id:
            mode_color = (
                "#4ADE80" if st.session_state.system_mode == "검증 모드" else "#FBBF24"
            )
            st.markdown(
                f"""
            <div style="background-color: #0F172A; padding: 15px; border-radius: 6px; border: 1px solid #334155; margin-bottom: 15px;">
                <span style="color:{mode_color}; font-size:13px; font-weight:700;">✓ {st.session_state.system_mode} 활성화</span><br>
                <span style="color:#CBD5E1; font-size:13px; display:inline-block; margin-top:5px; line-height:1.5;">
                AI가 <b>{selected_title}</b>의 내용을 Chroma DB에서 벡터 검색하여 실시간으로 답변을 스트리밍했습니다.
                </span>
            </div>
            
            <div class="ctx-card" style="border-left-color: #3B82F6;">
                <div class="ctx-header">
                    <span class="src-badge" style="border: 1px solid #3B82F6; color: #3B82F6; background-color: rgba(59, 130, 246, 0.15);">
                        내부 회의 기록
                    </span>
                    <span style="font-size:12px; color:#4ADE80; font-weight:700;">Vector Matched</span>
                </div>
                <div style="font-size:11px; color:#94A3B8; margin-bottom:6px;">
                    <strong>출처:</strong> {selected_title} 
                </div>
                <div class="ctx-text">AI가 해당 회의록 내에서 질문과 가장 의미적으로 유사한 텍스트 조각들을 추출하여 답변의 근거로 활용했습니다.</div>
            </div>
            """,
                unsafe_allow_html=True,
            )
        else:
            st.info("질의를 입력하면 AI가 참조한 문서가 이곳에 표시됩니다.")
