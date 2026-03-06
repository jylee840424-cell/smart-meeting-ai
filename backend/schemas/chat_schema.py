from pydantic import BaseModel


# 입력 스키마 유지!
class ChatRequest(BaseModel):
    meeting_id: str
    mode: str = "검증 모드"  # "검증 모드" 또는 "자문 모드"
    prompt: str       # 프론트엔드에서 넘어온 사용자 질문
    include_past_db: bool = False


class UploadRequest(BaseModel):
    meeting_title: str
    department: str
    video_url: str