import sqlite3
import logging
from pathlib import Path
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from core.prompts import AGENT_MODE_INSTRUCTIONS

# 스키마 및 서비스 임포트
from schemas.chat_schema import ChatRequest
from services.knowledge_base_service import KnowledgeBaseService, build_production_agent

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["Hybrid RAG Chat"])

# ==========================================
# 의존성 주입(DI)을 위한 싱글톤 에이전트 설정
# ==========================================

# DB를 찾을 때 '절대 경로'
_golden_base_dir = str(Path(__file__).resolve().parents[3])

_kb_service = KnowledgeBaseService(base_dir=_golden_base_dir)
_expert_agent = build_production_agent(_kb_service, model_name="gpt-4o-mini")

def get_expert_agent():
    """FastAPI 라우터에 에이전트를 안전하게 주입해 주는 함수입니다."""
    return _expert_agent

# ==========================================
# DB 헬퍼 함수 분리 (웨이터와 요리사의 분리)
# ==========================================
def fetch_completed_meetings_from_db():
    """DB에서 완료된 회의 목록만 가져오는 순수 데이터 처리 함수입니다."""
    # [개선 1] pathlib을 사용하여 안전하고 우아하게 경로 찾기
    # 현재 파일 위치에서 상위 폴더로 이동 후 database/relational/governance.db 연결
    base_dir = Path(__file__).resolve().parents[3]
    db_path = base_dir / "database" / "relational" / "governance.db"
    
    if not db_path.exists():
        logger.error(f"⚠️ DB 파일을 찾을 수 없습니다: {db_path}")
        return []

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT meeting_id, title, meeting_date, department FROM meetings WHERE status = '완료' ORDER BY meeting_date DESC")
    rows = cursor.fetchall()
    conn.close()
    
    return rows


@router.get("/meetings")
def get_completed_meetings():
    """프론트엔드 드롭다운용 회의 목록 반환 API"""
    try:
        rows = fetch_completed_meetings_from_db()
        result = [
            {
                "id": row["meeting_id"], 
                "display_name": f"[{row['meeting_date']}] {row['title']} ({row['department']})"
            } 
            for row in rows
        ]
        return result
    except Exception as e:
        logger.error(f"❌ DB 회의 목록 조회 오류: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="회의 목록을 불러오는 중 오류가 발생했습니다.")


@router.post("/ask")
async def ask_expert_agent(request: ChatRequest, agent = Depends(get_expert_agent)):
    """
    [지능형 Agent 챗봇 API] 
    사용자 질문과 모드를 에이전트에게 전달하여 맞춤형 답변을 스트리밍으로 반환합니다.
    """
    logger.info(f"💬 [모드: {request.mode}] 질문 수신: {request.prompt}")

    # 1. 프롬프트 모듈에서 모드에 맞는 지시사항 가져오기 (기본값은 '자문'으로 방어 로직 추가)
    mode_key = "검증" if request.mode in ["검증", "verification", "검증 모드"] else "자문"
    mode_instruction = AGENT_MODE_INSTRUCTIONS.get(mode_key)

    # 2. 사용자 입력은 순수하게 유지
    user_input = f"[회의록 ID: {request.meeting_id}]\n질문: {request.prompt}"

    # 3. 비동기 스트리밍 제너레이터
    async def generate_stream():
        try:
            session_id = getattr(request, "session_id", "default_user_session")
            
            # [수정됨] mode_instruction을 딕셔너리에 명시적으로 전달합니다.
            async for event in agent.astream_events(
                {
                    "input": user_input,
                    "mode_instruction": mode_instruction # 템플릿 변수에 매핑됨
                },
                config={"configurable": {"session_id": session_id}},
                version="v2"
            ):
                if event["event"] == "on_chat_model_stream":
                    chunk = event["data"]["chunk"].content
                    if chunk:
                        yield chunk
                        
        except Exception as e:
            logger.error(f" 에이전트 스트리밍 중 오류: {e}", exc_info=True)
            yield f"\n\n[오류] 답변을 생성하는 도중 시스템 문제가 발생했습니다."

    return StreamingResponse(generate_stream(), media_type="text/event-stream")