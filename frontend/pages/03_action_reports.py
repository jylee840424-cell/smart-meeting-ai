# ==========================================================
# AI 분석 리포트 시각화 및 액션 플랜 관리 센터
# ==========================================================
import re
import sys
import os
import streamlit as st
import requests
from datetime import datetime
from components.sidebar import render_sidebar

# ----------------------------------------------------------
# 1. 경로 설정
# ----------------------------------------------------------
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.abspath(os.path.join(CURRENT_DIR, ".."))

if FRONTEND_DIR not in sys.path:
    sys.path.append(FRONTEND_DIR)

st.set_page_config(
    page_title="무한상사 거버넌스 - 액션 및 리포트",
    layout="wide",
    initial_sidebar_state="expanded",
)

render_sidebar()

API_BASE_URL = "http://localhost:8000/api/v1"

# ----------------------------------------------------------
# 2. UI 스타일
# ----------------------------------------------------------
st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Pretendard:wght@400;700&display=swap');
.stApp { background-color: #FFFFFF; font-family: 'Pretendard', sans-serif; color: #0F172A; }
.blue-point { color: #1D4ED8; font-weight: 800; }
.pink-point { color: #BE185D; font-weight: 800; }
.pkg-card {
    background-color: #F8FAFC; 
    border: 2px solid #E2E8F0; 
    border-radius: 16px; 
    padding: 25px; 
    min-height: 350px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.05);
    margin-bottom: 20px;
}
.card-status { font-size:18px; color:#1D4ED8; font-weight:800; margin-bottom:10px; }
.card-label { font-size:20px; font-weight:700; color:#0F172A; margin-bottom:15px; }
.card-content { font-size:17px !important; color:#475569 !important; line-height:1.6; white-space: pre-wrap; word-break: keep-all; text-align: justify;}
</style>
""",
    unsafe_allow_html=True,
)


# ----------------------------------------------------------
# 3. API 데이터 로드
# ----------------------------------------------------------
@st.cache_data(ttl=600)
def get_report_data():
    """
    FastAPI 서버에서 최신 회의 리포트 조회
    Streamlit 캐싱을 통해 10분간 데이터 재사용
    """
    try:
        res = requests.get(f"{API_BASE_URL}/meetings/details/latest", timeout=10)
        res.raise_for_status()
        return res.json()
    except Exception as e:
        st.error(f"데이터 로드 실패: {e}")
        return None


# ----------------------------------------------------------
# 카드 UI 생성
# ----------------------------------------------------------
def render_pkg_card(status, title, content):
    """회의 결과 카드 UI"""
    st.markdown(
        f"""
    <div class="pkg-card">
        <div class="card-status">{status}</div>
        <div class="card-label">{title}</div>
        <div class="card-content">{content}</div>
    </div>
    """,
        unsafe_allow_html=True,
    )


# ----------------------------------------------------------
# 데이터 문자열 정규화
# ----------------------------------------------------------
def normalize_to_string(val):
    """
    리스트 / dict / 문자열 데이터를
    화면 출력용 문자열로 변환
    """
    if isinstance(val, list):
        parts = []
        for item in val:
            if isinstance(item, dict):
                parts.append(", ".join([f"{k}: {v}" for k, v in item.items()]))
            else:
                parts.append(str(item))
        s = "\n".join([p.strip() for p in parts if str(p).strip()])
    else:
        s = str(val).strip()

    # 중복 라인 제거
    seen = set()
    dedup = []
    for ln in s.splitlines():
        ln = ln.strip()
        if ln and ln not in seen:
            dedup.append(ln)
            seen.add(ln)

    return "\n".join(dedup)


# ----------------------------------------------------------
# 액션 아이템 포맷팅
# ----------------------------------------------------------
def format_actions(actions_raw):
    """
    API에서 받은 action 데이터를
    화면에 표시할 문자열 형식으로 변환
    """

    if not actions_raw:
        return "배정된 액션 플랜이 없습니다."

    formatted_items = []

    for item in actions_raw:

        # dict 형태 데이터 처리
        if isinstance(item, dict):
            who = item.get("Who") or item.get("who") or "미정"
            what = item.get("What") or item.get("what") or "내용 없음"
            when = item.get("When") or item.get("when") or "기한 미정"

        # 문자열 형태 데이터 파싱
        else:
            text = str(item)
            who_match = re.search(r"Who:\s*([^,\n]+)", text)
            what_match = re.search(r"What:\s*([^,\n]+)", text)
            when_match = re.search(r"When:\s*([^,\n\)]+)", text)

            who = who_match.group(1).strip() if who_match else "미정"
            what = what_match.group(1).strip() if what_match else ""
            when = when_match.group(1).strip() if when_match else "기한 미정"

        # 문자열 정리 함수
        def clean_text(t):
            t = str(t)
            t = t.replace("👤", "").replace("{", "").replace("}", "")
            t = t.replace("'", "").replace('"', "").replace("-", "").strip()
            t = re.sub(r"(Who|What|When):\s*", "", t)
            return t

        c_who = clean_text(who)
        c_what = clean_text(what)
        c_when = clean_text(when)

        # 화면 출력 포맷 구성
        if c_what:
            line = "👤 "

            if c_who and c_who not in ["미정", "전체", ""]:
                line += f"{c_who} : "

            line += f"{c_what}"

            when_text = (
                f"(📅 기한: {c_when})" if c_when and c_when not in ["미정", ""] else ""
            )

            if when_text:
                line += f"\n{when_text}"

            formatted_items.append(line)

    return (
        "\n\n".join(formatted_items)
        if formatted_items
        else "내용을 불러올 수 없습니다."
    )


# ----------------------------------------------------------
# 4. HITL 문서 수정 팝업
# ----------------------------------------------------------
@st.dialog("🤖 AI 비서와 문서 협업", width="medium")
def hitl_document_editor(doc_key, doc_title, current_val, meeting_id):
    """
    AI를 이용한 문서 수정 인터페이스
    - 현재 내용 확인
    - 수정 요청 입력
    - 수정 결과 비교
    """

    st.markdown(f"**{doc_title} 실시간 수정**")

    # 원본 문서
    origin_text = normalize_to_string(current_val)

    st.text_area(
        "현재 문서 내용 (수정 전)", value=origin_text, height=150, disabled=True
    )

    # 수정 입력 영역
    col_input, col_btn = st.columns([4, 1])

    with col_input:
        edit_prompt = st.text_area(
            "AI 수정 지시",
            placeholder="(예: 더 간결하게 요약해줘)",
            key=f"hitl_prompt_{doc_key}",
            label_visibility="collapsed",
        )

    with col_btn:
        st.write("")
        st.write("")
        submit_edit = st.button(
            "✏️ 수정", use_container_width=True, key=f"hitl_submit_{doc_key}"
        )

    # AI 수정 요청
    if submit_edit:

        if not edit_prompt:
            st.warning("수정 지시를 입력해주세요.")

        else:
            with st.spinner("AI 비서가 리포트를 갱신 중..."):

                payload = {
                    "meeting_id": meeting_id,
                    "document_type": doc_key,
                    "current_text": origin_text,
                    "prompt": edit_prompt,
                }

                try:
                    res = requests.post(
                        f"{API_BASE_URL}/meetings/workflow/hitl-edit",
                        json=payload,
                        timeout=20,
                    )

                    res.raise_for_status()

                    after_text = normalize_to_string(res.json().get("revised_text", ""))

                    # 수정 결과 세션 저장
                    st.session_state[f"hitl_revised_{doc_key}"] = after_text

                except Exception as e:
                    st.error(f"요청 실패: {e}")

    # 수정 결과 표시
    revised_text = st.session_state.get(f"hitl_revised_{doc_key}")

    if revised_text:

        st.markdown("---")
        st.markdown("✅ **수정 후**")

        st.text_area("AI 수정 결과", value=revised_text, height=150, disabled=True)

        st.success(
            "성공적으로 반영되었습니다! '닫기'를 누르면 메인 리포트가 갱신됩니다."
        )

    # 팝업 닫기
    if st.button("닫기", use_container_width=True):
        st.session_state.pop("hitl_open", None)
        st.rerun()


# ==========================================================
# 5. 메인 화면 렌더링
# ==========================================================
data = get_report_data()

if data and isinstance(data, dict) and "meta" in data:

    meeting_id = data.get("meeting_id", "latest")

    meta = data["meta"]
    summary = data.get("summary", {})
    actions = data.get("actions", [])
    insights = data.get("insights", {})

    action_text = format_actions(actions)

    # 페이지 제목
    st.markdown(
        '<div style="font-size:38px; font-weight:800; color:#0F172A;">📊 회의 분석 리포트 & 액션 보드</div>',
        unsafe_allow_html=True,
    )

    st.divider()

    # 회의 기본 정보 표시
    participants = data.get("joiner", [])

    if isinstance(participants, list):
        participants = ", ".join(participants)

    st.markdown(
        f"""
    <div style="background-color:#F1F5F9; border-left:8px solid #1D4ED8;
        border-radius:12px; padding:25px; margin:20px 0;">
        <div style="font-size:20px; color:#64748B; margin-bottom:15px; font-weight:800;">
        📋 회의 기본 정보
        </div>
        <div style="display:grid; grid-template-columns: 1fr 1fr 1fr; gap:30px; font-size:18px; font-weight:600;">
        <div><span style="color:#BE185D;">제목:</span> {meta['title']}</div>
        <div><span style="color:#BE185D;">참석자:</span> {participants}</div>
        <div><span style="color:#BE185D;">일시:</span> {datetime.now().strftime("%Y-%m-%d %H:%M")}</div>
        </div>
    </div>
    """,
        unsafe_allow_html=True,
    )

    # 회의 결과 카드 (요약 / 액션 / 리스크)
    st.subheader("📦 회의 결과 패키지")

    c1, c2, c3 = st.columns(3)

    summary_text = (
        st.session_state.get("hitl_revised_summary")
        or st.session_state.get("hitl_current_summary")
        or "\n".join(summary.get("done", []))
    )

    action_text = (
        st.session_state.get("hitl_revised_actions")
        or st.session_state.get("hitl_current_actions")
        or action_text
    )

    risk_text = (
        st.session_state.get("hitl_revised_risk_warning")
        or st.session_state.get("hitl_current_risk_warning")
        or insights.get("risk_warning", "")
    )

    # ----------------------------------------------------------
    # 카드 UI 렌더링
    # ----------------------------------------------------------
    with c1:
        render_pkg_card("DONE", "회의 요약", summary_text)
        if st.button("AI 수정 ➔", key="edit_summary"):
            st.session_state["hitl_open"] = "summary"

    with c2:
        render_pkg_card("WILL DO", "액션 아이템", action_text)
        if st.button("AI 수정 ➔", key="edit_action"):
            st.session_state["hitl_open"] = "actions"

    with c3:
        render_pkg_card("TBD", "주요 리스크", risk_text)
        if st.button("AI 수정 ➔", key="btn_risk"):
            st.session_state["hitl_open"] = "risk_warning"

    # ----------------------------------------------------------
    # HITL 수정 팝업 실행
    # ----------------------------------------------------------
    if "hitl_open" in st.session_state:

        section = st.session_state["hitl_open"]

        if section == "summary":
            summary_done = summary.get("done", [])

            summary_text = (
                "\n".join(summary_done)
                if isinstance(summary_done, list)
                else summary_done
            )

            hitl_document_editor("summary", "회의 요약", summary_text, meeting_id)

        elif section == "actions":
            formatted_actions = format_actions(actions)

            hitl_document_editor(
                "actions", "액션 아이템", formatted_actions, meeting_id
            )

        elif section == "risk_warning":
            hitl_document_editor(
                "risk_warning",
                "주요 리스크",
                insights.get("risk_warning", ""),
                meeting_id,
            )
