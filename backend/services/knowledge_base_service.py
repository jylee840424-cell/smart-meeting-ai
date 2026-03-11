import os
import logging
from collections import OrderedDict
from pydantic import BaseModel, Field

# LangChain 및 OpenAI 관련 임포트
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import Chroma
from langchain_core.tools import StructuredTool
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory

# 로거 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ==========================================
# 1. 공통 유틸리티: 메모리 최적화를 위한 LRU 캐시
# ==========================================
class LRUCache(OrderedDict):
    def __init__(self, maxsize=50, *args, **kwds):
        self.maxsize = maxsize
        super().__init__(*args, **kwds)

    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        if len(self) > self.maxsize:
            self.popitem(last=False)

# ==========================================
# 2. 핵심 서비스: 벡터 DB 기반 회의록 검색기
# ==========================================
class KnowledgeBaseService:
    
    def __init__(
        self, 
        base_dir: str = None,
        embedding_model: str = "text-embedding-3-small",
        max_db_cache_size: int = 50
    ):
        # 1. 외부(chat_api.py)에서 명시적으로 최상위 루트 경로를 넘겨주면 최우선 사용!
        if base_dir:
            self.persist_directory = os.path.join(base_dir, "database", "vector")
        else:
            # 2. 만약 외부 주입이 없을 경우, 현재 파일(services) 기준 2단계 위(최상위 루트)를 계산
            current_dir = os.path.dirname(__file__)
            fallback_dir = os.path.abspath(os.path.join(current_dir, "..", ".."))
            self.persist_directory = os.path.join(fallback_dir, "database", "vector")
            
        # 경로가 잘 맞았는지 터미널에서 확인하기 위한 로그
        logger.info(f"📁 설정된 Vector DB 절대 경로: {self.persist_directory}")
            
        self.embedding_function = OpenAIEmbeddings(model=embedding_model)
        self._db_cache = LRUCache(maxsize=max_db_cache_size)

    def _get_or_load_db(self, meeting_id: str) -> Chroma:
        if meeting_id in self._db_cache:
            value = self._db_cache.pop(meeting_id)
            self._db_cache[meeting_id] = value
            return value
        
        db_path = os.path.join(self.persist_directory, meeting_id)
        if not os.path.exists(db_path):
            return None
            
        logger.info(f"🔄 [{meeting_id}] 디스크에서 벡터 DB를 최초 로드합니다.")
        vectorstore = Chroma(
            persist_directory=db_path, 
            embedding_function=self.embedding_function,
            collection_name="meeting_collection"  # 서랍장 이름 통일!
        )
        
        self._db_cache[meeting_id] = vectorstore
        return vectorstore

    def search_relevant_context(self, meeting_id: str, query: str, top_k: int = 3) -> str:
        try:
            vectorstore = self._get_or_load_db(meeting_id)
            if not vectorstore:
                return f"안내: '{meeting_id}'에 해당하는 회의록 데이터베이스를 찾을 수 없습니다."

            docs = vectorstore.similarity_search(query, k=top_k)
            
            if not docs:
                return "안내: 질문에 일치하는 문맥을 찾지 못했습니다."

            formatted_docs = []
            for doc in docs:
                source = doc.metadata.get("source", "출처 불명")
                page = doc.metadata.get("page", "확인 불가")
                formatted_docs.append(f"[문서 출처: {source}, 페이지: {page}p]\n{doc.page_content}")

            return "\n\n---\n\n".join(formatted_docs)

        except Exception as e:
            logger.error(f"❌ 벡터 DB 검색 중 오류 발생: {e}", exc_info=True)
            return "안내: 문서 검색 중 시스템 내부 오류가 발생했습니다."

# ==========================================
# 3. 에이전트 도구 생성기
# ==========================================
class SearchMeetingInput(BaseModel):
    meeting_id: str = Field(..., description="검색할 회의록의 고유 ID (예: 'meeting_1234')")
    query: str = Field(..., description="회의록에서 찾고자 하는 사용자의 질문이나 핵심 키워드")

