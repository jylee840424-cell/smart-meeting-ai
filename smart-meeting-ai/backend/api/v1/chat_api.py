import sqlite3
import os
import logging
import asyncio
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from schemas.chat_schema import ChatRequest

# 우리가 만든 진짜 AI 부품들 호출
from services.knowledge_base_service import KnowledgeBaseService
from pipelines.rag_pipeline import RAGPipeline

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["Hybrid RAG Chat"])



@router.get("/meetings")
def get_completed_meetings():
    """DB(governance.db)에서 분석이 완료된 실제 회의 목록을 최신순으로 가져옵니다."""
    try:
        # [핵심 수정 1] DB 경로 안전하게 찾기 (backend 폴더 밖으로 나가야 하므로 4번 올라갑니다)
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        db_path = os.path.join(base_dir, "database", "relational", "governance.db")
        
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 완료된 회의만 최신순으로 가져오기
        cursor.execute("SELECT meeting_id, title, meeting_date, department FROM meetings WHERE status = '완료' ORDER BY meeting_date DESC")
        rows = cursor.fetchall()
        conn.close()
        
        # 프론트엔드 드롭다운에 예쁘게 보일 메타데이터 문자열 조합
        result = []
        for row in rows:
            display_title = f"[{row['meeting_date']}] {row['title']} ({row['department']})"
            result.append({"id": row["meeting_id"], "display_name": display_title})
            
        return result
    except Exception as e:
        logger.error(f"❌ DB 회의 목록 조회 오류: {e}")
        return []


@router.post("/ask")
async def ask_expert_agent(request: ChatRequest):
    """
    [Real RAG 챗봇 API] 
    사용자 질문(prompt)과 요청 모드(mode)를 받아 Vector DB를 검색하고, 
    GPT-4o가 생성한 맞춤형 답변을 타닥타닥 타이핑되는 스트리밍 방식으로 반환합니다.
    """
    logger.info(f"💬 [모드: {request.mode}] 질문 수신: {request.prompt}")

    # 1. 도서관 사서(Vector DB)에게 문맥 찾아오라고 지시
    kb_service = KnowledgeBaseService()
    context = kb_service.search_relevant_context(request.meeting_id, request.prompt)

    # 2. 브레인(LLM) 파이프라인 준비
    rag_pipeline = RAGPipeline()

    # 3. 비동기 스트리밍 제너레이터 함수 (텍스트를 한 조각씩 밀어냅니다)
    async def generate_stream():
        try:
            # =========================================================
            # [핵심 수정 2] 프론트엔드에서 받아온 request.mode를 반드시 넘겨줍니다!
            # 이 파라미터가 있어야 rag_pipeline이 뇌구조(검증/자문)를 바꿀 수 있습니다.
            # =========================================================
            async for chunk in rag_pipeline.stream_answer(request.prompt, context, request.mode):
                yield chunk
        except Exception as e:
            logger.error(f"❌ 스트리밍 중 오류: {e}")
            yield f"\n\n[오류] 답변 생성 중 문제가 발생했습니다: {str(e)}"

    # 4. 일반 딕셔너리 반환이 아닌 StreamingResponse로 통신구 개방!
    return StreamingResponse(
        generate_stream(), 
        media_type="text/event-stream"
    )