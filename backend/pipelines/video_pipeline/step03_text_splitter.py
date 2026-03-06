import logging

logger = logging.getLogger(__name__)

class TextSplitterProcessor:
    def __init__(self, chunk_size=500, chunk_overlap=50, use_mock=True):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.use_mock = use_mock

    def run(self, diarized_data: list) -> list:
        """화자가 분리된 데이터를 LangChain을 활용해 적절한 크기로 자릅니다(Chunking)."""
        logger.info("[Step 3] RAG를 위한 텍스트 분할(Chunking) 진행 중...")
        
        # 화자가 분리된 텍스트를 다시 하나의 문서 형태로 조합
        full_document = "\n".join([f"[{d['time']}] {d['speaker']}: {d['text']}" for d in diarized_data])
        
        if self.use_mock:
            return [{"page_content": full_document, "metadata": {"source": "meeting"}}]

        # [실제 프로덕션 코드 예시] LangChain 활용
        try:
            from langchain_text_splitters import RecursiveCharacterTextSplitter
            
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap,
                separators=["\n\n", "\n", ".", " ", ""]
            )
            chunks = text_splitter.create_documents([full_document])
            return [{"page_content": c.page_content, "metadata": c.metadata} for c in chunks]
        except ImportError:
            logger.error("langchain 패키지가 설치되지 않아 원본 텍스트를 그대로 반환합니다.")
            return [{"page_content": full_document, "metadata": {}}]