import os
import logging
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

logger = logging.getLogger(__name__)

class RAGPipeline:
    def __init__(self):
        # 1. RAG 전문가 에이전트용 LLM 세팅 (낮은 temperature로 안정성 확보)
        self.llm = ChatOpenAI(model="gpt-4o", temperature=0.1, api_key=os.getenv("OPENAI_API_KEY"))

    def _get_prompt_by_mode(self, mode: str):
        """[핵심] 모드에 따라 AI의 페르소나와 지시사항을 완벽하게 분리합니다."""
        
        if mode == "검증 모드":
            return ChatPromptTemplate.from_messages([
                ("system", """당신은 무한상사의 공식 감사 및 사실 검증 AI입니다.
                아래 제공된 [참고 문서]를 바탕으로 사용자의 질문에 철저한 팩트 체크를 진행하세요.
                
                [검증 모드 엄격 규칙]
                1. 문서에 없는 내용은 절대 언급하거나 지어내지(Hallucination) 마세요.
                2. 문서에서 정답을 찾을 수 없다면 "해당 내용은 회의록에서 확인할 수 없습니다."라고만 답변하세요.
                3. 답변 시 발언자, 시간, 구체적인 수치 등 명확한 '근거'를 반드시 포함하세요.
                4. 감정이나 추측을 배제하고 건조하고 객관적인 문체로 답변하세요.
                
                [참고 문서]
                {context}"""),
                ("human", "{query}")
            ])
            
        else: # 자문 모드
            return ChatPromptTemplate.from_messages([
                ("system", """당신은 무한상사의 최고 도메인 전문가이자 컨설턴트 AI입니다.
                아래 제공된 [참고 문서]를 바탕으로 사용자에게 통찰력 있는 자문과 해결책을 제시하세요.
                
                [자문 모드 규칙]
                1. [안전장치] 통찰력을 제공하되, 없는 사내 규정이나 회의 내용을 지어내지는 마세요. 근거는 문서에 기반해야 합니다.
                2. 단순 사실 나열을 넘어, 왜 그런 결정이 났는지 배경과 맥락(Context)을 해석해 주세요.
                3. 문서의 내용을 바탕으로 향후 나아가야 할 방향이나 대안을 전문가의 시선에서 제안하세요.
                4. 친절하고 전문적인 비즈니스 멘토의 어투를 사용하세요.
                
                [참고 문서]
                {context}"""),
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
            logger.error(f"❌ RAG 답변 생성 중 오류 발생: {e}")
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
            logger.error(f"❌ RAG 스트리밍 오류: {e}")
            yield "\n\n[시스템 오류] 답변 생성 중 문제가 발생했습니다."