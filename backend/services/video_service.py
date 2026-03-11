import asyncio
import logging
import json
import os
from services.database_service import DatabaseService

# 파이프라인 부품들
from pipelines.video_pipeline.step01_audio_to_text import AudioToTextProcessor
from pipelines.video_pipeline.step02_speaker_separator import SpeakerSeparator
from pipelines.video_pipeline.step03_text_splitter import TextSplitterProcessor
from pipelines.video_pipeline.step04_vector_embedding import VectorEmbeddingProcessor
from pipelines.video_pipeline.step05_qa_search_engine import QASearchEngine

logger = logging.getLogger(__name__)

class VideoAnalysisService:
    def __init__(self):
        try:
            self.step1 = AudioToTextProcessor()
            self.step2 = SpeakerSeparator()
            self.step3 = TextSplitterProcessor()
            self.step4 = VectorEmbeddingProcessor()
            self.step5 = QASearchEngine()
        except:
            self.step1 = AudioToTextProcessor(use_mock=False)
            self.step2 = SpeakerSeparator(use_mock=False)
            self.step3 = TextSplitterProcessor(use_mock=False)
            self.step4 = VectorEmbeddingProcessor(use_mock=False)
            self.step5 = QASearchEngine(use_mock=False)

        self.db_service = DatabaseService()

    async def run_pipeline(self, meeting_id: str, video_url: str, video_db: dict):
        try:
            logger.info(f"🚀 분석 시작 - ID: {meeting_id}, URL: {video_url}")

            # 1. Step 1 (Whisper)
            s1_result = await asyncio.to_thread(self.step1.run, video_url, meeting_id)
            if isinstance(s1_result, dict) and "transcript_with_time" in s1_result:
                raw_list = s1_result["transcript_with_time"]
            else:
                raw_list = [{"start": 0.0, "text": str(s1_result)}]

            # 2. Step 2 (화자 분리)
            diarized_list = await asyncio.to_thread(self.step2.run, raw_list)
            if not isinstance(diarized_list, list):
                diarized_list = [{"speaker": "Unknown", "time": "00:00", "text": "데이터 분석 중"}]

            # 3. Step 3 (텍스트 분할)
            chunks = await asyncio.to_thread(self.step3.run, diarized_list)

            # 4. Step 4 (벡터 저장)
            if chunks:
                await asyncio.to_thread(self.step4.run, meeting_id, chunks)

            # 5. Step 5 (요약 및 리포트 생성 - 고도화된 JSON 반환)
            analysis_report = await asyncio.to_thread(
                self.step5.summarize_meeting, meeting_id, diarized_list
            )

            # -------------------------------------------------------
            # 6. [추가] 3번 팀 DB 규격에 맞춘 데이터 가공 (핵심!)
            # -------------------------------------------------------
            # (1) 참석자(joiner) 명단 추출
            speakers = list(set([d['speaker'] for d in diarized_list if d.get('speaker')]))
            joiner_str = ", ".join(speakers)

            # (2) 3번 팀 UI가 사용하는 'purpose' 및 'actions' JSON 생성
            purpose_json_str = json.dumps(analysis_report, ensure_ascii=False)
            actions_json_str = json.dumps(analysis_report.get("actions", []), ensure_ascii=False)
            
            # (3) 요약 텍스트 추출 (리스트의 첫 번째 항목 또는 문자열)
            done_list = analysis_report.get("summary", {}).get("done", [])
            summary_text = done_list[0] if done_list else "분석 완료"

            # 7. [수정] DB 서비스 호출 (3번 팀 컬럼명에 매칭)
            # DatabaseService의 save_analysis_results가 아래 인자들을 받도록 되어 있어야 합니다.
            self.db_service.save_analysis_results(
                meeting_id=meeting_id,
                video_url=video_url,
                purpose=purpose_json_str,      # 3번 팀 메인 데이터
                summary=summary_text,          # 대표 요약문
                joiner=joiner_str,             # 참석자 명단
                actions=actions_json_str,      # 액션 아이템 JSON 리스트
                kpi=analysis_report.get("insights", {}).get("kpi", "-"),
                risks=analysis_report.get("insights", {}).get("risk_warning", "-"),
                transcript=json.dumps(diarized_list, ensure_ascii=False)
            )

            # [방어] 데이터 규격 강제 및 상태 업데이트
            safe_transcript = diarized_list if isinstance(diarized_list, list) else []
            if meeting_id in video_db:
                video_db[meeting_id].update({
                    "status": "completed",
                    "percent": 100,
                    "transcript": safe_transcript,
                    "report": analysis_report,
                    "summary": analysis_report,
                    "msg": "모든 분석이 성공적으로 완료되었습니다!",
                })

            logger.info(f"✅ [{meeting_id}] 분석 및 DB(purpose/joiner/actions 등) 저장 완료")

            return {
                "meeting_id": meeting_id,
                "status": "success",
                "transcript": safe_transcript,
                "report": analysis_report,
            }

        except Exception as e:
            logger.error(f"❌ 파이프라인 에러: {e}")
            if meeting_id in video_db:
                video_db[meeting_id].update({"status": "error", "msg": str(e)})

# [브릿지 함수]
async def run_video_analysis_pipeline(meeting_id, video_url, video_db):
    service = VideoAnalysisService()
    await service.run_pipeline(meeting_id, video_url, video_db)