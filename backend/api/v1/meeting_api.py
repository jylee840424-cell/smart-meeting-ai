# ==========================================================
# 회의 데이터 조회 및 HITL 수정 기능 제공
# ==========================================================
import ast
import json
import logging
import sqlite3
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from langchain_openai import ChatOpenAI
from schemas.meeting_schema import MeetingReportResponse
from services.database_service import DatabaseService

# FastAPI 라우터 설정
router = APIRouter(prefix="/meetings", tags=["Meeting History"])
logger = logging.getLogger(__name__)

# 1. LLM 및 DB 서비스 초기화
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.2)  # 회의 문서 수정용 LLM
db_service = DatabaseService()  # DB 업데이트 처리 서비스

# DB 파일 경로 설정
BASE_DIR = Path(__file__).resolve().parents[3]
DB_PATH = BASE_DIR / "database" / "relational" / "governance.db"


# HITL 수정 요청 데이터 모델
class HitlEditRequest(BaseModel):
    meeting_id: str
    document_type: str
    current_text: str
    prompt: str


# SQLite DB 연결 생성
def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # 컬럼명 기반 접근 가능
    return conn


# ==========================================================
# [GET] 회의 리포트 조회
# ==========================================================
@router.get("/details/{meeting_id}", response_model=MeetingReportResponse)
async def get_meeting_details(meeting_id: str):
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Latest 요청 시 가장 최근 회의 조희
        if meeting_id == "latest":
            cursor.execute("SELECT * FROM meetings ORDER BY created_at DESC LIMIT 1")
        else:
            cursor.execute("SELECT * FROM meetings WHERE meeting_id = ?", (meeting_id,))

        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="회의 정보를 찾을 수 없습니다.")

        report_dict = dict(row)

    except Exception as e:
        logger.error(f"DB 조회 실패: {e}")
        raise HTTPException(status_code=500, detail="데이터베이스 연동 실패")
    finally:
        if conn:
            conn.close()

    # DB 데이터 → API 응답 구조로 변환
    try:
        purpose_data = json.loads(report_dict.get("purpose", "{}"))

        # 중첩된 summary 구조 처리
        s_data = purpose_data.get("summary", {})
        if isinstance(s_data, dict) and "summary" in s_data:
            s_data = s_data["summary"]

        summary_obj = {
            "display_text": s_data.get("display_text")
            or report_dict.get("details", "분석 중..."),
            "done": s_data.get("done") if isinstance(s_data.get("done"), list) else [],
            "will_do": (
                s_data.get("will_do") if isinstance(s_data.get("will_do"), list) else []
            ),
            "tbd": s_data.get("tbd") if isinstance(s_data.get("tbd"), list) else [],
        }

        # --------------------------------------------------
        # actions 데이터 파싱
        # - 문자열 / JSON / 리스트 등 다양한 형태 대응
        # --------------------------------------------------
        actions_raw = report_dict.get("actions", [])

        if isinstance(actions_raw, str):
            actions_raw = actions_raw.strip()
            if actions_raw:
                try:
                    # JSON 형태 파싱
                    actions_raw = json.loads(actions_raw)
                except:
                    try:
                        # Python dict 문자열 파싱
                        actions_raw = ast.literal_eval(actions_raw)
                    except:
                        # 실패 시 줄바꿈으로 분리
                        actions_raw = [
                            line.strip()
                            for line in actions_raw.splitlines()
                            if line.strip()
                        ]
            else:
                actions_raw = []

        # FastAPI 응답 모델 규격에 맞게 정리
        actions_list = []
        if isinstance(actions_raw, list):
            for item in actions_raw:

                # 문자열 형태 dict 변환
                if isinstance(item, str) and (
                    item.startswith("{") or item.startswith("[")
                ):
                    try:
                        item = ast.literal_eval(item)
                    except:
                        pass

                if isinstance(item, dict):
                    actions_list.append(
                        {
                            "Who": str(item.get("Who") or item.get("who") or "전체"),
                            "What": str(
                                item.get("What") or item.get("what") or "내용 없음"
                            ),
                            "When": str(
                                item.get("When") or item.get("when") or "확인필요"
                            ),
                        }
                    )

                # dict가 아닌 문자열인 경우
                elif item:
                    actions_list.append(
                        {"Who": "전체", "What": str(item), "When": "확인필요"}
                    )

        # --------------------------------------------------
        # 최종 API 응답 구조 반환
        # --------------------------------------------------
        return {
            "meta": {"title": report_dict.get("title") or "제목 없음"},
            "meeting_id": report_dict.get("meeting_id")
            or report_dict.get("id")
            or "latest",
            "joiner": report_dict.get("joiner") or "미지정",
            "summary": summary_obj,
            "actions": actions_list,
            "insights": {
                "kpi": report_dict.get("kpi", "-"),
                "risk_warning": report_dict.get("risks", "-"),
            },
        }

    except Exception as e:
        logger.error(f"Mapping Error: {e}")
        raise HTTPException(status_code=500, detail="데이터 변환 오류")


# ==========================================================
# [POST] 실시간 수정
# ==========================================================
@router.post("/workflow/hitl-edit")
async def edit_meeting_document(request: HitlEditRequest):
    try:
        # LLM 수정 요청 프롬프트 생성
        prompt_text = f"수정분야: {request.document_type}\n현재: {request.current_text}\n요청: {request.prompt}\n# 수정된 본문만 출력."

        response = llm.invoke(prompt_text)
        revised_text = response.content.strip()

        # DB 컬럼명 매핑 처리
        doc_type = request.document_type
        if doc_type == "risk_warning":
            doc_type = "risks"

        # 수정 결과 DB 저장
        success = db_service.update_hitl_document(
            meeting_id=request.meeting_id,
            document_type=doc_type,
            revised_text=revised_text,
        )

        if not success:
            raise HTTPException(status_code=500, detail="DB 저장 실패")

        return {"status": "success", "revised_text": revised_text}

    except Exception as e:
        logger.error(f"HITL Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
