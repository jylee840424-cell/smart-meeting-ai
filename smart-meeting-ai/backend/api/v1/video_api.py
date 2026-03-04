from fastapi import APIRouter, HTTPException, BackgroundTasks
import uuid
from schemas.chat_schema import UploadRequest
# 방금 만든 작업 반장(Service)을 불러옵니다!
from services.video_service import run_video_analysis_pipeline

router = APIRouter(prefix="/video", tags=["Video Analysis"])

# 임시 메모리 저장소 (서비스 로직과 상태를 공유함)
VIDEO_DB = {}



@router.post("/upload")
async def start_video_analysis(request: UploadRequest, background_tasks: BackgroundTasks):
    """
    영상 분석 시작 엔드포인트
    무거운 분석 작업은 백그라운드(BackgroundTasks)로 넘기고, 프론트엔드에는 즉시 응답합니다.
    """
    meeting_id = f"M-{uuid.uuid4().hex[:8]}"
    
    # 1. 초기 상태 세팅 (1단계)
    VIDEO_DB[meeting_id] = {
        "status": "processing", 
        "current_step": 1, 
        "percent": 5, 
        "time_left": "분석 준비 중...", 
        "msg": "파이프라인 환경을 설정하고 있습니다."
    }
    
    # 2. [핵심] 백그라운드 태스크 실행 지시!
    # API는 여기서 바로 끝나지만, 서버 뒷단에서는 run_video_analysis_pipeline이 묵묵히 돌아갑니다.
    background_tasks.add_task(run_video_analysis_pipeline, meeting_id, request.video_url, VIDEO_DB)
    
    return {
        "meeting_id": meeting_id,
        "status": "processing",
        "message": f"'{request.meeting_title}' 영상 분석 파이프라인이 백그라운드에서 가동되었습니다."
    }

@router.get("/status/{meeting_id}")
async def get_analysis_status(meeting_id: str):
    """
    분석 상태 조회 엔드포인트
    프론트엔드가 1.5초마다 이 주소를 찔러서 현재 VIDEO_DB 상태를 가져갑니다.
    """
    if meeting_id not in VIDEO_DB:
        raise HTTPException(status_code=404, detail="회의 기록을 찾을 수 없습니다.")

    # 서비스 로직이 실시간으로 업데이트하고 있는 상태를 그대로 프론트엔드에 전달!
    return VIDEO_DB[meeting_id]