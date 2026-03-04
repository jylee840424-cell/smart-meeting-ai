import os
import logging
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma

logger = logging.getLogger(__name__)

class KnowledgeBaseService:
    def __init__(self):
        # 1. [핵심 개선] 어떤 환경에서 실행하든 무조건 프로젝트 최상단의 database/vector를 찾도록 절대 경로화
        # 현재 위치(services) -> backend -> 최상단
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        self.persist_directory = os.path.join(base_dir, "database", "vector")
        
        # 2. [핵심 개선] 저장과 검색의 씽크를 맞추기 위해 가장 가성비 좋고 성능이 뛰어난 모델로 명시!
        self.embedding_function = OpenAIEmbeddings(model="text-embedding-3-small")

    def search_relevant_context(self, meeting_id: str, query: str, top_k: int = 3) -> str:
        """
        [RAG 검색 핵심 로직] 특정 회의록의 벡터 DB 방에서 유사 문서를 찾아옵니다.
        """
        try:
            db_path = os.path.join(self.persist_directory, meeting_id)
            
            # 3. 방어 로직 (경로 확인)
            if not os.path.exists(db_path):
                logger.warning(f"⚠️ [{meeting_id}] 벡터 DB 폴더가 없습니다: {db_path}")
                return ""

            # 4. 저장된 Chroma DB 로드
            vectorstore = Chroma(
                persist_directory=db_path, 
                embedding_function=self.embedding_function
            )

            # 5. 질문과 가장 비슷한 조각들을 검색
            docs = vectorstore.similarity_search(query, k=top_k)
            
            if not docs:
                logger.warning(f"⚠️ [{meeting_id}] 질문에 일치하는 문맥을 DB에서 찾지 못했습니다.")
                return ""

            # 6. 문맥 병합
            context_text = "\n\n---\n\n".join([doc.page_content for doc in docs])
            logger.info(f"✅ [{meeting_id}] 관련 문맥 {len(docs)}개 검색 완료 (DB 경로: {db_path})")
            
            return context_text

        except Exception as e:
            logger.error(f"❌ 벡터 DB 검색 중 오류 발생: {e}")
            return ""