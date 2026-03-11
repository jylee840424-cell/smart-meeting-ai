import streamlit as st
import requests
import time
from components.sidebar import render_sidebar

# 페이지 설정
st.set_page_config(page_title="무한상사 - 영상 분석", layout="wide")
render_sidebar()

st.title("📹 회의 영상 분석 시스템")
st.caption("AI 5단계 파이프라인을 통해 실시간으로 회의록을 생성합니다.")

# 입력 폼
with st.container(border=True):
    col1, col2 = st.columns([2, 1])
    with col1:
        video_url = st.text_input("유튜브 링크 또는 영상 URL", placeholder="https://www.youtube.com/watch?v=...")
    with col2:
        meeting_title = st.text_input("회의 제목", placeholder="2026 전략 기획 회의")
    
    analyze_button = st.button("🚀 AI 분석 가동", use_container_width=True)

# 분석 프로세스 시각화 부분
if analyze_button and video_url:
    try:
        # 1. 백엔드에 분석 시작 요청
        res = requests.post("http://localhost:8000/api/v1/upload", 
                             json={"video_url": video_url, "meeting_title": meeting_title})
        meeting_id = res.json()["meeting_id"]
        
        st.divider()
        st.subheader(f"🆔 회의 ID: {meeting_id} 분석 현황")
        
        # 실시간 업데이트를 위한 자리 만들기
        status_msg = st.empty()
        progress_bar = st.progress(0)
        
        # 5단계 카드 레이아웃
        step_cols = st.columns(5)
        step_names = ["음성 추출", "화자 분리", "텍스트 분할", "벡터 저장", "요약 생성"]
        placeholders = [col.empty() for col in step_cols]

       # Polling 루프 (상태 확인)
        while True:
            response = requests.get(f"http://localhost:8000/api/v1/video/status/{meeting_id}")
            data = response.json()
            
            # 1. 진행 바 및 메시지 업데이트
            # data["percent"]가 없거나 문자열일 경우를 대비해 기본값 0 설정
            percent = data.get("percent", 0)
            progress_bar.progress(float(percent) / 100)
            status_msg.info(f"⚙️ **진행 상태:** {data.get('msg', '분석 중...')}")
            
            # 2. 각 단계별 체크마크 표시
            # [수정포인트] steps_completed가 숫자여도 에러 안 나게 리스트화 시킴
            completed_steps = data.get("steps_completed", [])
            if isinstance(completed_steps, int): # 만약 숫자(3)라면 [1, 2, 3]으로 변환
                completed_steps = [f"step0{j}" for j in range(1, completed_steps + 1)]
            
            current_step = data.get("current_step", 0)

            for i in range(5):
                step_num = i + 1
                step_key = f"step0{step_num}"
                
                # 체크 표시 로직
                if step_key in completed_steps:
                    placeholders[i].success(f"✅ {step_names[i]}")
                elif current_step == step_num:
                    placeholders[i].warning(f"⏳ {step_names[i]}")
                else:
                    placeholders[i].info(f"⚪ {step_names[i]}")
            
            # 3. 종료 조건 확인
            status = data.get("status", "processing")
            if status == "completed":
                st.balloons()
                st.success("✨ 모든 분석 단계가 완료되었습니다! 결과 페이지에서 확인하세요.")
                break
            elif status == "error":
                st.error(f"❌ 분석 실패: {data.get('msg', '알 수 없는 오류')}")
                break
            
            time.sleep(2)

    except Exception as e:
        st.error(f"연결 오류: {str(e)}")