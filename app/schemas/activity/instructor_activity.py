from pydantic import BaseModel
from typing import List, Optional
from datetime import date
from app.schemas.activity.student_activity import ActivityEntry


class StudentActivityEntry(BaseModel):
    id: int
    student_id: int
    course_id: int
    activity_date: date
    student_email: Optional[str] = None
    student_first_name: Optional[str] = None
    student_last_name: Optional[str] = None

    class Config:
        from_attributes = True


class GetCourseActivityResponse(BaseModel):
    activities: List[StudentActivityEntry]


class StudentSummary(BaseModel):
    student_id: int
    email: str
    activity_days: int


class DailyActivity(BaseModel):
    date: date
    active_students: int


class GetCourseActivitySummaryResponse(BaseModel):
    course_id: int
    course_title: str
    period: str
    start_date: date
    end_date: date
    total_unique_active_students: int
    total_activity_entries: int
    students: List[StudentSummary]
    daily_activity: List[DailyActivity] 