def create_search_meeting_tool(kb_service: KnowledgeBaseService) -> StructuredTool:
    def search_meeting_records(meeting_id: str, query: str) -> str:
        return kb_service.search_relevant_context(meeting_id=meeting_id, query=query, top_k=3)

    return StructuredTool.from_function(
        func=search_meeting_records,
        name="search_meeting_records",
        description=(
            "사용자가 특정 회의록의 내용을 물어볼 때 이 도구를 사용하세요. "
            "회의록 ID와 질문을 입력하면, 관련된 실제 회의 내용과 출처를 반환합니다. "
            "답변을 생성할 때 반드시 이 도구가 반환한 내용을 기반으로 작성해야 합니다."
        ),
        args_schema=SearchMeetingInput
    )

# ==========================================
# 4. 에이전트 생성 팩토리 (메모리 캡슐화 적용)
# ==========================================
def build_production_agent(
    kb_service: KnowledgeBaseService, 
    model_name: str = "gpt-4o-mini", 
    temperature: float = 0.3,
    max_sessions: int = 1000
):
    """
    함수 내부에서 고유한 세션 저장소를 생성하여 캡슐화
    이렇게 하면 여러 에이전트를 만들어도 서로의 대화가 섞이지 않음
    """
    local_session_store = LRUCache(maxsize=max_sessions)

    def get_session_history(session_id: str) -> ChatMessageHistory:
        if session_id not in local_session_store:
            local_session_store[session_id] = ChatMessageHistory()
        return local_session_store[session_id]

    llm = ChatOpenAI(model=model_name, temperature=temperature)
    tools = [create_search_meeting_tool(kb_service)]
    
    system_prompt = """당신은 팀의 업무를 돕는 똑똑한 AI 파트너입니다.
    
    [현재 작동 모드 지시사항]
    {mode_instruction}
    
    [공통 행동 지침]
    1. 일상적인 인사나 가벼운 질문에는 검색 도구를 쓰지 말고 자연스럽게 대화하세요.
    2. '특정 회의', '과거 결정 사항', '기록'에 대한 질문은 반드시 `search_meeting_records` 도구를 사용하세요.
    3. 정보의 출처(페이지 등)가 있다면 괄호로 부드럽게 덧붙여 주세요.
    """
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        MessagesPlaceholder(variable_name="chat_history"),
        ("user", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])
    
    agent = create_tool_calling_agent(llm, tools, prompt)
    
    agent_executor = AgentExecutor(
        agent=agent, 
        tools=tools, 
        verbose=False, 
        handle_parsing_errors="도구의 결과를 처리하는 중 문제가 발생했습니다. 조금 다르게 다시 질문해 주시겠어요?", 
        max_iterations=3 
    )
    
    conversational_agent = RunnableWithMessageHistory(
        agent_executor,
        get_session_history,
        input_messages_key="input",
        history_messages_key="chat_history",
    )
    
    return conversational_agent

# ==========================================
# 5. 실행 및 테스트
# ==========================================
if __name__ == "__main__":
    # 실행 전 OPENAI_API_KEY가 환경변수에 설정되어 있어야 합니다.
    if "OPENAI_API_KEY" not in os.environ:
        logger.warning("⚠️ OPENAI_API_KEY 환경변수가 설정되지 않았습니다. 실행 전 확인해주세요.")

    print("🚀 Knowledge Base Agent 초기화 중...")
    
    # 설정값을 유연하게 주입하여 서비스 인스턴스 생성
    my_kb_service = KnowledgeBaseService(embedding_model="text-embedding-3-small")
    my_agent = build_production_agent(my_kb_service, model_name="gpt-4o-mini")
    
    config = {"configurable": {"session_id": "test_user_001"}}
    
    print("\n--- 봇 테스트 시작 (종료하려면 'quit' 입력) ---")
    while True:
        user_input = input("👤 사용자: ")
        if user_input.lower() in ['quit', 'exit', '종료']:
            break
            
        try:
            # [개선 3] 나중에 비동기 서버(FastAPI)로 전환할 때는 
            # response = await my_agent.ainvoke({"input": user_input}, config) 로 쉽게 변경 가능합니다.
            response = my_agent.invoke({"input": user_input}, config)
            print(f"🤖 에이전트: {response['output']}\n")
        except Exception as e:
            print(f"❌ 에러 발생: {e}\n")