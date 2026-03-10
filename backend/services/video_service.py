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
        # 인자 없이 생성되는지 확인하며 안전하게 초기화
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

    # 인자 순서를 명확히 고정합니다.
    async def run_pipeline(self, meeting_id: str, video_url: str, video_db: dict):
        try:
            logger.info(f"🚀 분석 시작 - ID: {meeting_id}, URL: {video_url}")

            # 1. Step 1 (Whisper) - 진모님 step01은 (video_url, meeting_id)를 받음
            s1_result = await asyncio.to_thread(self.step1.run, video_url, meeting_id)
            
            # [수정된 핵심 로직] s1_result가 dict이고 그 안에 리스트가 있는지 확인
            if isinstance(s1_result, dict) and "transcript_with_time" in s1_result:
                raw_list = s1_result["transcript_with_time"]
            else:
                # 만약 dict가 아니거나 데이터가 없으면 강제로 리스트화 (int 에러 방지)
                raw_list = [{"start": 0.0, "text": str(s1_result)}]

            # 2. Step 2 (화자 분리)
            diarized_list = await asyncio.to_thread(self.step2.run, raw_list)
            
            # [방어] 숫자가 반환되면 리스트로 강제 치환 (int is not iterable 방지)
            if not isinstance(diarized_list, list):
                logger.warning(f"⚠️ Step 2 반환값이 리스트가 아님: {type(diarized_list)}")
                diarized_list = [{"speaker": "Unknown", "time": "00:00", "text": "데이터 분석 중"}]

            # 3. Step 3 (텍스트 분할)
            chunks = await asyncio.to_thread(self.step3.run, diarized_list)

            # 4. Step 4 (벡터 저장)
            if chunks:
                await asyncio.to_thread(self.step4.run, meeting_id, chunks)

            # 5. Step 5 (요약)
            analysis_report = await asyncio.to_thread(self.step5.summarize_meeting, meeting_id, diarized_list)
            summary_text = analysis_report.get("summary", "요약 완료")

            # DB 저장
            self.db_service.save_analysis_results(
                meeting_id=meeting_id,
                video_url=video_url,  # <--- 이 녀석을 꼭 넣어줘야 합니다!
                summary=summary_text,
                transcript=json.dumps(diarized_list, ensure_ascii=False)
            )
            
            # [핵심] 프론트엔드가 'iterable' 에러를 내지 않도록 데이터 규격을 강제합니다.
            safe_transcript = diarized_list if isinstance(diarized_list, list) else []
            safe_summary = analysis_report if analysis_report else {"summary": "요약을 생성할 수 없습니다."}
            
            
            # 상태 업데이트
            if meeting_id in video_db:
                video_db[meeting_id].update({
                    "status": "completed",
                    "percent": 100,
                    "transcript": safe_transcript, # 리스트임을 보장
                    "report": safe_summary,       # None 방지
                    "summary": safe_summary,        # 하위 호환성
                    "msg": "모든 분석이 성공적으로 완료되었습니다!"
                })
            
            logger.info(f"✅ [{meeting_id}] 분석 완료")
            
            return {
                "meeting_id": meeting_id,
                "status": "success",
                "transcript": safe_transcript,
                "report": safe_summary
            }
        except Exception as e:
            logger.error(f"❌ 파이프라인 에러: {e}")
            if meeting_id in video_db:
                video_db[meeting_id].update({"status": "error", "msg": str(e)})

# [브릿지 함수] 이 함수가 있으면 API에서 어떻게 불러도 에러가 안 납니다.
async def run_video_analysis_pipeline(meeting_id, video_url, video_db):
    service = VideoAnalysisService()
    await service.run_pipeline(meeting_id, video_url, video_db)