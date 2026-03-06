-- ==============================================================================
-- 🏢 무한상사 AI 거버넌스 시스템 - 슬림 MVP 데이터베이스 스키마 (최종본)
-- ==============================================================================

PRAGMA foreign_keys = ON;

-- ---------------------------------------------------------
-- 1. Meetings (회의 마스터 테이블)
-- 회의 기본 정보, 비디오 분석 파이프라인(1~5단계) 진행 상태, 최종 요약본을 저장합니다.
-- ---------------------------------------------------------
CREATE TABLE IF NOT EXISTS meetings (
    meeting_id VARCHAR(50) PRIMARY KEY,      -- 예: 'MEET-2026-001' (UUID 등)
    title VARCHAR(200) NOT NULL,             -- 회의 제목
    meeting_date DATE NOT NULL,              -- 회의 날짜
    department VARCHAR(100) NOT NULL,        -- 부서명 (예: '영업본부')
    
    -- [AI 파이프라인 상태 관리]
    status VARCHAR(50) DEFAULT '업로드 대기',   -- '진행중', '완료', '에러'
    pipeline_step INTEGER DEFAULT 0,         -- 0~5단계 (1:STT, 2:화자분리, 3:청크, 4:벡터DB, 5:요약)
    
    -- [AI 생성 결과물]
    summary TEXT,                            -- AI가 생성한 마크다운 형식의 최종 회의 요약
    video_path VARCHAR(255),                 -- 원본 영상 또는 오디오 파일 경로
    
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ---------------------------------------------------------
-- 2. Actions (파생 액션 아이템 테이블)
-- 03_action_reports.py 화면에서 보여줄 '누가, 언제까지, 무엇을 할 것인가'를 저장합니다.
-- ---------------------------------------------------------
CREATE TABLE IF NOT EXISTS actions (
    action_id VARCHAR(50) PRIMARY KEY,       -- 예: 'ACT-1001'
    meeting_id VARCHAR(50) NOT NULL,         -- 해당 액션이 도출된 회의 (FK)
    task_description TEXT NOT NULL,          -- 실행해야 할 업무 내용
    assignee VARCHAR(100) NOT NULL,          -- 담당자
    deadline DATE NOT NULL,                  -- 기한
    status VARCHAR(50) DEFAULT '진행중',        -- '진행중', '완료', '지연'
    
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (meeting_id) REFERENCES meetings(meeting_id) ON DELETE CASCADE
);