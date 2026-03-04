from fastapi import APIRouter
import asyncio

router = APIRouter(prefix="/meetings", tags=["Meeting History"])

@router.get("/details/{meeting_id}")
async def get_meeting_details(meeting_id: str):
    """[Mock] 특정 회의의 AI 구조화 요약 및 액션 아이템 반환"""
    
    # DB 조회 및 AI 요약 로딩 시간 모방
    await asyncio.sleep(0.8)
    
    # 앞서 정의했던 api_spec.md의 구조와 완벽히 일치하는 응답 데이터
    return {
      "meta": {
          "title": meeting_id if meeting_id != "latest" else "주간 제품 전략 회의", 
          "department": "제품 개발본부", 
          "date": "2026-03-01", 
          "status": "완료"
      },
      "summary": {
        "purpose": "4분기 모바일 앱 리뉴얼 작업 범위 조율",
        "rag_context": "지난 2월 15일 마케팅 킥오프의 연장선상에 있는 회의이며, 과거 '제스처 네비게이션' 관련 UX 실패 사례를 참고하여 진행됨.",
        "discussions": [
            "디자인팀: 최신 트렌드에 맞춘 제스처 기반 네비게이션 전면 도입 제안",
            "엔지니어링팀: 기존 레거시 코드와의 호환성 및 개발 공수 문제 제기",
            "마케팅본부: 4분기 필수 출시 일정을 맞추는 것이 최우선 과제임을 강조"
        ],
        "pros": ["전반적인 UX 흐름 개선", "모던한 UI 확보로 20대 유저 어필"],
        "cons": ["단기 개발 공수 과부하", "4분기 필수 출시일 위협 리스크"]
      },
      "actions": [
        {
            "action_id": "ACT-1001", "title": "1단계 기술 스펙 업데이트", 
            "assignee": "김개발 책임", "department": "IT 개발본부", 
            "deadline": "2026-03-05", "status": "완료", "is_overdue": False
        },
        {
            "action_id": "ACT-1002", "title": "제스처 네비게이션 롤백 디자인 기획", 
            "assignee": "이디자인 선임", "department": "디자인팀", 
            "deadline": "2026-02-28", "status": "지연", "is_overdue": True
        }
      ],
      "insights": {
        "risk_warning": "단기 개발 공수 과부하로 인해 4분기 마케팅 런칭 방향성과 상충될 위험이 매우 높습니다. 경영진의 빠른 결단이 필요합니다."
      }
    }