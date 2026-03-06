# ---------------------------------------------------------
# [백엔드 연동] AI 에이전트 협업 및 공식 문서 배포 워크플로우
# ---------------------------------------------------------
import streamlit as st
import requests
import time
from datetime import datetime
from components.sidebar import render_sidebar

API_BASE_URL = "http://localhost:8000/api/v1"

st.set_page_config(page_title="무한상사 거버넌스 - 액션 및 리포트", layout="wide", initial_sidebar_state="expanded")
render_sidebar()

# ---------------------------------------------------------
# 상태 관리 (세션 초기화)
# ---------------------------------------------------------
if "current_meeting" not in st.session_state:
    st.session_state.current_meeting = "Q4 마케팅 킥오프"
if "is_approved" not in st.session_state:
    st.session_state.is_approved = False
if "approved_time" not in st.session_state:
    st.session_state.approved_time = "-"
    
# AI가 생성한 3개의 패키지 초안 데이터 유지
if "doc_summary" not in st.session_state:
    st.session_state.doc_summary = "[회의 요약 보고서]\n\n1. 목적: 모던 UX 확보 및 20대 유저 어필\n2. 주요 결정: 예산 35% 증액 및 제스처 도입 보류\n3. 액션: 디자인팀 롤백 기획, 개발팀 스펙 업데이트"
if "doc_action" not in st.session_state:
    st.session_state.doc_action = "[공식 액션 계획]\n\n- 디자인팀: 2/28까지 롤백 디자인 전달\n- 마케팅팀: 3/5까지 소셜 미디어 송출 매체 예약 확정\n- IT개발본부: 3/5 기술 스펙 업데이트 완료"
if "doc_research" not in st.session_state:
    st.session_state.doc_research = "[외부 참고 리서치]\n\n- 경쟁사 A: 최근 3개월간 소셜 미디어 예산 40% 증액\n- 트렌드: 20대 타겟 UX는 제스처 기반 인터랙션 선호도 85%"

# 우측 타임라인 로그 초기화
if "workflow_logs" not in st.session_state:
    st.session_state.workflow_logs = [
        {"time": "09:20 KST", "type": "대기", "title": "경영진 최종 승인 요청 발송", "assignee": "System", "color": "#F59E0B"},
        {"time": "09:15 KST", "type": "생성", "title": "실행 패키지 초안 생성", "assignee": "System", "color": "#3B82F6"}
    ]

