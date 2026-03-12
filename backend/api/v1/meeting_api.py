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

        if isinstance(raw_purpose, str):
            try:
                # JSON 문자열인 경우 파싱 시도
                summary_json = json.loads(raw_purpose)
            except (json.JSONDecodeError, TypeError):
                # JSON이 아닌 일반 텍스트일 경우 수동으로 구조 생성
                summary_json = {
                    "summary": {"done": [raw_purpose]},
                    "actions": [],
                    "insights": {},
                }
        else:
            # 이미 dict(객체) 형태라면 그대로 사용
            summary_json = raw_purpose if raw_purpose else {}

        # 4. 요약 데이터 처리 (리스트를 불렛포인트로 변환)
        inner_summary = summary_json.get("summary", {})
        done_list = inner_summary.get("done", [])

        # 리스트인 경우 줄바꿈을 포함한 텍스트로, 문자열인 경우 그대로 사용
        if isinstance(done_list, list):
            display_text = "\n".join([f"- {str(item)}" for item in done_list])
        else:
            display_text = str(done_list)

        # 5. ActionItem 리스트 변환 (다양한 DB 키값 대응)
        formatted_actions = []
        for act in summary_json.get("actions", []):
            if isinstance(act, dict):
                # 모든 필드값을 str()로 감싸서 dict가 들어와도 에러가 나지 않게 방어합니다.
                who_val = (
                    act.get("Who") or act.get("manager") or act.get("owner") or "미정"
                )
                what_val = act.get("What") or act.get("task") or "내용 없음"
                when_val = (
                    act.get("When") or act.get("deadline") or act.get("due_date") or "-"
                )

                formatted_actions.append(
                    ActionItem(
                        Who=str(who_val),
                        What=str(what_val),
                        When=str(when_val),
                    )
                )

        # 6. 최종 결과 반환
        return MeetingReportResponse(
            meta=MeetingMeta(title=row_dict.get("title") or "제목 없음"),
            joiner=row_dict.get("joiner") or "미지정",
            summary=SummarySchema(
                display_text=str(display_text),  # 문자열 보장
                done=done_list,
                will_do=[str(a) for a in summary_json.get("will_do", [])],
                tbd=inner_summary.get("tbd", []),
            ),
            actions=formatted_actions,
            insights=InsightsSchema(
                kpi=str(summary_json.get("insights", {}).get("kpi", "-")),
                risk_warning=str(
                    summary_json.get("insights", {}).get("risk_warning", "-")
                ),
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
        # 데이터 구조 방어 로직 (step05 호환)
        # --------------------------------------------------
        # AI가 준 평문 텍스트를 step05가 인식할 수 있는 JSON 구조로 재포장합니다.
        if request.document_type == "done":
            # 요약 수정 시: 줄바꿈을 기준으로 리스트화하여 JSON 생성
            final_save_value = json.dumps(
                {
                    "done": [
                        line.strip()
                        for line in revised_text.split("\n")
                        if line.strip()
                    ],
                    "tbd": [],  # 기존 구조 유지
                },
                ensure_ascii=False,
            )
        elif request.document_type == "actions":
            # 액션 수정 시: 리스트 안에 딕셔너리가 들어가는 구조 유지
            final_save_value = json.dumps(
                [{"Who": "전체", "What": revised_text, "When": "확인필요"}],
                ensure_ascii=False,
            )
        else:
            final_save_value = revised_text

        # --------------------------------------------------
        # 수정된 문서 DB 저장
        # --------------------------------------------------
        from services.database_service import DatabaseService

        db_service = DatabaseService()

        success = db_service.update_hitl_document(
            request.meeting_id,
            request.document_type,
            final_save_value,
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
