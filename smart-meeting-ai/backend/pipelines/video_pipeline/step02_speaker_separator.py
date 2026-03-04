import logging
import json
import os
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate

logger = logging.getLogger(__name__)

class SpeakerSeparator:
    def __init__(self, use_mock=False):
        self.use_mock = use_mock
        self.llm = ChatOpenAI(model="gpt-4o", temperature=0.0, api_key=os.getenv("OPENAI_API_KEY"))

    def run(self, raw_text: str) -> list:
        logger.info("[Step 2] AI 에이전트 기반 진짜 화자 분리 가동 중...")

        if self.use_mock:
            return [{"speaker": "System", "time": "00:00", "text": "Mock Mode가 켜져 있습니다."}]

        prompt = PromptTemplate(
            input_variables=["text"],
            template="""
            당신은 세계 최고의 회의 대화 분석 AI 에이전트입니다.
            아래의 텍스트를 분석하여 화자를 분리해 주세요.

            [엄격한 규칙]
            1. 원본 텍스트의 내용은 절대 누락하거나 지어내지(Hallucination) 말고 100% 반영하세요.
            2. 반드시 아래의 JSON 배열(Array) 포맷으로만 출력하세요.
            3. [매우 중요] 만약 입력 텍스트가 에러 메시지이거나, 너무 짧거나, 정상적인 대화가 아니라면 절대로 가상의 회의 내용을 지어내지 마세요! 그럴 경우 반드시 [{{"speaker": "System", "time": "00:00", "text": "정상적인 대화 스크립트를 추출하지 못했습니다."}}] 라고만 출력하세요.

            [입력 텍스트]
            {text}
            """
        )

        try:
            chain = prompt | self.llm
            response = chain.invoke({"text": raw_text})

            clean_json_str = response.content.replace('```json', '').replace('```', '').strip()
            return json.loads(clean_json_str)

        except Exception as e:
            logger.error(f"❌ 화자 분리 AI 처리 중 오류 발생: {e}")
            raise Exception("화자 분리 중 구조화(JSON)에 실패했습니다.")