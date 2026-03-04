import os
import logging
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
# [핵심 추가] LangChain이 요구하는 공식 규격 상자(Document) 임포트
from langchain_core.documents import Document 

logger = logging.getLogger(__name__)

class VectorEmbeddingProcessor:
    def __init__(self, use_mock=False):
        self.use_mock = use_mock
        
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
        self.persist_directory = os.path.join(base_dir, "database", "vector")
        
        # 사서와 완벽하게 동일한 모델 사용!
        self.embedding_function = OpenAIEmbeddings(model="text-embedding-3-small")

    def run(self, meeting_id: str, chunks: list):
        if self.use_mock:
            return True

        try:
            db_path = os.path.join(self.persist_directory, meeting_id)
            
            # =========================================================
            # [핵심 해결] 딕셔너리(dict)를 LangChain의 Document 객체로 변환
            # =========================================================
            langchain_docs = []
            for chunk in chunks:
                if isinstance(chunk, dict):
                    # 텍스트 추출
                    content = chunk.get("text", chunk.get("page_content", ""))
                    # 나머지 화자(speaker), 시간(time) 등의 정보는 메타데이터로 예쁘게 분류하여 저장
                    metadata = {str(k): str(v) for k, v in chunk.items() if k not in ["text", "page_content"]}
                    langchain_docs.append(Document(page_content=content, metadata=metadata))
                elif isinstance(chunk, str):
                    langchain_docs.append(Document(page_content=chunk))
                else:
                    # 이미 Document 객체인 경우 그냥 통과
                    langchain_docs.append(chunk)

            if not langchain_docs:
                raise ValueError("임베딩할 유효한 텍스트 데이터가 없습니다.")

            # 이제 오류 없이 벡터 DB에 저장됩니다!
            Chroma.from_documents(
                documents=langchain_docs,
                embedding=self.embedding_function,
                persist_directory=db_path
            )
            logger.info(f"✅ [Step 4] 벡터 DB 저장 완료 (경로: {db_path})")
            return True
            
        except Exception as e:
            logger.error(f"❌ 벡터 임베딩 중 오류 발생: {e}")
            raise Exception("벡터 DB 저장에 실패했습니다.")