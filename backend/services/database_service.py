import sqlite3
import os
import logging

logger = logging.getLogger(__name__)

# DB 파일 경로 설정 (backend/services/ 위치에서 밖으로 나가서 database 폴더를 찾습니다)
DB_PATH = os.path.join(os.path.dirname(__file__), "../../database/relational/governance.db")

class DatabaseService:
    def _get_connection(self):
        """DB 연결을 안전하게 생성하는 내부 헬퍼 함수입니다."""
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            return conn
        except Exception as e:
            logger.error(f"DB 연결 실패: {e}")
            return None

    def save_analysis_results(self, meeting_id: str, summary: str, transcript: str):
        """AI가 분석한 회의 요약본과 전체 스크립트를 meetings 테이블에 저장합니다."""
        conn = self._get_connection()
        if not conn:
            return False
        
        try:
            cursor = conn.cursor()
            
            # 1. meetings 테이블에 요약본(purpose)과 스크립트(rag_context) 업데이트
            cursor.execute("""
                UPDATE meetings 
                SET purpose = ?, rag_context = ?, status = '완료'
                WHERE meeting_id = ?
            """, (summary, transcript, meeting_id))
            
            # [방어 로직] 만약 프론트엔드에서 아직 meeting_id를 INSERT 하지 않았다면? 
            # 에러를 내지 않고 일단 새 회의록으로 만들어버립니다.
            if cursor.rowcount == 0:
                logger.warning(f"[{meeting_id}] 기존 회의 기록이 없어 새로 생성합니다.")
                cursor.execute("""
                    INSERT INTO meetings (meeting_id, title, meeting_date, department, purpose, rag_context, status)
                    VALUES (?, ?, date('now'), ?, ?, ?, '완료')
                """, (meeting_id, f"AI 분석 회의 ({meeting_id[:6]})", "미지정", summary, transcript))

            conn.commit()
            logger.info(f"✅ [{meeting_id}] DB에 AI 분석 결과 저장 완료!")
            return True
            
        except Exception as e:
            conn.rollback() # 에러가 나면 데이터를 꼬이지 않게 원상복구(Rollback) 합니다.
            logger.error(f"❌ DB 저장 중 오류 발생: {e}")
            return False
        finally:
            conn.close() # 작업이 끝나면 무조건 DB 문을 닫습니다. (메모리 누수 방지)