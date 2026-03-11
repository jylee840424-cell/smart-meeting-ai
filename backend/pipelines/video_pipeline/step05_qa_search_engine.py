import os
import logging
import json
from openai import OpenAI

logger = logging.getLogger(__name__)

class QASearchEngine:
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.client = OpenAI(api_key=self.api_key)
        
        current_dir = os.path.dirname(os.path.abspath(__file__))
        self.base_dir = os.path.abspath(os.path.join(current_dir, "..", "..", ".."))
        self.backup_directory = os.path.join(self.base_dir, "database", "processed_text")
        os.makedirs(self.backup_directory, exist_ok=True)

    def _safe_join(self, data_list):
        """리스트 내의 dict 요소를 텍스트로 안전하게 변환 (에러 방지)"""
        if not isinstance(data_list, list): return str(data_list)
        processed = []
        for item in data_list:
            if isinstance(item, dict):
                processed.append(" ".join([str(v) for v in item.values()]))
            else:
                processed.append(str(item))
        return "\n".join(processed)

    def summarize_meeting(self, meeting_id: str, diarized_data: list):
        try:
            full_text = "\n".join([f"{d['speaker']}: {d['text']}" for d in diarized_data])
            
            # [3번 팀 스키마 완벽 반영 프롬프트]
            prompt = f"""
            당신은 회의 분석 전문가입니다. 반드시 아래 JSON 구조로만 응답하세요.
            
            1. meta: {{ "title": "회의 제목" }}
            2. summary: {{ 
                 "display_text": "전체 요약 문장", 
                 "done": ["결정사항1", "결정사항2"], 
                 "will_do": ["향후계획1"], 
                 "tbd": ["미결안건1"] 
               }}
            3. actions: [ {{ "Who": "담당자", "What": "할일", "When": "기한" }} ]
            4. insights: {{ "kpi": "지표", "risk_warning": "리스크" }}

            회의 내용:
            {full_text[-8000:]}
            """

            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "system", "content": "너는 MeetingReportResponse 규격을 준수하는 분석가야."},
                          {"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )

            report_content = json.loads(response.choices[0].message.content)

            # 3번 팀의 03_action_reports.py 및 meeting_api.py가 요구하는 최종 구조
            final_report = {
                "meeting_id": meeting_id,
                "meta": report_content.get("meta", {"title": f"회의_{meeting_id[:6]}"}),
                "joiner": "참석자 데이터 분석 중", # VideoService에서 사후 업데이트 권장
                "summary": report_content.get("summary", {}),
                "actions": report_content.get("actions", []),
                "insights": report_content.get("insights", {}),
                # 아래는 우리 내부 DB 저장 및 에러 방지용 보조 데이터
                "details": {
                    "done": self._safe_join(report_content.get("summary", {}).get("done", [])),
                    "tbd": self._safe_join(report_content.get("summary", {}).get("tbd", []))
                },
                "messages": diarized_data 
            }

            # 파일 저장
            save_path = os.path.join(self.backup_directory, f"{meeting_id}_report.json")
            with open(save_path, "w", encoding="utf-8") as f:
                json.dump(final_report, f, ensure_ascii=False, indent=4)
            
            return final_report

        except Exception as e:
            logger.error(f"❌ Step 05 통합 분석 오류: {e}")
            return {"error": str(e)}