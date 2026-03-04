import logging
import json
import os
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate

logger = logging.getLogger(__name__)

class QASearchEngine:
    def __init__(self, use_mock=False):
        self.use_mock = use_mock
        # 요약 작업은 빠르고 가성비 좋은 gpt-4o-mini 모델을 사용합니다.
        self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.2, api_key=os.getenv("OPENAI_API_KEY"))

    def summarize_meeting(self, meeting_id: str, transcript_data: list = None) -> dict:
        """분리된 스크립트 전체를 읽고 핵심 요약과 액션 아이템을 추출합니다."""
        logger.info(f"[Step 5] 미팅({meeting_id}) 진짜 LLM 구조화 요약 생성 중...")
        
        if self.use_mock or not transcript_data:
            return {"summary": "안전장치(Mock) 작동 중 또는 데이터가 없습니다.", "actions": []}
            
        # 화자가 분리된 배열 데이터를 텍스트로 예쁘게 묶어줍니다.
        full_text = "\n".join([f"[{d.get('time', '00:00')}] {d.get('speaker', 'Unknown')}: {d.get('text', '')}" for d in transcript_data])
        
        prompt = PromptTemplate(
            input_variables=["text"],
            template="""
            다음은 화자가 분리된 회의록 스크립트입니다. 
            이 회의의 핵심 결정 사항 1줄 요약과, 담당자가 수행해야 할 액션 아이템들을 추출해서 반드시 아래 JSON 포맷으로만 대답해주세요.
            
            [회의록]
            {text}
            
            [JSON 출력 포맷 (다른 말은 절대 하지 마세요)]
            {{
                "summary": "이 회의의 핵심 결론 1~2줄 요약",
                "actions": ["액션아이템 1", "액션아이템 2"]
            }}
            """
        )
        
        try:
            chain = prompt | self.llm
            response = chain.invoke({"text": full_text})
            
            clean_json_str = response.content.replace('```json', '').replace('```', '').strip()
            summary_data = json.loads(clean_json_str)
            
            logger.info("✅ 진짜 회의 요약 및 액션 아이템 추출 완료!")
            return summary_data
            
        except Exception as e:
            logger.error(f"❌ LLM 요약 중 오류 발생: {e}")
            return {"summary": "AI 요약 중 오류가 발생했습니다.", "actions": []}

    def ask_question(self, meeting_id: str, question: str) -> str:
        if self.use_mock:
            return "Mock 모드 답변입니다."
        return "RAG 엔진 답변 (추후 구현 예정)"