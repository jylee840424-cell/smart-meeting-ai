from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.video_service import VideoAnalysisService
from services.database_service import DatabaseService # DB 서비스 추가
import logging
import json
import uuid

logger = logging.getLogger(__name__)
router = APIRouter()
video_service = VideoAnalysisService()
db_service = DatabaseService() # DB 서비스 인스턴스화

# 메모리 DB (현재 세션용)
VIDEO_DB = {}

class VideoRequest(BaseModel):
    video_url: str

@router.post("/upload")
async def upload_video(request: VideoRequest):
    try:
        # 서비스 내의 ID 생성 로직 사용 (기존에 쓰시던 방식이 있다면 그것을 따릅니다)
        meeting_id = f"mtg_{uuid.uuid4().hex[:8]}"
        
        VIDEO_DB[meeting_id] = {"status": "processing", "percent": 0}
        
        # 분석 시작 (백그라운드에서 실행되도록 await)
        # 만약 분석이 너무 오래 걸려 타임아웃 난다면 asyncio.create_task를 고려해야 합니다.
        result = await video_service.run_pipeline(meeting_id, request.video_url, VIDEO_DB)
        return result
    except Exception as e:
        logger.error(f"🔥 업로드 에러: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/video/status/{meeting_id}")
async def get_video_status(meeting_id: str):
    """
    프론트엔드가 'msg'가 없다고 징징대지 못하게 
    무조건 기본값을 채워서 보내주는 안전 창구
    """
    # 1. VIDEO_DB에서 데이터를 가져옵니다.
    status_data = VIDEO_DB.get(meeting_id, {})

    # 2. [필살기] .get()의 두 번째 인자를 활용해서 'msg'가 없으면 기본 문구를 보냅니다.
    # 이렇게 하면 KeyError: 'msg'는 물리적으로 발생할 수 없습니다.
    return {
        "meeting_id": meeting_id,
        "status": status_data.get("status", "processing"),
        "percent": status_data.get("percent", 0),
        "msg": status_data.get("msg", "데이터를 처리 중입니다..."), # <-- 여기가 포인트!
        "transcript": status_data.get("transcript", []),
        "report": status_data.get("report", {"summary": ""}),
        "steps_completed": status_data.get("steps_completed", 0),
        "total_steps": 5
    }