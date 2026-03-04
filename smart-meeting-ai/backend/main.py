from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from api.v1 import video_api, chat_api, meeting_api # <-- *_api 추가!
from dotenv import load_dotenv
load_dotenv()


# 1. FastAPI 애플리케이션 초기화 (엔터프라이즈급 API 문서 메타데이터 설정)
app = FastAPI(
    title="무한상사 회의 거버넌스 시스템 API",
    description="Streamlit 프론트엔드와 통신하기 위한 하이브리드 Mock API 서버입니다.",
    version="1.0.0",
    docs_url="/docs", # Swagger UI 주소 (http://localhost:8000/docs)
    redoc_url="/redoc"
)

# 2. CORS(Cross-Origin Resource Sharing) 설정
# (Streamlit 포트인 8501과 FastAPI 포트인 8000 사이의 통신을 허용하기 위함)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # 실무에서는 ["http://localhost:8501"] 등으로 제한하지만, 개발 환경에서는 모두 열어둡니다.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3. 각 도메인별 라우터(부품)들을 메인 서버에 조립
app.include_router(video_api.router, prefix="/api/v1")
app.include_router(chat_api.router, prefix="/api/v1")
app.include_router(meeting_api.router, prefix="/api/v1")


# 4. 헬스 체크(Health Check) 엔드포인트
# 서버가 정상적으로 켜졌는지 확인하기 위한 기본 경로입니다.
@app.get("/", tags=["Health"])
async def health_check():
    return {
        "status": "success",
        "message": "🚀 무한상사 거버넌스 API 서버가 정상적으로 가동 중입니다."
    }
if __name__ == "__main__":
    # 보안 강화를 위해 외부망 접속을 차단하고 로컬(127.0.0.1)에서만 작동하도록 수정합니다.
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)