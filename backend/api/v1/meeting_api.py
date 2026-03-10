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

        # DB의 'purpose' 컬럼에서 데이터를 가져와야 합니다.
        raw_purpose = row["purpose"]
        summary_json = {}

        if raw_purpose:
            try:
                summary_json = json.loads(raw_purpose)
            except Exception:
                # JSON 형식이 아닐 경우 단순 문자열 처리
                summary_json = {"summary": {"done": [raw_purpose], "tbd": []}}

        # -------------------------------
        # summary JSON 파싱 & 방어
        # -------------------------------
        summary_json = {}
        try:
            summary_json = json.loads(row["purpose"]) if row["purpose"] else {}
        except Exception:
            logger.warning(
                f"[{row['meeting_id']}] purpose JSON 파싱 실패, 기본 구조 생성"
            )
            summary_json = {}

        # 기본 구조 보장 및 필드 매핑
        summary_data = {
            "summary": summary_json.get("summary", {"done": [], "tbd": []}),
            "actions": summary_json.get("actions", []),
            "insights": summary_json.get("insights", {"kpi": "-", "risk_warning": "-"}),
            "joiner": summary_json.get(
                "joiner", row["joiner"] if "joiner" in row.keys() else "미지정"
            ),
        }

        # display_text 생성 (프론트엔드 DONE 카드용)
        done_lines = summary_data["summary"].get("done", [])
        display_text = (
            "\n".join(done_lines) if done_lines else "분석된 요약 내용이 없습니다."
        )

        # ActionItem 리스트 변환
        formatted_actions = []
        for act in summary_data["actions"]:
            if isinstance(act, dict):
                formatted_actions.append(
                    ActionItem(
                        Who=act.get("Who", act.get("manager", "미정")),
                        What=act.get("What", act.get("task", "내용 없음")),
                        When=act.get("When", act.get("deadline", "-")),
                    )
                )

        return MeetingReportResponse(
            meta=MeetingMeta(title=row["title"] or "회의 분석 보고서"),
            joiner=summary_data["joiner"],
            summary=SummarySchema(
                display_text=display_text,
                done=done_lines,
                will_do=summary_data["actions"],
                tbd=summary_data["summary"].get("tbd", []),
            ),
            actions=formatted_actions,
            insights=InsightsSchema(
                kpi=summary_data["insights"].get("kpi", "-"),
                risk_warning=summary_data["insights"].get("risk_warning", "-"),
            ),
        )
    except Exception as e:
        logger.error(f"서버 에러: {e}")
        raise HTTPException(status_code=500, detail="리포트 생성 실패")


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
