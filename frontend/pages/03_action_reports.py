# ==========================================================
# AI 분석 리포트 시각화 및 액션 플랜 관리 센터
# ==========================================================
import sys
import os
import json
import streamlit as st
import requests
import pandas as pd
from datetime import datetime
from components.sidebar import render_sidebar

# ----------------------------------------------------------
# 1. 경로 설정 : 절대 경로를 사용하여 모듈 참조 오류 방지
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
# 2. UI 스타일 (CSS) 적용
# ----------------------------------------------------------
st.markdown(
    """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Pretendard:wght@400;700&display=swap');
        
        /* 앱 전체 배경색 및 폰트 설정 */
        .stApp { background-color: #FFFFFF; font-family: 'Pretendard', sans-serif; color: #0F172A; }
        
        /* 강조 컬러 정의 */
        .blue-point { color: #1D4ED8; font-weight: 800; }
        .pink-point { color: #BE185D; font-weight: 800; }

        /* 분석 결과 카드 컴포넌트 스타일 */
        .pkg-card {
            background-color: #F8FAFC; 
            border: 2px solid #E2E8F0; 
            border-radius: 16px; 
            padding: 25px; 
            min-height: 400px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
            margin-bottom: 20px;
        }
        .card-status { font-size: 18px; color: #1D4ED8; font-weight: 800; margin-bottom: 10px; }
        .card-label { font-size: 20px; font-weight: 700; color: #0F172A; margin-bottom: 15px; }
        .card-content { font-size: 18px !important; color: #475569 !important; line-height: 1.6; white-space: pre-wrap; }
    </style>
    """,
    unsafe_allow_html=True,
)


# ----------------------------------------------------------
# 3. 데이터 로드 및 UI 렌더링을 위한 헬퍼 함수
# ----------------------------------------------------------
def get_report_data():
    """백엔드로부터 최신 회의 데이터를 가져옵니다."""
    try:
        res = requests.get(f"{API_BASE_URL}/meetings/details/latest", timeout=5)
        res.raise_for_status()
        return res.json()
    except Exception as e:
        st.error(f"데이터 로드 실패: {e}")
        return None


def render_pkg_card(status, title, content):
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
# 4. HITL AI 수정 다이얼로그
# ----------------------------------------------------------
@st.dialog("🤖 AI 문서 수정 에디터", width="large")
def hitl_document_editor(doc_key, doc_title, current_val, meeting_id):
    st.markdown(f"**{doc_title}✍️ 실시간 수정**")

    # 데이터 타입에 따른 텍스트 변환
    if isinstance(current_val, list):
        formatted_items = []
        for item in current_val:
            if isinstance(item, dict):
                # 액션플랜 등 딕셔너리 리스트인 경우 "키: 값" 형태로 가공
                val_str = ", ".join([f"{k}: {v}" for k, v in item.items()])
                formatted_items.append(f"- {val_str}")
            else:
                formatted_items.append(str(item))
        display_text = "\n".join(formatted_items)
    else:
        display_text = str(current_val)

    st.text_area("현재 문서 내용", value=display_text, height=250, disabled=True)
    prompt = st.chat_input("AI에게 수정 지시 (예: 더 간결하게 요약해줘)")
    if prompt:
        with st.spinner("AI가 리포트를 갱신 중..."):
            try:
                # 백엔드 HITL 편집 API 호출
                payload = {
                    "meeting_id": meeting_id,
                    "document_type": doc_key,
                    "current_text": display_text,
                    "prompt": prompt,
                }

                res = requests.post(
                    f"{API_BASE_URL}/meetings/workflow/hitl-edit", json=payload
                )

                if res.status_code == 200:
                    response_data = res.json()
                    before_text = display_text
                    after_text = response_data.get("revised_text", "")

                    st.markdown("### ✏️ 수정 전")
                    st.text_area(
                        "기존 내용", value=before_text, height=200, disabled=True
                    )
                    st.markdown("### ✅ 수정 후")
                    st.text_area(
                        "AI가 수정한 내용", value=after_text, height=200, disabled=True
                    )
                    st.success("수정 요청이 반영되었습니다!")
                else:
                    st.error(f"서버 응답 오류: {res.status_code}")
            except Exception as e:
                st.error(f"통신 에러 발생: {e}")