# ---------------------------------------------------------
# Custom Enterprise CSS (오리지널 디자인 완벽 복원)
# ---------------------------------------------------------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;600;700;900&display=swap');
    @import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@24,400,1,0');
    
    .stApp { background-color: #0B0F19; font-family: 'Noto Sans KR', sans-serif; color: #F8FAFC; }

    /* Top Section */
    .page-title { font-size: 30px; font-weight: 900; color: #FFFFFF; margin-bottom: 8px; letter-spacing: -0.5px; }
    .subtitle-text { font-size: 14px; color: #94A3B8; margin-bottom: 25px; font-weight: 400; }
    .section-title { font-size: 16px; font-weight: 700; color: #F8FAFC; margin-bottom: 15px; margin-top: 10px; border-bottom: 1px solid #334155; padding-bottom: 10px; }

    /* Package Cards (3 Columns) */
    .pkg-card { background-color: #1E293B; border: 1px solid #334155; border-radius: 8px; padding: 20px; height: 100%; display: flex; flex-direction: column; justify-content: space-between; transition: all 0.2s; }
    .pkg-card:hover { border-color: #475569; transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,0.2); }
    .pkg-badge { font-size: 11px; font-weight: 700; padding: 4px 8px; border-radius: 4px; display: inline-block; margin-bottom: 15px; }
    .badge-green { background-color: rgba(16, 185, 129, 0.1); color: #10B981; border: 1px solid rgba(16, 185, 129, 0.3); }
    .badge-yellow { background-color: rgba(245, 158, 11, 0.1); color: #F59E0B; border: 1px solid rgba(245, 158, 11, 0.3); }
    .pkg-title { font-size: 16px; font-weight: 700; color: #F8FAFC; margin-bottom: 8px; }
    .pkg-desc { font-size: 13px; color: #94A3B8; margin-bottom: 20px; line-height: 1.5; flex-grow: 1; }
    .pkg-meta { font-size: 12px; color: #64748B; display: flex; justify-content: space-between; align-items: center; border-top: 1px dashed #334155; padding-top: 15px; }
    
    /* Control Boxes */
    .ctrl-box { background-color: #1E293B; border: 1px solid #334155; border-radius: 8px; padding: 20px; margin-bottom: 25px; }
    .grid-container { display: grid; grid-template-columns: 1fr 1fr 1fr auto; align-items: center; gap: 20px; }
    .grid-item-label { font-size: 12px; color: #94A3B8; font-weight: 700; margin-bottom: 6px; }
    .grid-item-value { font-size: 14px; color: #F8FAFC; font-weight: 700; }
    
    /* Right Timeline Log */
    .timeline-container { padding-left: 10px; margin-top: 15px; }
    .timeline-item { position: relative; padding-left: 20px; padding-bottom: 20px; border-left: 2px solid #334155; }
    .timeline-item:last-child { border-left: 2px solid transparent; }
    .timeline-dot { position: absolute; left: -6px; top: 0; width: 10px; height: 10px; border-radius: 50%; }
    .log-meta { font-size: 11px; font-weight: 700; margin-bottom: 4px; }
    .log-title { font-size: 14px; color: #F8FAFC; font-weight: 700; margin-bottom: 4px; }
    .log-assignee { font-size: 12px; color: #94A3B8; }

    /* Accuracy Shield Box */
    .shield-box { background-color: rgba(59, 130, 246, 0.05); border: 1px solid rgba(59, 130, 246, 0.2); border-radius: 8px; padding: 15px; display: flex; align-items: center; gap: 15px; margin-top: 30px; }
    .shield-icon { color: #3B82F6; font-size: 24px !important; }

    /* Streamlit Overrides */
    div[data-testid="stVerticalBlockBorderWrapper"] { background-color: #1E293B !important; border: 1px solid #334155 !important; border-radius: 8px !important; padding: 10px 20px !important; margin-bottom: 20px !important; }
    .stButton > button { font-weight: 700 !important; border-radius: 6px !important; transition: all 0.3s ease; }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# HITL 팝업 다이얼로그 (AI 에이전트와 문서 협업)
# ---------------------------------------------------------
# [수정됨] 최신 정식 문법인 @st.dialog 로 변경!
@st.dialog("🤖 AI 에이전트와 문서 협업 (HITL)")
def hitl_document_editor(doc_key, doc_title):
    st.markdown(f"**{doc_title} 편집 및 검토**")
    
    # 현재 문서 상태 (Read-only 처럼 보이지만 AI를 통해 수정)
    st.text_area("현재 문서 내용", value=st.session_state[doc_key], height=250, disabled=True)
    
    # AI 채팅 지시창
    prompt = st.chat_input("AI에게 수정 지시 (예: 분량을 절반으로 줄여줘)")
    if prompt:
        with st.spinner("AI가 지시사항을 반영하여 문서를 재작성 중입니다..."):
            try:
                # 백엔드 API 호출
                payload = {"document_type": doc_key, "current_text": st.session_state[doc_key], "prompt": prompt}
                res = requests.post(f"{API_BASE_URL}/workflow/hitl-edit", json=payload)
                res.raise_for_status()
                data = res.json()
                
                # 데이터 업데이트
                st.session_state[doc_key] = data["updated_text"]
                now = datetime.now().strftime("%H:%M KST")
                st.session_state.workflow_logs.insert(0, {
                    "time": now, "type": "수정", "title": f"'{doc_title}' AI 협업 수정 완료", "assignee": "Director Morgan", "color": "#10B981"
                })
                st.success(f"✅ 반영 완료: {data.get('agent_reply', '')}")
                time.sleep(1)
                st.rerun() # 팝업 닫고 새로고침
            except Exception as e:
                st.error(f"통신 에러가 발생했습니다: {e}")

# ---------------------------------------------------------
# Main Content Area
# ---------------------------------------------------------
st.markdown('<div class="page-title">회의 실행 및 공식 배포 관리</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle-text">공식 의사결정 및 액션 항목 배포 통제 시스템</div>', unsafe_allow_html=True)

# 상단 셀렉터 바
with st.container(border=True):
    col_sel, col_sync = st.columns([8, 2])
    with col_sel:
        st.selectbox("진행할 회의 컨텍스트 선택", ["Q4 마케팅 킥오프", "주간 제품 전략 회의"], label_visibility="collapsed")
    with col_sync:
        st.markdown('<div style="text-align:right; font-size:12px; color:#94A3B8; margin-top:10px;">마지막 동기화: Today, 09:00 KST</div>', unsafe_allow_html=True)

col_left, col_right = st.columns([7, 3], gap="large")

with col_left:
    # 1️⃣ 회의 실행 패키지 구성 (3개의 카드)
    st.markdown('<div class="section-title">회의 실행 패키지 구성</div>', unsafe_allow_html=True)
    
    pkg_col1, pkg_col2, pkg_col3 = st.columns(3)
    
    # 카드 1: 회의 요약 보고서
    with pkg_col1:
        st.markdown("""
        <div class="pkg-card">
            <div>
                <span class="pkg-badge badge-green">검토 완료</span>
                <div class="pkg-title">회의 요약 보고서</div>
                <div class="pkg-desc">마케팅 예산안 및 캠페인 타임라인 요약.</div>
            </div>
            <div class="pkg-meta"><span>1.8 MB • PDF</span></div>
        </div>
        """, unsafe_allow_html=True)
        # 카드 밑에 붙어있는 버튼 (팝업 호출)
        if st.button("상세 검토 ➔", key="btn1", use_container_width=True):
            hitl_document_editor("doc_summary", "회의 요약 보고서")
            
    # 카드 2: 공식 액션 계획
    with pkg_col2:
        st.markdown("""
        <div class="pkg-card">
            <div>
                <span class="pkg-badge badge-yellow">승인 대기</span>
                <div class="pkg-title">공식 액션 계획</div>
                <div class="pkg-desc">매체 송출 예약 및 디자인 에셋 전달 일정.</div>
            </div>
            <div class="pkg-meta"><span>Pending Review</span></div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("상세 검토 ➔", key="btn2", use_container_width=True):
            hitl_document_editor("doc_action", "공식 액션 계획")

    # 카드 3: 외부 참고 리서치 보고서
    with pkg_col3:
        st.markdown("""
        <div class="pkg-card">
            <div>
                <span class="pkg-badge badge-green">검토 완료</span>
                <div class="pkg-title">외부 참고 리서치 보고서</div>
                <div class="pkg-desc">Q4 소셜 미디어 광고 단가 트렌드 분석.</div>
            </div>
            <div class="pkg-meta"><span>Web Search & Context</span></div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("상세 검토 ➔", key="btn3", use_container_width=True):
            hitl_document_editor("doc_research", "외부 참고 리서치 보고서")

    # 2️⃣ 배포 승인 통제 박스
    st.markdown('<div class="section-title" style="margin-top: 30px;">배포 승인 통제</div>', unsafe_allow_html=True)
    
    status_text = "승인 완료" if st.session_state.is_approved else "승인 대기"
    status_badge = "badge-green" if st.session_state.is_approved else "badge-yellow"
    
    st.markdown(f"""
    <div class="ctrl-box">
        <div class="grid-container">
            <div>
                <div class="grid-item-label">배포 승인자</div>
                <div class="grid-item-value" style="color: #F59E0B;">David Chen (CMO)</div>
            </div>
            <div>
                <div class="grid-item-label">승인 상태</div>
                <span class="pkg-badge {status_badge}" style="margin:0; font-size:12px;">{status_text}</span>
            </div>
            <div>
                <div class="grid-item-label">결재 일시</div>
                <div class="grid-item-value" style="font-weight: 400; color: #CBD5E1;">{st.session_state.approved_time}</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # HTML 그리드 위에 겹치지 않게 버튼을 따로 빼서 우측 정렬합니다.
    col_blank, col_btn = st.columns([7, 3])
    with col_btn:
        if not st.session_state.is_approved:
            if st.button("결재권자 승인 처리", type="primary", use_container_width=True):
                with st.spinner("승인 중..."):
                    try:
                        requests.post(f"{API_BASE_URL}/workflow/approve", json={"meeting_id": st.session_state.current_meeting, "approver": "David Chen"})
                        st.session_state.is_approved = True
                        now = datetime.now().strftime("%H:%M KST")
                        st.session_state.approved_time = now
                        st.session_state.workflow_logs.insert(0, {"time": now, "type": "승인", "title": "배포 최종 승인 완료", "assignee": "David Chen", "color": "#10B981"})
                        st.rerun()
                    except Exception as e:
                        st.error("API 연동 에러")
        else:
            st.button("승인 이력 조회", disabled=True, use_container_width=True)

    # 3️⃣ 공식 배포 관리
    st.markdown('<div class="section-title" style="margin-top: 20px;">공식 배포 관리</div>', unsafe_allow_html=True)
    with st.container(border=True):
        st.markdown('<div style="font-size: 13px; color: #94A3B8; margin-bottom: 10px; font-weight: 700;">수신 대상 부서 지정</div>', unsafe_allow_html=True)
        target_depts = st.multiselect("수신 대상 부서 지정", ["마케팅 본부", "IT 개발본부", "디자인팀", "재무팀"], default=["마케팅 본부"], label_visibility="collapsed")
        
        btn_disabled = not st.session_state.is_approved or len(target_depts) == 0
        if st.button("🚀 선택 부서로 패키지 배포 실행", disabled=btn_disabled, type="primary"):
            with st.spinner("사내 메일망을 통해 공식 패키지를 배포 중입니다..."):
                try:
                    res = requests.post(f"{API_BASE_URL}/workflow/distribute", json={"meeting_id": st.session_state.current_meeting, "target_departments": target_depts})
                    data = res.json()
                    st.session_state.workflow_logs.insert(0, data["new_log"])
                    st.success("✅ 배포가 성공적으로 완료되었습니다!")
                    time.sleep(1.5)
                    st.rerun()
                except:
                    st.error("배포 실패")

with col_right:
    # 4️⃣ 우측 실행 및 배포 로그 (타임라인)
    st.markdown('<div class="section-title">실행 및 배포 로그</div>', unsafe_allow_html=True)
    
    st.markdown('<div class="timeline-container">', unsafe_allow_html=True)
    for log in st.session_state.workflow_logs:
        # 🛡️ [핵심 방어 코드] 꺼내기 전에 미리 .get()으로 안전하게 변수에 담아둡니다!
        color = log.get("color", "#3B82F6")
        l_type = log.get("type", "시스템")
        l_time = log.get("time", "-")
        l_title = log.get("title", "내역 없음")
        
        # 데이터에 'assignee'가 없으면 에러를 내는 대신 "System"이라는 기본값을 넣습니다.
        l_assignee = log.get("assignee", "System") 
        
        st.markdown(f"""
        <div class="timeline-item">
            <div class="timeline-dot" style="background-color: {color};"></div>
            <div class="log-meta" style="color: {color};">{l_type} • {l_time}</div>
            <div class="log-title">{l_title}</div>
            <div class="log-assignee">담당자: {l_assignee}</div>
        </div>
        """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # 5️⃣ AI 분석 신뢰도 쉴드 뱃지
    st.markdown("""
    <div class="shield-box">
        <span class="material-symbols-outlined shield-icon">shield_person</span>
        <div>
            <div style="font-size: 11px; color: #94A3B8; font-weight: 700; margin-bottom: 4px;">AI 분석 신뢰도</div>
            <div style="font-size: 14px; color: #60A5FA; font-weight: 900;">94% High Accuracy</div>
        </div>
    </div>
    """, unsafe_allow_html=True)