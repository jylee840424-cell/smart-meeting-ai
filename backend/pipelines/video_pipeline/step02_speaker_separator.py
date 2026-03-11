import os
import json
import re
import logging
from openai import OpenAI
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class SpeakerSeparator:
    def __init__(self, use_mock: bool = False):
        self.use_mock = use_mock
        # 환경 변수에서 키를 가져오거나 직접 설정된 키를 사용합니다.
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.client = OpenAI(api_key=self.api_key)

    def run(self, raw_transcript: Any) -> List[Dict[str, Any]]:
        # [결함 1 수정] Step 01의 반환값({"transcript_with_time": [...]}) 대응 로직
        if isinstance(raw_transcript, dict):
            logger.info("[Step 2] 딕셔너리 형태의 입력을 감지하여 데이터를 추출합니다.")
            raw_transcript = raw_transcript.get("transcript_with_time", [])

        if not raw_transcript:
            logger.warning("[Step 2] 전달받은 트랜스크립트 데이터가 비어있습니다.")
            return []

        # 기존 방어로직 유지: 텍스트 생성
        try:
            text_to_analyze = "\n".join([f"[{t['start']}s] {t['text']}" for t in raw_transcript])
        except (KeyError, TypeError) as e:
            logger.error(f"[Step 2] 데이터 파싱 에러: {e}")
            return []

        # ⭐ f-string 안의 중괄호를 {{ }}로 이중 처리하여 파이썬 문법 에러 방지 (기존 로직 유지)
        prompt = f"""
        # Role
        당신은 복잡한 다수 참여자 회의를 분석하고 화자를 식별하는 '언어 패턴 분석 전문가'입니다. 
        당신의 목표는 타임스탬프 데이터를 바탕으로 각 발화자가 누구인지 논리적으로 추론하여 완벽한 JSON 데이터를 생성하는 것입니다.

        # Speaker Identification Strategy
        1. **고유 식별자 부여**: 이름이 언급되지 않은 경우 '화자 A', '화자 B', '화자 C'와 같이 알파벳으로 구분하세요.
        2. **역할 파악**: 
        - 회의를 이끌거나 질문을 던지는 사람은 '진행자' 혹은 '의장'으로 명명.
        - 특정 주제에 대해 길게 설명하는 사람은 '발표자'로 명명.
        3. **일관성 유지**: 
        - 문장 사이의 연결성(A의 질문에 B가 답변)을 분석하여 동일 인물의 발화가 끊기더라도 같은 화자 ID를 유지하세요.
        - 말투(어미, 전문 용어 사용 빈도)와 대화의 맥락을 대조하여 화자를 검증하세요.
        4. **짧은 추임새 처리**: "네", "아 그렇군요", "확인했습니다"와 같은 짧은 발언도 앞뒤 맥락상 가장 적절한 화자에게 배정하세요.

        # Strict Constraints
        - **JSON Format Only**: 출력은 반드시 마크다운 코드 블록(```) 없이 순수 JSON 배열만 반환하세요.
        - **Data Integrity**: 제공된 'start' 시간과 'text' 내용은 0.1%도 수정하지 말고 그대로 유지하세요. 오직 'speaker' 필드만 당신이 추론하여 채웁니다.
        
        # Output Example (중괄호를 두 번 써서 에러 방지)
        [{{ "start": 1.25, "speaker": "화자 A", "text": "안녕하세요" }}, {{ "start": 5.4, "speaker": "진행자", "text": "반갑습니다" }}]

        # Input Data
        {text_to_analyze}

        # Final Output (Valid JSON Array)
        """

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0
            )
            
            content = response.choices[0].message.content.strip()
            
            # 마크다운 제거 로직 (기존 방어로직 유지)
            content = re.sub(r'```json|```', '', content).strip()
            
            # JSON 파싱 및 최종 결과 반환
            diarized_data = json.loads(content)
            logger.info(f"✅ [Step 2] 화자 분리 완료 ({len(diarized_data)} 문장)")
            return diarized_data

        except Exception as e:
            logger.error(f"❌ [Step 2] 화자 분리 중 오류 발생: {e}")
            return []