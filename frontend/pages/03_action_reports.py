# ==========================================================
# AI 분석 리포트 시각화 및 액션 플랜 관리 센터
# 백엔드 분석 결과 출력 / HITL 문서 수정 / 워크플로우 로그 표시
# ==========================================================
import sys
import os
import json
import streamlit as st
import requests
import pandas as pd
from datetime import datetime
from components.sidebar import render_sidebar

# 1. 경로 설정 (반드시 최상단)
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if FRONTEND_DIR not in sys.path:
    sys.path.append(FRONTEND_DIR)


# 3. Streamlit 페이지 설정
st.set_page_config(
    page_title="무한상사 거버넌스 - 액션 및 리포트",
    layout="wide",
    initial_sidebar_state="expanded",
)

render_sidebar()

# API 설정
API_BASE_URL = "http://localhost:8000/api/v1"


# ==========================================================
# Backend 통신 함수 (최신 API 규격 반영)
# ==========================================================
def get_report_data():
    try:
        # 백엔드: @router.get("/details/{meeting_id}")
        res = requests.get(f"{API_BASE_URL}/meetings/details/latest", timeout=10)
        res.raise_for_status()
        return res.json()  # MeetingReportResponse 객체 반환
    except Exception as e:
        st.error(f"데이터 로드 실패: {e}")
        return None


# 세션 상태 초기화
if "api_data" not in st.session_state:
    st.session_state.api_data = get_report_data()

# ==========================================================
# UI 레이아웃 시작
# ==========================================================
st.markdown(
    '<div style="font-size:38px; font-weight:800; color:#0F172A;">📊 회의 실행 센터: Action Hub</div>',
    unsafe_allow_html=True,
)

# 새로고침 버튼
if st.button("🔄 최신 결과 불러오기", use_container_width=True):
    st.session_state.api_data = get_report_data()
    st.rerun()

st.divider()

if not st.session_state.api_data:
    st.warning(
        "📡 분석된 회의 데이터가 없습니다. 페이지 1에서 분석을 먼저 완료해주세요."
    )
else:
    # 백엔드 데이터 구조: { meta, joiner, summary, actions, insights }
    data = st.session_state.api_data

    # 상단 정보 바
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

    col_left, col_right = st.columns([7, 3], gap="large")

    with col_left:
        st.subheader("📦 회의 결과 패키지")
        c1, c2, c3 = st.columns(3)

        # 1. DONE (Summary)
        with c1:
            summary_text = data["summary"]["display_text"]
            st.info(f"**[회의 요약]**\n\n{summary_text[:100]}...")
            if st.button("전문 검토 ➔", key="btn_done"):
                # HITL 호출 로직...
                pass

        # 2. WILL DO (Actions)
        with c2:
            action_count = len(data["actions"])
            st.success(
                f"**[실행 계획]**\n\n총 {action_count}건의 과제가 도출되었습니다."
            )
            if st.button("액션 수정 ➔", key="btn_action"):
                pass

        # 3. TBD (Insights)
        with c3:
            risk_text = data["insights"]["risk_warning"]
            st.warning(f"**[리스크 인사이트]**\n\n{risk_text}")
            if st.button("리스크 수정 ➔", key="btn_risk"):
                pass

        # 상세 액션플랜 테이블 (백엔드에서 대문자 Who, What, When으로 정규화해서 보내줌)
        st.write("### 📋 상세 액션플랜")
        if data["actions"]:
            st.table(pd.DataFrame(data["actions"]))

    with col_right:
        st.subheader("📊 실시간 지표")
        st.metric(label="핵심 KPI", value=data["insights"]["kpi"])

        st.divider()
        st.subheader("📜 시스템 로그")
        st.caption("AI 분석 엔진 정상 작동 중")
