from pydantic import BaseModel, Field
from typing import List, Optional


class SummarySchema(BaseModel):
    display_text: str = Field(
        default="분석된 내용이 없습니다.", description="UI 출력용 통합 텍스트"
    )
    done: List[str] = Field(default_factory=list)
    will_do: List[str] = Field(default_factory=list)
    tbd: List[str] = Field(default_factory=list)


class ActionItem(BaseModel):
    Who: str = Field(default="미정", description="담당자명")
    What: str = Field(default="내용 없음", description="업무 내용")
    When: str = Field(default="-", description="기한")


class InsightsSchema(BaseModel):
    kpi: str = Field(default="-")
    risk_warning: str = Field(default="-")


class MeetingMeta(BaseModel):
    title: str = Field(default="알 수 없는 회의")


class MeetingReportResponse(BaseModel):
    meta: MeetingMeta
    joiner: str = Field(default="미지정")
    summary: SummarySchema
    actions: List[ActionItem] = Field(default_factory=list)
    insights: InsightsSchema
