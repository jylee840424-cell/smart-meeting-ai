from pydantic import BaseModel, Field
from typing import List, Optional


class SummarySchema(BaseModel):
    # UI에서 바로 보여줄 줄바꿈(\n)이 포함된 통합 텍스트 (필수)
    display_text: str = Field(..., description="UI 출력용 통합 텍스트")
    # 데이터 분석이나 수정을 위한 원본 리스트들
    done: List[str] = Field(default_factory=list, description="수행 완료 항목")
    will_do: List[str] = Field(default_factory=list, description="예정 항목")
    tbd: List[str] = Field(default_factory=list, description="미정 항목")


class ActionItem(BaseModel):
    # 프론트엔드 액션플랜 테이블 규격에 맞춘 필수 키값
    Who: str = Field(..., description="담당자명")
    What: str = Field(..., description="업무 내용")
    When: str = Field(..., description="기한")


class InsightsSchema(BaseModel):
    kpi: str = Field(default="-", description="회의 KPI 지표")
    risk_warning: str = Field(default="-", description="잠재적 리스크(Risk Warning)")


class MeetingMeta(BaseModel):
    title: str = Field(..., description="회의 제목")


class MeetingReportResponse(BaseModel):
    meta: MeetingMeta
    joiner: str = Field(..., description="참석자 명단")
    summary: SummarySchema
    actions: List[ActionItem]
    insights: InsightsSchema
