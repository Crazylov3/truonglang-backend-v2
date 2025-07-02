from pydantic import BaseModel
from typing import List, Optional
from datetime import date


class AdminActivityEntry(BaseModel):
    id: int
    student_id: int
    course_id: int
    activity_date: date
    student_email: Optional[str] = None
    student_first_name: Optional[str] = None
    student_last_name: Optional[str] = None
    course_title: Optional[str] = None

    class Config:
        from_attributes = True


class GetAllActivityResponse(BaseModel):
    activities: List[AdminActivityEntry]
    total_count: Optional[int] = None 