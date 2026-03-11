# ==========================================================
# Meeting API Router
# 회의 데이터 조회 및 HITL 수정 기능 제공
# ==========================================================

import json
import logging
import sqlite3
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI

from schemas.meeting_schema import (
    ActionItem,
    InsightsSchema,
    MeetingMeta,
    MeetingReportResponse,
    SummarySchema,
)

router = APIRouter(prefix="/meetings", tags=["Meeting History"])
logger = logging.getLogger(__name__)

# DB 경로 설정
BASE_DIR = Path(__file__).resolve().parents[3]
DB_PATH = BASE_DIR / "database" / "relational" / "governance.db"

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.2)


# ----------------------------------------------------------
# 요청 데이터 Schema (HITL 수정 요청)
# ----------------------------------------------------------
class HitlEditRequest(BaseModel):
    meeting_id: str
    document_type: str
    current_text: str
    prompt: str


# ==========================================================
# [GET] 최신/특정 회의 리포트 조회
# ==========================================================
@router.get("/details/{meeting_id}", response_model=MeetingReportResponse)
async def get_meeting_details(meeting_id: str):
    try:
        if not DB_PATH.exists():
            logger.error(f"❌ DB 파일을 찾을 수 없습니다.: {DB_PATH}")
            raise HTTPException(status_code=500, detail="데이터베이스 연결 오류")

        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # 1. 쿼리 실행
        query = (
            "SELECT * FROM meetings ORDER BY rowid DESC LIMIT 1"
            if meeting_id == "latest"
            else "SELECT * FROM meetings WHERE meeting_id = ?"
        )
        params = () if meeting_id == "latest" else (meeting_id,)

        cursor.execute(query, params)
        row = cursor.fetchone()
        conn.close()

        if not row:
            raise HTTPException(
                status_code=404, detail="회의 데이터가 존재하지 않습니다."
            )

        # 2. sqlite3.Row를 dict로 변환 (속성 에러 방지)
        row_dict = dict(row)

        # 3. purpose 데이터 파싱 (JSON 에러 방어)
        raw_purpose = row_dict.get("purpose")
        summary_json = {}

        if raw_purpose:
            try:
                # JSON 문자열인 경우 파싱 시도
                summary_json = json.loads(raw_purpose)
            except (json.JSONDecodeError, TypeError):
                # JSON이 아닌 일반 텍스트일 경우 수동으로 구조 생성
                summary_json = {"summary": {"done": [str(raw_purpose)]}}

        # 4. Summary 데이터 구성 (기본값 보장)
        inner_summary = summary_json.get("summary", {})
        done_list = inner_summary.get("done", [])
        if not isinstance(done_list, list):
            done_list = [str(done_list)] if done_list else []

        display_text = (
            "\n".join(done_list) if done_list else "분석된 요약 내용이 없습니다."
        )

        # 5. ActionItem 리스트 변환 (다양한 DB 키값 대응)
        formatted_actions = []
        for act in summary_json.get("actions", []):
            if isinstance(act, dict):
                formatted_actions.append(
                    ActionItem(
                        Who=act.get("Who") or act.get("manager") or "미정",
                        What=act.get("What") or act.get("task") or "내용 없음",
                        When=act.get("When") or act.get("deadline") or "-",
                    )
                )

        # 6. 최종 결과 반환 (단 하나의 return문으로 정합성 유지)
        return MeetingReportResponse(
            meta=MeetingMeta(title=row_dict.get("title") or "제목 없음"),
            joiner=row_dict.get("joiner") or "미지정",
            summary=SummarySchema(
                display_text=display_text,
                done=done_list,
                will_do=[str(a) for a in summary_json.get("will_do", [])],
                tbd=inner_summary.get("tbd", []),
            ),
            actions=formatted_actions,
            insights=InsightsSchema(
                kpi=summary_json.get("insights", {}).get("kpi", "-"),
                risk_warning=summary_json.get("insights", {}).get("risk_warning", "-"),
            ),
        )

    except Exception as e:
        logger.error(f"❌ 서버 에러 상세: {e}")
        raise HTTPException(status_code=500, detail=f"리포트 생성 실패: {str(e)}")


# ==========================================================
# [POST] HITL수정 요청 처리
# ==========================================================
@router.post("/workflow/hitl-edit")
async def hitl_document_edit(request: HitlEditRequest):
    """
    사용자 지시사항(Prompt)을 반영하여 기존 문서를 AI로 재작성
    """
    logger.info(
        f"✍️ [HITL 편집 요청] Type: {request.document_type}, Meeting ID: {request.meeting_id}"
    )

    try:
        # --------------------------------------------------
        # HITL 수정용 프롬프트
        # --------------------------------------------------
        hitl_prompt = PromptTemplate(
            input_variables=["current", "instruction"],
            template="""
            당신은 전문 문서 편집 AI입니다. 
            아래의 기존 내용을 사용자의 지시사항에 맞게 수정해주세요.
            
            [기존 내용]
            {current}
            
            [수정 지시사항]
            {instruction}
            
            수정된 내용만 깔끔하게 반환하세요.
            """,
        )

        chain = hitl_prompt | llm

        response = chain.invoke(
            {"current": request.current_text, "instruction": request.prompt}
        )

        revised_text = response.content.strip()

        # --------------------------------------------------
        # 수정된 문서 DB 저장
        # --------------------------------------------------
        from services.database_service import DatabaseService

        db_service = DatabaseService()

        success = db_service.update_hitl_document(
            request.meeting_id,
            request.document_type,
            revised_text,
        )

        if not success:
            raise HTTPException(status_code=500, detail="DB 저장에 실패했습니다.")

        return {
            "status": "success",
            "revised_text": revised_text,
        }

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"❌ HITL 편집 실패: {e}")

        raise HTTPException(
            status_code=500,
            detail="AI 수정 처리 중 오류가 발생했습니다.",
        )
