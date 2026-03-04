# frontend/services/api_service.py
import requests
import streamlit as st

API_BASE_URL = "http://localhost:8000/api/v1"
TIMEOUT_UPLOAD = 60  
TIMEOUT_STATUS = 10

def upload_meeting_video(title: str, dept: str, video_url: str):
    """[회의 영상 등록] URL을 기반으로 백엔드에 분석을 요청합니다."""
    url = f"{API_BASE_URL}/video/upload"
    payload = {
        "meeting_title": title, 
        "department": dept, 
        "video_url": video_url
    }
    try:
        response = requests.post(url, json=payload, timeout=TIMEOUT_UPLOAD)
        response.raise_for_status()
        return response.json() # {"meeting_id": "M-..."} 반환
    except Exception as e:
        raise Exception(f"서버 통신 중 오류가 발생했습니다: {e}")

def get_analysis_status(meeting_id: str):
    """[상태 폴링] 분석 진행 상태를 주기적으로 확인합니다."""
    url = f"{API_BASE_URL}/video/status/{meeting_id}"
    try:
        response = requests.get(url, timeout=TIMEOUT_STATUS)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        raise Exception(f"상태 조회 중 오류 발생: {e}")

@st.cache_data(ttl=5)
def get_completed_meeting_list():
    """[회의 목록 조회] 챗봇 화면에서 선택할 수 있는 분석 완료 회의 목록을 가져옵니다."""
    url = f"{API_BASE_URL}/chat/meetings"
    try:
        res = requests.get(url, timeout=TIMEOUT_STATUS)
        if res.status_code == 200:
            meetings = res.json()
            if meetings and len(meetings) > 0:
                return {m["display_name"]: m["id"] for m in meetings}
    except Exception as e:
        pass
    return {}

def stream_expert_answer(meeting_id: str, mode: str, query: str):
    """[스트리밍 챗봇] RAG 챗봇에 질문하고 타닥타닥 타이핑되는 텍스트를 제너레이터로 반환합니다."""
    url = f"{API_BASE_URL}/chat/ask"
    payload = {
        "meeting_id": meeting_id, 
        "mode": mode, 
        "prompt": query, 
        "include_past_db": False
    }
    try:
        # 핵심: stream=True 옵션으로 텍스트 조각을 수신
        with requests.post(url, json=payload, stream=True) as response:
            response.raise_for_status()
            for chunk in response.iter_content(chunk_size=None, decode_unicode=True):
                if chunk:
                    yield chunk
    except Exception as e:
        yield f"\n\n❌ 백엔드 통신 오류가 발생했습니다: {str(e)}"