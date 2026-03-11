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

# ----------------------------------------------------------
# 2. Streamlit 페이지 설정 및 사이드바 렌더링
# ----------------------------------------------------------
st.set_page_config(
    page_title="무한상사 거버넌스 - 액션 및 리포트",
    layout="wide",
    initial_sidebar_state="expanded",
)

render_sidebar()

API_BASE_URL = "http://localhost:8000/api/v1"


# ----------------------------------------------------------
# 3. 데이터 로드 함수
# ----------------------------------------------------------
def get_report_data():
    """백엔드로부터 회의 리포트 데이터를 가져옵니다."""
    try:
        res = requests.get(f"{API_BASE_URL}/meetings/details/latest", timeout=30)
        res.raise_for_status()
        return res.json()
    except Exception as e:
        st.error(f"데이터 로드 실패: {e}")
        return None


# ----------------------------------------------------------
# 4. HITL AI 수정 다이얼로그
# ----------------------------------------------------------
@st.dialog("🤖 AI 에이전트와 문서 협업 (HITL)")
def hitl_document_editor(doc_key, doc_title, current_val, meeting_id):

    st.markdown(f"**{doc_title} 실시간 수정 제안**")

    # 데이터 타입에 따른 텍스트 변환
    if isinstance(current_val, list):

        formatted_items = []

        for item in current_val:

            if isinstance(item, dict):
                val_str = ", ".join([f"{k}: {v}" for k, v in item.items()])
                formatted_items.append(f"- {val_str}")

            else:
                formatted_items.append(str(item))

        display_text = "\n".join(formatted_items)

    else:
        display_text = str(current_val)

    # 수정 전 원본
    st.text_area("현재 문서 내용", value=display_text, height=250, disabled=True)

    prompt = st.chat_input("AI에게 수정 지시 (예: 더 간결하게 요약해줘)")

    if prompt:

        with st.spinner("AI가 리포트를 갱신 중..."):

            try:

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

                    st.success("수정 내용이 반영되었습니다!")

                else:
                    st.error(f"서버 오류: {res.status_code}")

            except Exception as e:
                st.error(f"통신 오류 발생: {e}")


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
        <div style="font-size:15px; color:#64748B; margin-bottom:15px; font-weight:800;">📋 회의 기본 정보</div>
        <div style="display:grid; grid-template-columns: 2fr 1fr 1fr; gap:20px; font-size:16px; font-weight:600;">
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

        preview = (
            summary_text[:100] + "..." if len(summary_text) > 100 else summary_text
        )

        st.info(f"**[회의 요약]**\n\n{preview}")

        if st.button("전문 검토 ➔"):
            st.session_state.hitl_open = "summary"
            st.rerun()

    # 액션 플랜
    with c2:

        action_count = len(actions)

        st.success(f"**[실행 계획]**\n\n총 {action_count}건의 과제가 도출되었습니다.")

        if st.button("액션 수정 ➔"):
            st.session_state.hitl_open = "action"
            st.rerun()

    # 리스크
    with c3:

        risk_text = insights.get("risk_warning", "-")

        st.warning(f"**[리스크 인사이트]**\n\n{risk_text}")

        if st.button("리스크 수정 ➔"):
            st.session_state.hitl_open = "risk"
            st.rerun()

    # ------------------------------------------------------
    # 인물별 업무
    # ------------------------------------------------------
    st.subheader("👥 인물별 업무 분담")

    if actions:

        df_actions = pd.DataFrame(actions)

        df_actions = df_actions.rename(
            columns={
                "Who": "담당자 (Who)",
                "What": "업무 내용 (What)",
                "When": "기한 (When)",
            }
        )

        st.table(df_actions)

    else:
        st.info("도출된 상세 업무 리스트가 없습니다.")

    # ------------------------------------------------------
    # HITL 다이얼로그 실행
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

        elif section == "risk":
            hitl_document_editor(
                "insights",
                "리스크 인사이트",
                insights.get("risk_warning", ""),
                meeting_id,
            )

        elif section == "risk":

            hitl_document_editor(
                "insights",
                "리스크 인사이트",
                insights.get("risk_warning", ""),
                meeting_id,
            )
