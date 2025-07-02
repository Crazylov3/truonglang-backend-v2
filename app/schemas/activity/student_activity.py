from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date
from app.schemas.users.user_info import UserInfo


class LogActivityRequest(BaseModel):
    course_id: int = Field(..., description="ID of the course to log activity for")


class LogActivityResponse(BaseModel):
    message: str
    date: date


class ActivityEntry(BaseModel):
    id: int
    student_id: int
    course_id: int
    activity_date: date
    course_title: Optional[str] = None

    class Config:
        from_attributes = True


class GetMyActivityResponse(BaseModel):
    activities: List[ActivityEntry]


class CourseActivitySummary(BaseModel):
    course_id: int
    course_title: str
    activity_days: int


class GetMyActivitySummaryResponse(BaseModel):
    period: str
    start_date: date
    end_date: date
    total_activity_days: int
    courses: List[CourseActivitySummary] 