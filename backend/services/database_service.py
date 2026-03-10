import sqlite3
import os
import logging
import json

logger = logging.getLogger(__name__)

# DB 경로 설정 
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
DB_PATH = os.path.normpath(os.path.join(BASE_DIR, "database/relational/governance.db"))

class DatabaseService:
    def __init__(self):
        # 클래스 생성 시 자동으로 테이블 및 컬럼 체크 
        self._ensure_table_exists()

    def _get_connection(self):
        """DB 연결 생성 (row_factory 설정으로 컬럼명 접근 가능)"""
        try:
            os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            return conn
        except Exception as e:
            logger.error(f"DB 연결 실패: {e}")
            return None

    def _ensure_table_exists(self):
        """테이블 자동 생성 및 video_url 컬럼 추가 (방어 로직)"""
        conn = self._get_connection()
        if not conn: return
        try:
            cursor = conn.cursor()
            # 1. 테이블 생성 (기존 팀원들의 purpose, rag_context 명칭 유지 + video_url 추가)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS meetings (
                    meeting_id TEXT PRIMARY KEY,
                    title TEXT,
                    meeting_date TEXT,
                    department TEXT,
                    video_url TEXT,
                    purpose TEXT,
                    rag_context TEXT,
                    status TEXT,
                    pipeline_step INTEGER DEFAULT 0
                )
            """)
            # 2. video_url 컬럼이 혹시 없으면 추가 (하이브리드 체크)
            cursor.execute("PRAGMA table_info(meetings)")
            columns = [column[1] for column in cursor.fetchall()]
            if 'video_url' not in columns:
                cursor.execute("ALTER TABLE meetings ADD COLUMN video_url TEXT")
                logger.info("✅ 'video_url' 컬럼이 추가되었습니다.")
            conn.commit()
        except Exception as e:
            logger.error(f"테이블 체크 실패: {e}")
        finally:
            conn.close()

    def save_analysis_results(self, meeting_id: str, video_url: str, summary: str, transcript: str):
        """AI 분석 결과 저장 (진모님 방식 + 팀원 규격 합체)"""
        conn = self._get_connection()
        if not conn: return False
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO meetings (
                    meeting_id, title, meeting_date, department, 
                    video_url, purpose, rag_context, status, pipeline_step
                )
                VALUES (?, ?, date('now'), ?, ?, ?, ?, '완료', 5)
            """, (
                meeting_id, f"AI 분석 회의 ({meeting_id[:6]})", "미지정", 
                video_url, summary, transcript
            ))
            conn.commit()
            logger.info(f"✅ [{meeting_id}] DB 저장 완료 (URL: {video_url})")
            return True
        except Exception as e:
            conn.rollback()
            logger.error(f"❌ DB 저장 오류: {e}")
            return False
        finally:
            conn.close()

    def get_latest_meeting(self):
        """최신 회의 데이터 조회 (팀원 추가 기능)"""
        conn = self._get_connection()
        if not conn: return None
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM meetings ORDER BY rowid DESC LIMIT 1")
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    # ------------------------------------------------------
    # HITL 문서 업데이트
    # ------------------------------------------------------
    def update_hitl_document(self, meeting_id: str, document_type: str, revised_text):
        """
        HITL(Human-In-The-Loop) 문서 수정 결과를 DB에 반영
        - revised_text: string 또는 리스트(dict) 형태 모두 허용
        document_type:
            - 'done'    → summary.done
            - 'actions' → actions
            - 'risks'   → insights.risk_warning
        """
        conn = self._get_connection()
        if not conn:
            return False

        try:
            cursor = conn.cursor()

            # 회의 데이터 조회
            if meeting_id == "latest":
                cursor.execute(
                    "SELECT meeting_id, purpose FROM meetings ORDER BY rowid DESC LIMIT 1"
                )
            else:
                cursor.execute(
                    "SELECT meeting_id, purpose FROM meetings WHERE meeting_id = ?",
                    (meeting_id,),
                )

            row = cursor.fetchone()
            if not row:
                logger.error(f"[{meeting_id}] 회의 데이터 없음")
                return False

            actual_meeting_id = row["meeting_id"]
            purpose_data = row["purpose"]

            # JSON 파싱
            try:
                summary_data = json.loads(purpose_data)
            except Exception:
                logger.warning("purpose JSON 파싱 실패 → 기본 구조 생성")
                summary_data = {
                    "summary": {"done": [], "tbd": []},
                    "actions": [],
                    "insights": {"kpi": "-", "risk_warning": "-"},
                }

            # JSON 구조 방어
            summary_data.setdefault("summary", {"done": [], "tbd": []})
            summary_data.setdefault("actions", [])
            summary_data.setdefault("insights", {"kpi": "-", "risk_warning": "-"})

            # document_type → JSON path 업데이트
            if document_type == "done":
                summary_data["summary"]["done"] = (
                    [revised_text] if isinstance(revised_text, str) else revised_text
                )
            elif document_type == "actions":
                if isinstance(revised_text, str):
                    revised_text = [{"Who": "-", "What": revised_text, "When": "-"}]
                summary_data["actions"] = revised_text
            elif document_type == "risks":
                summary_data["insights"]["risk_warning"] = revised_text
            else:
                logger.warning(f"⚠️ 알 수 없는 document_type: {document_type}")
                return False

            # JSON 저장
            updated_json = json.dumps(summary_data, ensure_ascii=False)
            cursor.execute(
                "UPDATE meetings SET purpose = ? WHERE meeting_id = ?",
                (updated_json, actual_meeting_id),
            )

            conn.commit()
            logger.info(f"✅ HITL 문서 업데이트 완료 ({document_type})")
            return True

        except Exception as e:
            conn.rollback()
            logger.error(f"❌ HITL 업데이트 오류: {e}")
            return False

        finally:
            conn.close()