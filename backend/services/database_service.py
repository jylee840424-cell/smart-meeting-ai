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
        """테이블 자동 생성 및 3번 팀 컬럼(joiner, kpi 등) 추가 (방어 로직)"""
        conn = self._get_connection()
        if not conn: return
        try:
            cursor = conn.cursor()
            # 1. 테이블 생성 (3번 팀의 UI 연동을 위한 컬럼들 대거 추가)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS meetings (
                    meeting_id TEXT PRIMARY KEY,
                    title TEXT,
                    meeting_date TEXT,
                    department TEXT,
                    video_url TEXT,
                    purpose TEXT,        -- 통합 분석 리포트 (JSON)
                    joiner TEXT,         -- 참석자 명단
                    done TEXT,           -- 결정 사항 (텍스트)
                    actions TEXT,        -- 액션 아이템 (JSON 리스트)
                    kpi TEXT,            -- 성과 지표
                    risks TEXT,          -- 리스크 요약
                    rag_context TEXT,    -- 전체 스크립트 (기존 명칭 유지)
                    status TEXT,
                    pipeline_step INTEGER DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 2. 누락된 컬럼 자동 추가 (마이그레이션 방어 로직)
            cursor.execute("PRAGMA table_info(meetings)")
            columns = [column[1] for column in cursor.fetchall()]
            
            # 추가가 필요한 컬럼 리스트
            required_columns = {
                'video_url': 'TEXT',
                'joiner': 'TEXT',
                'done': 'TEXT',
                'actions': 'TEXT',
                'kpi': 'TEXT',
                'risks': 'TEXT'
            }

            for col_name, col_type in required_columns.items():
                if col_name not in columns:
                    cursor.execute(f"ALTER TABLE meetings ADD COLUMN {col_name} {col_type}")
                    logger.info(f"✅ '{col_name}' 컬럼이 추가되었습니다.")
            
            conn.commit()
        except Exception as e:
            logger.error(f"테이블 체크 실패: {e}")
        finally:
            conn.close()

    def save_analysis_results(self, meeting_id: str, video_url: str, purpose: str, 
                              summary: str, joiner: str, actions: str, kpi: str, risks: str, transcript: str):
        """
        AI 분석 결과 저장 (Step 05의 모든 결과물을 3번 팀 컬럼 규격에 맞춰 분산 저장)
        """
        conn = self._get_connection()
        if not conn: return False
        try:
            cursor = conn.cursor()
            # 3번 팀 UI가 읽어가는 모든 컬럼에 데이터 매칭
            cursor.execute("""
                INSERT OR REPLACE INTO meetings (
                    meeting_id, title, meeting_date, department, 
                    video_url, purpose, joiner, done, actions, kpi, risks,
                    rag_context, status, pipeline_step
                )
                VALUES (?, ?, date('now'), ?, ?, ?, ?, ?, ?, ?, ?, ?, '완료', 5)
            """, (
                meeting_id, 
                f"AI 분석 회의 ({meeting_id[:6]})", 
                "미지정부서", 
                video_url, 
                purpose,    # 전체 JSON
                joiner,     # 화자 명단
                summary,    # 요약 텍스트 (done)
                actions,    # 액션플랜 JSON
                kpi,        # KPI 점수
                risks,      # 리스크 요약
                transcript  # 전체 대화 스크립트
            ))
            conn.commit()
            logger.info(f"✅ [{meeting_id}] DB 저장 완료 (모든 분석 컬럼 포함)")
            return True
        except Exception as e:
            conn.rollback()
            logger.error(f"❌ DB 저장 오류: {e}")
            return False
        finally:
            conn.close()

    def get_latest_meeting(self):
        """최신 회의 데이터 조회"""
        conn = self._get_connection()
        if not conn: return None
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM meetings ORDER BY created_at DESC LIMIT 1")
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def update_hitl_document(self, meeting_id: str, document_type: str, revised_text):
        """
        HITL(Human-In-The-Loop) 수정 기능을 지원하며, 수정된 내용을 개별 컬럼에도 동기화합니다.
        """
        conn = self._get_connection()
        if not conn: return False

        try:
            cursor = conn.cursor()
            # 데이터 조회
            if meeting_id == "latest":
                cursor.execute("SELECT * FROM meetings ORDER BY created_at DESC LIMIT 1")
            else:
                cursor.execute("SELECT * FROM meetings WHERE meeting_id = ?", (meeting_id,))

            row = cursor.fetchone()
            if not row: return False

            actual_id = row["meeting_id"]
            try:
                summary_data = json.loads(row["purpose"])
            except:
                summary_data = {"summary": {"done": []}, "actions": [], "insights": {}}

            # 수정 로직 및 개별 컬럼 동기화 준비
            target_col = None
            new_val = None

            if document_type == "done":
                summary_data.setdefault("summary", {})["done"] = [revised_text] if isinstance(revised_text, str) else revised_text
                target_col = "done"
                new_val = revised_text if isinstance(revised_text, str) else "\n".join(revised_text)
            
            elif document_type == "actions":
                if isinstance(revised_text, str):
                    revised_text = [{"Who": "-", "What": revised_text, "When": "-"}]
                summary_data["actions"] = revised_text
                target_col = "actions"
                new_val = json.dumps(revised_text, ensure_ascii=False)
            
            elif document_type == "risks":
                summary_data.setdefault("insights", {})["risk_warning"] = revised_text
                target_col = "risks"
                new_val = revised_text

            # 1. 통합 JSON(purpose) 업데이트
            updated_json = json.dumps(summary_data, ensure_ascii=False)
            
            # 2. 개별 컬럼과 purpose를 동시에 업데이트
            if target_col:
                cursor.execute(f"UPDATE meetings SET purpose = ?, {target_col} = ? WHERE meeting_id = ?",
                               (updated_json, new_val, actual_id))
            else:
                cursor.execute("UPDATE meetings SET purpose = ? WHERE meeting_id = ?", (updated_json, actual_id))

            conn.commit()
            logger.info(f"✅ HITL 업데이트 완료: {document_type}")
            return True

        except Exception as e:
            conn.rollback()
            logger.error(f"❌ HITL 업데이트 오류: {e}")
            return False
        finally:
            conn.close()