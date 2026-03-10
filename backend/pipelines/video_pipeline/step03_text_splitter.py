import logging
import os
from dotenv import load_dotenv
from typing import List, Dict, Any

# 1. .env 경로 잡기 (1, 2번과 동일하게 유지하여 통일성 확보)
current_dir = os.path.dirname(os.path.abspath(__file__))
dotenv_path = os.path.normpath(os.path.join(current_dir, "../../../.env"))
load_dotenv(dotenv_path)

logger = logging.getLogger(__name__)

class TextSplitterProcessor:
    def __init__(self, chunk_size=800, chunk_overlap=100, use_mock=False):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.use_mock = use_mock

    def run(self, diarized_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """화자 정보를 유지하면서 RAG 최적화 크기로 텍스트를 자릅니다."""
        logger.info(f"[Step 3] 회의 맥락을 유지하며 텍스트 분할(Chunking) 중... (크기: {self.chunk_size})")
        
        # 1. 화자 분리된 데이터를 '대화록' 형태로 예쁘게 합치기
        full_document = "\n".join([
            f"[{d.get('time', '00:00')}] {d.get('speaker', '알 수 없음')}: {d.get('text', '')}" 
            for d in diarized_data
        ])
        
        if self.use_mock:
            logger.warning("⚠️ Mock 모드: 텍스트를 자르지 않고 통째로 반환합니다.")
            return [{"page_content": full_document, "metadata": {"source": "meeting_mock"}}]

        try:
            # 2. LangChain의 스플리터 사용
            from langchain_text_splitters import RecursiveCharacterTextSplitter
            
            # 줄바꿈과 문장 부호를 기준으로 자르는 이 설정은 아주 좋습니다!
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap,
                separators=["\n\n", "\n", ". ", "? ", "! ", " ", ""] 
            )
            
            # 문서를 자르고 메타데이터 심기
            chunks = text_splitter.create_documents(
                [full_document], 
                metadatas=[{"source": "meeting_transcript", "type": "speech_to_text"}]
            )
            
            logger.info(f"✅ 분할 완료: {len(chunks)}개의 청크(Chunk) 생성됨.")
            
            # 4번 단계(벡터 저장)에서 사용하기 편한 리스트 형태로 반환
            return [{"page_content": c.page_content, "metadata": c.metadata} for c in chunks]

        except ImportError:
            logger.error("❌ langchain-text-splitters 패키지가 없습니다. 'pip install langchain-text-splitters'가 필요합니다.")
            return [{"page_content": full_document, "metadata": {"error": "import_fail"}}]