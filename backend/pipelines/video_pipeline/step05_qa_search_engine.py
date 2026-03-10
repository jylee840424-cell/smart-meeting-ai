import os
import logging
from openai import OpenAI

logger = logging.getLogger(__name__)

class QASearchEngine:
    def __init__(self):
        # API 키 로드 및 클라이언트 초기화
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            logger.error("❌ OpenAI API Key가 설정되지 않았습니다.")
        self.client = OpenAI(api_key=self.api_key)

    def summarize_meeting(self, meeting_id: str, diarized_data: list):
        """회의 데이터를 요약하여 리포트를 생성합니다."""
        if not diarized_data:
            return {"summary": "요약할 데이터가 없습니다."}

        try:
            logger.info(f"📝 Step 05: 요약 시작 (ID: {meeting_id})")
            # 대화 텍스트 결합
            full_text = "\n".join([f"{d['speaker']}: {d['text']}" for d in diarized_data])
            
            # GPT 호출 (4o-mini 사용하여 비용 절감)
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "너는 회의록 요약 전문가야."},
                    {"role": "user", "content": f"다음 내용을 핵심 위주로 요약해줘:\n\n{full_text[:3500]}"}
                ],
                temperature=0.5
            )
            
            summary = response.choices[0].message.content
            return {"summary": summary}

        except Exception as e:
            logger.error(f"❌ Step 05 요약 중 오류 발생: {e}")
            return {"summary": f"요약 생성 실패: {str(e)}"}