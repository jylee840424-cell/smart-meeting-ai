import streamlit as st
import datetime
import requests
import time
from components.sidebar import render_sidebar

API_BASE_URL = "http://localhost:8000/api/v1"

st.set_page_config(page_title="무한상사 회의 거버넌스 시스템 - 회의 분석", layout="wide", initial_sidebar_state="expanded")
render_sidebar()

# ---------------------------------------------------------
# State Management
# ---------------------------------------------------------
if 'is_analyzing' not in st.session_state:
    st.session_state.is_analyzing = False
if "analysis_done" not in st.session_state:
    st.session_state.analysis_done = False
if "meeting_id" not in st.session_state:
    st.session_state.meeting_id = None
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "summary_data" not in st.session_state:
    st.session_state.summary_data = {}
if "transcript_data" not in st.session_state:
    st.session_state.transcript_data = []

# ---------------------------------------------------------
# Custom Enterprise CSS
# ---------------------------------------------------------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;700&display=swap');
    .stApp { background-color: #0B0F19; font-family: 'Noto Sans KR', sans-serif; color: #F8FAFC; }
    .page-title { font-size: 32px; font-weight: 700; color: #FFFFFF; margin-bottom: 5px; letter-spacing: -0.5px; }
    .page-subtitle { font-size: 15px; color: #94A3B8; margin-bottom: 20px; font-weight: 400; }
    .title-divider { border-bottom: 1px solid #334155; margin-bottom: 30px; }
    
    div[data-testid="stVerticalBlockBorderWrapper"] {
        background-color: #1E293B !important; border: 1px solid #334155 !important;
        border-radius: 8px !important; padding: 10px 10px !important; margin-bottom: 20px !important;
    }
    .card-title { font-size: 18px; font-weight: 700; color: #FFFFFF; margin-bottom: 20px; border-bottom: 1px solid #334155; padding-bottom: 10px; }
    
    .workflow-container { display: flex; justify-content: space-between; align-items: center; margin-top: 10px; margin-bottom: 10px; }
    .step-box { display: flex; flex-direction: column; align-items: center; flex: 1; position: relative; }
    .step-box:not(:last-child)::after { content: ''; position: absolute; top: 15px; right: -50%; width: 100%; height: 2px; background-color: #334155; z-index: 1; }
    .step-box.active:not(:last-child)::after { background-color: #2563EB; }
    .step-circle { width: 32px; height: 32px; border-radius: 50%; background-color: #334155; color: #94A3B8; display: flex; justify-content: center; align-items: center; font-size: 14px; font-weight: 700; z-index: 2; margin-bottom: 10px; }
    .step-box.completed .step-circle { background-color: #16A34A; color: #FFFFFF; }
    .step-box.processing .step-circle { background-color: #2563EB; color: #FFFFFF; box-shadow: 0 0 0 4px rgba(37, 99, 235, 0.2); }
    .step-label { font-size: 13px; color: #CBD5E1; font-weight: 500; margin-bottom: 5px; }
    
    .badge { padding: 4px 8px; border-radius: 4px; font-size: 11px; font-weight: 700; }
    .badge-pending { background-color: #334155; color: #94A3B8; }
    .badge-processing { background-color: rgba(37, 99, 235, 0.2); color: #60A5FA; border: 1px solid #2563EB; }
    .badge-completed { background-color: rgba(22, 163, 74, 0.2); color: #4ADE80; border: 1px solid #16A34A; }

    .log-item { display: flex; justify-content: space-between; padding: 12px 0; border-bottom: 1px dashed #334155; font-size: 14px; }
    .log-item:last-child { border-bottom: none; }
    .log-label { color: #94A3B8; }
    .log-value { color: #F8FAFC; font-weight: 500; }

    .stTextInput > label, .stSelectbox > label, .stDateInput > label { color: #CBD5E1 !important; font-weight: 600 !important; font-size: 13px !important; }
    .stButton > button { background-color: #2563EB !important; color: #FFFFFF !important; border: none !important; font-weight: 700 !important; border-radius: 6px !important; padding: 12px 24px !important; width: 100%; }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# Dynamic UI 렌더링 & 스트리밍 헬퍼 함수
# ---------------------------------------------------------
def get_workflow_html(current_step):
    steps = ["영상 등록", "음성 분석", "화자 분리", "구조화 요약 생성", "결정 검토 준비"]
    html_parts = ['<div class="workflow-container">']
    for i, label in enumerate(steps, 1):
        if i < current_step:
            box_cls, cir_txt, bdg_cls, bdg_txt = "completed active", "✓", "badge-completed", "완료"
        elif i == current_step:
            box_cls, cir_txt, bdg_cls, bdg_txt = "processing active", str(i), "badge-processing", "진행 중"
        else:
            box_cls, cir_txt, bdg_cls, bdg_txt = "", str(i), "badge-pending", "대기"
            
        raw_html = f'<div class="step-box {box_cls}"><div class="step-circle">{cir_txt}</div><div class="step-label">{label}</div><span class="badge {bdg_cls}">{bdg_txt}</span></div>'
        html_parts.append("".join([line.strip() for line in raw_html.splitlines()]))
    html_parts.append('</div>')
    return "".join(html_parts)

def get_log_panel_html(step, percent, time_left, msg, status):
    status_color = "#4ADE80" if status == "completed" else "#60A5FA"
    status_text = "분석 완료" if status == "completed" else "정상 처리 중..."
    raw_html = f"""
    <div class="log-item"><span class="log-label">현재 처리 단계</span><span class="log-value" style="color: #60A5FA;">{step}/5 {msg[:15]}...</span></div>
    <div class="log-item"><span class="log-label">예상 소요 시간</span><span class="log-value">{time_left}</span></div>
    <div class="log-item"><span class="log-label">진행률</span><span class="log-value">{percent}%</span></div>
    <div class="log-item"><span class="log-label">시스템 상태</span><span class="log-value" style="color: {status_color};">{status_text}</span></div>
    <div style="margin-top: 40px; padding-top: 20px; border-top: 1px solid #334155;">
        <p style="color: #94A3B8; font-size: 13px; font-weight: 700; margin-bottom: 15px;">분석 시스템 로그</p>
        <p style="color: #64748B; font-size: 13px;">> {msg}</p>
    </div>
    """
    return "".join([line.strip() for line in raw_html.splitlines()])

# [추가됨] 백엔드의 스트리밍 데이터를 받아오는 제너레이터 함수
def stream_expert_answer(meeting_id: str, query: str):
    url = f"{API_BASE_URL}/chat/ask"
    payload = {"meeting_id": meeting_id, "mode": "일반", "prompt": query}
    
    try:
        # stream=True 옵션을 통해 백엔드가 쏘는 조각들을 실시간으로 받습니다.
        with requests.post(url, json=payload, stream=True) as response:
            response.raise_for_status()
            for chunk in response.iter_content(chunk_size=None, decode_unicode=True):
                if chunk:
                    yield chunk
    except Exception as e:
        yield f"\n\n❌ 서버 통신 오류가 발생했습니다: {str(e)}"

# ---------------------------------------------------------
# Main Content
# ---------------------------------------------------------
st.markdown('<div class="page-title">회의 분석 관리</div>', unsafe_allow_html=True)
st.markdown('<div class="page-subtitle">공식 회의 영상 등록 및 AI 분석 단계</div>', unsafe_allow_html=True)
st.markdown('<div class="title-divider"></div>', unsafe_allow_html=True)

left_col, right_col = st.columns([6.5, 3.5], gap="large")

with left_col:
    # 1. 회의 영상 등록 폼
    with st.container(border=True):
        st.markdown('<div class="card-title">회의 영상 등록</div>', unsafe_allow_html=True)
        form_col1, form_col2 = st.columns(2)
        with form_col1:
            title = st.text_input("회의 제목", placeholder="예: 2026년 1분기 경영전략 회의")
            dept = st.selectbox("부서 선택", ["전략기획실", "영업1본부", "인사/컴플라이언스", "IT개발본부"])
        with form_col2:
            date = st.date_input("회의 날짜", datetime.date.today())
            url = st.text_input("영상 링크 (URL)", placeholder="https://youtube.com/watch?v=...")
        
        st.file_uploader("또는 로컬 영상/음성 파일 업로드 (MP4, MP3, WAV)", type=['mp4', 'mp3', 'wav'])
        
        if st.button("🚀 AI 분석 시작", disabled=st.session_state.is_analyzing or st.session_state.analysis_done):
            try:
                res = requests.post(f"{API_BASE_URL}/video/upload", json={"meeting_title": title, "department": dept, "video_url": url})
                res.raise_for_status()
                st.session_state.meeting_id = res.json()["meeting_id"]
                st.session_state.is_analyzing = True
                st.session_state.analysis_done = False
                st.session_state.summary_data = {}
                st.session_state.transcript_data = []
                st.session_state.chat_history = [] # 새 영상 등록시 챗 히스토리 초기화
                st.rerun() 
            except Exception as e:
                st.error(f"API 서버 통신 오류: {e}")

    # 2. 실시간 분석 진행 단계
    with st.container(border=True):
        st.markdown('<div class="card-title">분석 진행 단계</div>', unsafe_allow_html=True)
        workflow_placeholder = st.empty() 
        
        if not st.session_state.is_analyzing and not st.session_state.analysis_done:
            workflow_placeholder.markdown(get_workflow_html(1), unsafe_allow_html=True)
        elif st.session_state.analysis_done:
            workflow_placeholder.markdown(get_workflow_html(6), unsafe_allow_html=True)

    # 3. [핵심] AI 질의 응답 영역 (Real RAG + Streaming)
    with st.container(border=True):
        st.markdown('<div class="section-title" style="font-size: 18px; font-weight: 700; color: #FFFFFF; margin-bottom: 20px;">AI 회의 분석 질의</div>', unsafe_allow_html=True)
        
        # 이전 채팅 내역 출력
        for chat in st.session_state.chat_history:
            with st.chat_message(chat["role"]):
                st.markdown(chat["content"])

        is_disabled = not st.session_state.analysis_done
        prompt = st.chat_input("분석이 완료되면 활성화됩니다..." if is_disabled else "회의 내용에 대해 질문해 주세요.", disabled=is_disabled)

        if prompt:
            # 사용자 질문 UI에 즉시 추가
            st.session_state.chat_history.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)
                
            # AI 답변 스트리밍 수신 및 UI 렌더링
            with st.chat_message("assistant"):
                # st.write_stream은 제너레이터가 뱉는 글자를 타닥타닥 예쁘게 그려주고 최종 문자열을 반환합니다.
                stream_generator = stream_expert_answer(st.session_state.meeting_id, prompt)
                full_response = st.write_stream(stream_generator)
                
            # 최종 완성된 스트리밍 답변을 세션(히스토리)에 저장
            st.session_state.chat_history.append({"role": "assistant", "content": full_response})

with right_col:
    # 4. 우측 패널
    with st.container(border=True):
        
        if not st.session_state.is_analyzing and not st.session_state.analysis_done:
            st.markdown('<div class="card-title">분석 상태 로그</div>', unsafe_allow_html=True)
            st.markdown("""
            <div style="text-align: center; color: #64748B; margin-top: 150px; margin-bottom: 150px;">
                <div style="font-size: 40px; margin-bottom: 10px;">📋</div>
                <p style="font-size: 14px;">등록된 회의가 없습니다.<br>좌측에서 회의 영상을 등록해주세요.</p>
            </div>
            """, unsafe_allow_html=True)
            log_placeholder = st.empty()
            
        elif st.session_state.is_analyzing:
            st.markdown('<div class="card-title">분석 상태 로그</div>', unsafe_allow_html=True)
            log_placeholder = st.empty()
            
        elif st.session_state.analysis_done:
            st.markdown('<div class="card-title" style="color: #4ADE80;">✅ AI 분석 리포트</div>', unsafe_allow_html=True)
            
            summary_info = st.session_state.summary_data.get("summary", "요약 정보를 불러올 수 없습니다.")
            st.markdown(f"""
            <div style="background-color: #1E293B; padding: 20px; border-radius: 8px; border-left: 4px solid #60A5FA; margin-bottom: 20px;">
                <h4 style="margin-top: 0; color: #F8FAFC; font-size: 15px;">핵심 요약</h4>
                <p style="color: #CBD5E1; font-size: 14px; line-height: 1.6; margin-bottom: 0;">{summary_info}</p>
            </div>
            """, unsafe_allow_html=True)
            
            actions = st.session_state.summary_data.get("actions", [])
            if actions:
                st.markdown('<p style="font-size: 14px; font-weight: 700; color: #F8FAFC; margin-bottom: 10px;">📌 주요 액션 아이템</p>', unsafe_allow_html=True)
                for act in actions:
                    st.markdown(f'<div style="background-color: #0F172A; padding: 10px 15px; border-radius: 6px; margin-bottom: 8px; font-size: 13px; color: #94A3B8;">• {act}</div>', unsafe_allow_html=True)
            
            st.markdown("<hr style='border-color: #334155; margin: 25px 0;'>", unsafe_allow_html=True)
            
            with st.expander("📝 화자 분리 원본 스크립트 보기"):
                transcript = st.session_state.transcript_data
                if isinstance(transcript, list) and len(transcript) > 0:
                    for line in transcript:
                        if isinstance(line, dict):
                            speaker = line.get('speaker', 'Unknown')
                            time_str = line.get('time', '00:00')
                            text = line.get('text', '')
                            st.markdown(f"<span style='color:#60A5FA; font-size:12px;'>[{time_str}]</span> **{speaker}**<br><span style='color:#CBD5E1; font-size:14px;'>{text}</span><br><br>", unsafe_allow_html=True)
                        else:
                            st.write(line)
                elif isinstance(transcript, str):
                    st.write(transcript)
                else:
                    st.write("스크립트 데이터가 없습니다.")

# ---------------------------------------------------------
# 백엔드 실시간 Polling(폴링) 루프 
# ---------------------------------------------------------
if st.session_state.is_analyzing and st.session_state.meeting_id:
    while True:
        try:
            res = requests.get(f"{API_BASE_URL}/video/status/{st.session_state.meeting_id}")
            data = res.json()
            
            workflow_placeholder.markdown(get_workflow_html(data["current_step"]), unsafe_allow_html=True)
            log_placeholder.markdown(get_log_panel_html(data["current_step"], data.get("percent", 0), data.get("time_left", ""), data.get("msg", ""), data["status"]), unsafe_allow_html=True)
            
            if data["status"] == "completed":
                st.session_state.summary_data = data.get("summary", {})
                st.session_state.transcript_data = data.get("transcript", [])
                st.session_state.is_analyzing = False
                st.session_state.analysis_done = True
                
                time.sleep(1) 
                st.rerun() 
                break
            elif data["status"] == "error":
                st.session_state.is_analyzing = False
                st.error("분석 중 오류가 발생하여 중단되었습니다.")
                break
                
            time.sleep(1.5)
            
        except Exception as e:
            st.error(f"상태 조회 중 오류 발생: {e}")
            break