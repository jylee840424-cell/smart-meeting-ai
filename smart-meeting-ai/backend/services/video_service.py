import asyncio
import logging
import traceback
import json
from services.database_service import DatabaseService

# ---------------------------------------------------------
# [AI 공장 부품 임포트]
# ---------------------------------------------------------
from pipelines.video_pipeline.step01_audio_to_text import AudioToTextProcessor
from pipelines.video_pipeline.step02_speaker_separator import SpeakerSeparator
from pipelines.video_pipeline.step03_text_splitter import TextSplitterProcessor
from pipelines.video_pipeline.step04_vector_embedding import VectorEmbeddingProcessor
from pipelines.video_pipeline.step05_qa_search_engine import QASearchEngine

logger = logging.getLogger(__name__)

async def run_video_analysis_pipeline(meeting_id: str, video_url: str, video_db: dict):
    """
    [Real AI 파이프라인 오케스트레이터]
    가짜 모드를 끄고 실제 OpenAI 모델을 사용하며, 각 단계마다 강력한 데이터 검증(Guardrail)을 수행합니다.
    """
    try:
        use_mock = False 
        
        audio_processor = AudioToTextProcessor(use_mock=use_mock)
        speaker_separator = SpeakerSeparator(use_mock=use_mock)
        text_splitter = TextSplitterProcessor(use_mock=use_mock)
        vector_embedder = VectorEmbeddingProcessor(use_mock=use_mock)
        qa_engine = QASearchEngine(use_mock=use_mock)

        # ---------------------------------------------------------
        # [Step 1] 유튜브 음성 추출 및 텍스트 변환 (Whisper STT)
        # ---------------------------------------------------------
        video_db[meeting_id].update({"current_step": 2, "percent": 15, "msg": "유튜브 영상에서 오디오를 추출하고 진짜 텍스트로 변환 중입니다...", "time_left": "약 3분 45초"})
        await asyncio.sleep(1.0) 
        
        raw_text = audio_processor.run(video_url)

        # 🛡️ [가드레일 1] 텍스트가 정상적으로 추출되었는지 품질 검사
        if not raw_text or len(raw_text.strip()) < 5:
            raise ValueError("영상에서 추출된 유효한 음성/대화 데이터가 없습니다. (음악만 있거나 추출이 차단된 영상일 수 있습니다.)")

        # ---------------------------------------------------------
        # [Step 2] 화자 분리 (GPT-4o Semantic Diarization)
        # ---------------------------------------------------------
        video_db[meeting_id].update({"percent": 35, "msg": "참석자 목소리와 문맥을 분석하여 진짜 화자를 분리하고 있습니다...", "time_left": "약 2분 30초"})
        await asyncio.sleep(1.0)
        
        diarized_data = speaker_separator.run(raw_text)

        # 🛡️ [가드레일 2] 화자 분리가 소설(환각) 없이 제대로 되었는지 품질 검사
        if not diarized_data or (len(diarized_data) == 1 and "System" in diarized_data[0].get("speaker", "")):
            raise ValueError("대화 문맥을 분석할 수 없어 화자 분리에 실패했습니다. 정상적인 회의 영상인지 확인해주세요.")

        # ---------------------------------------------------------
        # [Step 3] 텍스트 분할 (LangChain Chunking)
        # ---------------------------------------------------------
        video_db[meeting_id].update({"current_step": 3, "percent": 55, "msg": "텍스트를 AI가 이해할 수 있는 단위로 분할 중입니다...", "time_left": "약 1분 45초"})
        await asyncio.sleep(1.0)
        
        chunks = text_splitter.run(diarized_data)

        # ---------------------------------------------------------
        # [Step 4] 벡터 DB 임베딩 및 저장 (ChromaDB)
        # ---------------------------------------------------------
        video_db[meeting_id].update({"current_step": 4, "percent": 75, "msg": "분할된 텍스트를 벡터 DB(Chroma)에 저장 중입니다...", "time_left": "약 40초"})
        await asyncio.sleep(1.0)
        
        vector_embedder.run(meeting_id, chunks)

        # ---------------------------------------------------------
        # [Step 5] LLM 구조화 요약 및 액션 아이템 추출
        # ---------------------------------------------------------
        video_db[meeting_id].update({"current_step": 5, "percent": 90, "msg": "LLM을 활용해 진짜 회의 요약 및 액션 아이템을 생성 중입니다...", "time_left": "마무리 중"})
        await asyncio.sleep(1.0)
        
        summary_data = qa_engine.summarize_meeting(meeting_id, transcript_data=diarized_data)

        # ---------------------------------------------------------
        # [DB 저장] 사내 DB에 최종 결과물 영구 저장
        # ---------------------------------------------------------
        video_db[meeting_id].update({"msg": "분석 결과를 사내 데이터베이스(governance.db)에 안전하게 저장 중입니다..."})
        
        db_service = DatabaseService()
        transcript_str = json.dumps(diarized_data, ensure_ascii=False)
        summary_str = json.dumps(summary_data, ensure_ascii=False)
        
        db_service.save_analysis_results(meeting_id, summary_str, transcript_str)

        # ---------------------------------------------------------
        # [최종 완료] 프론트엔드에 완료 신호 전송
        # ---------------------------------------------------------
        video_db[meeting_id].update({
            "status": "completed", 
            "percent": 100, 
            "msg": "AI 분석 및 구조화 요약이 모두 완료되었습니다.", 
            "time_left": "완료",
            "transcript": diarized_data,  
            "summary": summary_data       
        })
        logger.info(f"✅ [{meeting_id}] 진짜 AI 분석 파이프라인 완벽 가동 종료!")
        
    except ValueError as ve:
        # 가드레일에 걸린 명확한 에러는 사용자에게 친절하게 보여줍니다.
        logger.warning(f"⚠️ 파이프라인 중단 (데이터 불량): {ve}")
        video_db[meeting_id].update({
            "status": "error",
            "msg": f"분석 중단: {str(ve)}",
            "percent": 0
        })
    except Exception as e:
        # 예상치 못한 시스템 에러
        error_msg = traceback.format_exc()
        logger.error(f"❌ 파이프라인 실행 중 시스템 오류 발생: {error_msg}")
        video_db[meeting_id].update({
            "status": "error",
            "msg": f"시스템 오류가 발생했습니다: {str(e)}",
            "percent": 0
        })