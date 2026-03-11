import os
import logging
from langchain_openai import ChatOpenAI
from core.prompts import RAG_SYSTEM_PROMPTS
from langchain_core.prompts import ChatPromptTemplate

logger = logging.getLogger(__name__)

class RAGPipeline:
    def __init__(self):
        # 1. RAG 전문가 에이전트용 LLM 세팅 (낮은 temperature로 안정성 확보)
        self.llm = ChatOpenAI(model="gpt-4o", temperature=0.1, api_key=os.getenv("OPENAI_API_KEY"))

    def _get_prompt_by_mode(self, mode: str):
        """[수정됨] core.prompts에서 프롬프트를 가져와 LangChain 템플릿으로 변환합니다."""
        
        mode_key = "검증" if mode in ["검증", "verification", "검증 모드"] else "자문"
        system_prompt_text = RAG_SYSTEM_PROMPTS.get(mode_key)
        
        return ChatPromptTemplate.from_messages([
            ("system", system_prompt_text),
            ("human", "{query}")
        ])
                

    def generate_answer(self, query: str, context: str, mode: str = "검증 모드") -> str:
        """[단일 응답용] 질문에 대한 전체 답변을 한 번에 생성하여 반환합니다. (보고서 추출 등에 활용)"""
        logger.info(f"🧠 RAG 파이프라인 ({mode}): LLM 단일 답변 생성 가동 중...")
        
        if not context or context.strip() == "":
            return "관련된 회의록 데이터를 찾을 수 없어 답변을 드릴 수 없습니다."

        try:
            dynamic_prompt = self._get_prompt_by_mode(mode)
            chain = dynamic_prompt | self.llm
            response = chain.invoke({"context": context, "query": query})
            
            logger.info("✅ RAG 파이프라인: 성공적으로 답변을 생성했습니다.")
            return response.content

        except Exception as e:
            logger.error(f" RAG 답변 생성 중 오류 발생: {e}")
            return "죄송합니다. 답변을 생성하는 도중 AI 시스템에 오류가 발생했습니다."

    async def stream_answer(self, query: str, context: str, mode: str = "검증 모드"):
        """[스트리밍용] 모드에 맞는 답변을 단어 단위로 쪼개서 비동기적으로 뱉어냅니다."""
        if not context or context.strip() == "":
            yield "관련된 회의록 데이터를 찾을 수 없어 답변을 드릴 수 없습니다."
            return

        try:
            # 2. 요청받은 모드(검증/자문)에 맞는 프롬프트 장착
            dynamic_prompt = self._get_prompt_by_mode(mode)
            chain = dynamic_prompt | self.llm
            
            # 3. 실시간 텍스트 스트리밍 전송
            async for chunk in chain.astream({"context": context, "query": query}):
                if chunk.content:
                    yield chunk.content
                    
        except Exception as e:
            logger.error(f" RAG 스트리밍 오류: {e}")
            yield "\n\n[시스템 오류] 답변 생성 중 문제가 발생했습니다."