# ==========================================================
# 실행 영역
# ==========================================================
data = get_report_data()

if data and isinstance(data, dict) and "meta" in data:
    try:
        meeting_id = data["meta"].get("meeting_id", "latest")
        meta = data["meta"]
        summary = data.get("summary", {})
        actions = data.get("actions", [])
        insights = data.get("insights", {})
    except Exception as e:
        st.error(f"데이터 파싱 오류: {e}")
        st.stop()

    # ------------------------------------------------------
    # 화면 제목
    # ------------------------------------------------------
    st.markdown(
        '<div style="font-size:38px; font-weight:800; color:#0F172A;">📊 회의 분석 리포트 & 액션 보드</div>',
        unsafe_allow_html=True,
    )

    st.divider()

    # ------------------------------------------------------
    # 회의 기본 정보
    # ------------------------------------------------------
    participants = data.get("joiner", "-")
    if isinstance(participants, list):
        participants = ", ".join(participants)
    st.markdown(
        f"""
    <div style="background-color:#F1F5F9; border-left:8px solid #1D4ED8; border-radius:12px; padding:25px; margin:20px 0;">
        <div style="font-size:20px; color:#64748B; margin-bottom:15px; font-weight:800;">📋 회의 기본 정보</div>
        <div style="display:grid; grid-template-columns: 2fr 1fr 1fr; gap:20px; font-size:18px; font-weight:600;">
            <div><span style="color:#BE185D;">제목:</span> {data['meta']['title']}</div>
            <div><span style="color:#BE185D;">참석자:</span> {data['joiner']}</div>
            <div><span style="color:#BE185D;">일시:</span> {datetime.now().strftime("%Y-%m-%d %H:%M")}</div>
        </div>
    </div>
    """,
        unsafe_allow_html=True,
    )

    # ------------------------------------------------------
    # 회의 결과 카드
    # ------------------------------------------------------
    st.subheader("📦 회의 결과 패키지")
    c1, c2, c3 = st.columns(3)

    # 회의 요약
    with c1:
        summary_text = summary.get("display_text", "")
        render_pkg_card("DONE", "회의 요약", summary_text)
        preview = (
            summary_text[:300] + "..." if len(summary_text) > 300 else summary_text
        )
        if st.button("AI 수정 ➔", key="edit_summary"):
            st.session_state.hitl_open = "summary"
            st.rerun()

    # 액션 플랜
    with c2:
        if actions:
            formatted_items = []
            for item in actions:
                if isinstance(item, dict):
                    who = item.get("Who", "담당자 미정")
                    what = item.get("What", "")
                    when = item.get("When", "")
                    # 문장 형태로 변환
                    sentence = f"{who} : {when}까지 {what}"
                    formatted_items.append(f"- {sentence}")
                else:
                    formatted_items.append(str(item))
            action_text = "\n".join(formatted_items)
        else:
            action_text = "도출된 상세 업무 리스트가 없습니다."
        render_pkg_card("WILL DO", "업무 분담", action_text)
        preview = action_text[:300] + "..." if len(action_text) > 300 else action_text
        if st.button("AI 수정 ➔", key="edit_action"):
            st.session_state.hitl_open = "actions"
            st.rerun()

    # 리스크 분석
    with c3:
        risk_text = insights.get("risk_warning", "")
        render_pkg_card("TBD", "리스크 분석", risk_text)
        preview = risk_text[:300] + "..." if len(risk_text) > 300 else risk_text
        if st.button("AI 수정 ➔", key="btn_risk"):
            st.session_state.hitl_open = "risk"
            st.rerun()

    # ------------------------------------------------------
    # HITL 수정 에디터 노출
    # ------------------------------------------------------
    if "hitl_open" in st.session_state:
        section = st.session_state.hitl_open
        if section == "summary":
            hitl_document_editor(
                "done",
                "회의 요약",
                summary.get("display_text", ""),
                meeting_id,
            )

        elif section == "actions":
            hitl_document_editor("actions", "업무 분담", actions, meeting_id)

        elif section == "risk":
            hitl_document_editor(
                "insights",
                "리스크 분석",
                insights.get("risk_warning", ""),
                meeting_id,
            )
