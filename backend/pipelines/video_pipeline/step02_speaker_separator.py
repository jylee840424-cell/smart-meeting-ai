import os
import json
import re
import logging
from openai import OpenAI
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class SpeakerSeparator:
    def __init__(self):
        # 환경 변수에서 키를 가져오거나 직접 설정된 키를 사용합니다.
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.client = OpenAI(api_key=self.api_key)

    def run(self, raw_transcript: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not raw_transcript:
            return []

        # 텍스트가 너무 길면 GPT가 힘들어하므로 상위 50개 문장만 예시로 처리하거나 조절 가능
        text_to_analyze = "\n".join([f"[{t['start']}s] {t['text']}" for t in raw_transcript])

        # ⭐ f-string 안의 중괄호를 {{ }}로 이중 처리하여 파이썬 문법 에러 방지
        prompt = f"""
        당신은 회의록 분석 전문가입니다. 아래 대화 내용을 분석하여 '발표자 A', '참석자 B' 등으로 화자를 구분해 주세요.
        반드시 아래의 JSON 배열 형식으로만 답변하세요.
        
        형식 예시: [{{ "start": 0.0, "speaker": "발표자 A", "text": "안녕하세요" }}]

        내용:
        {text_to_analyze}
        """

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",  # 가성비 좋은 모델 사용
                messages=[{"role": "user", "content": prompt}],
                temperature=0
            )
            
            content = response.choices[0].message.content.strip()
            
            # 마크다운 제거 로직 (GPT가 ```json 이라고 붙여주는 경우 대비)
            content = re.sub(r'```json|```', '', content).strip()
            
            # JSON 파싱
            match = re.search(r'\[.*\]', content, re.DOTALL)
            if match:
                return json.loads(match.group(0))
            else:
                return json.loads(content)

        except Exception as e:
            logger.error(f"❌ Step 2 화자 분리 실패: {e}")
            # 실패 시 원본이라도 유지해서 다음 단계(저장)로 넘어가게 함
            return [{"start": t.get("start", 0), "speaker": "Unknown", "text": t.get("text", "")} for t in raw_transcript]