from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import time
from uuid import UUID
from app.schemas.common import BaseUUIDModel, PaginatedResponse
from app.models.location import DayOfWeek


# Branch Schemas
class BranchBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255,
                      description="Branch name")
    address: str = Field(..., min_length=1, max_length=500,
                         description="Branch address")
    contact_info: Optional[str] = Field(
        None, max_length=255, description="Contact information")


class BranchCreate(BranchBase):
    pass


class BranchUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    address: Optional[str] = Field(None, min_length=1, max_length=500)
    contact_info: Optional[str] = Field(None, max_length=255)


class BranchResponse(BranchBase, BaseUUIDModel):
    class Config:
        from_attributes = True


BranchesListResponse = PaginatedResponse[BranchResponse]


# Room Schemas
class RoomBase(BaseModel):
    branch_id: UUID = Field(..., description="Branch ID")
    room_number: str = Field(..., min_length=1,
                             max_length=50, description="Room number")
    capacity: Optional[int] = Field(None, gt=0, description="Room capacity")


class RoomCreate(RoomBase):
    pass


class RoomUpdate(BaseModel):
    room_number: Optional[str] = Field(None, min_length=1, max_length=50)
    capacity: Optional[int] = Field(None, gt=0)


class RoomResponse(RoomBase, BaseUUIDModel):
    branch_name: Optional[str] = Field(None, description="Branch name")

    class Config:
        from_attributes = True


RoomsListResponse = PaginatedResponse[RoomResponse]


# Course Schedule Schemas
class CourseScheduleBase(BaseModel):
    course_id: UUID = Field(..., description="Course ID")
    room_id: UUID = Field(..., description="Room ID")
    day_of_week: DayOfWeek = Field(..., description="Day of the week")
    start_time: time = Field(..., description="Start time")
    end_time: time = Field(..., description="End time")


class CourseScheduleCreate(BaseModel):
    room_id: UUID = Field(..., description="Room ID")
    day_of_week: DayOfWeek = Field(..., description="Day of the week")
    start_time: time = Field(..., description="Start time")
    end_time: time = Field(..., description="End time")


class CourseScheduleUpdate(BaseModel):
    room_id: Optional[UUID] = None
    day_of_week: Optional[DayOfWeek] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None


class CourseScheduleResponse(CourseScheduleBase, BaseUUIDModel):
    course_title: Optional[str] = Field(None, description="Course title")
    room_number: Optional[str] = Field(None, description="Room number")
    branch_name: Optional[str] = Field(None, description="Branch name")

    class Config:
        from_attributes = True


class CourseSchedulesResponse(BaseModel):
    course_id: UUID
    schedules: List[CourseScheduleResponse]
    total: int


# Week Schedule View
class WeekScheduleItem(BaseModel):
    schedule_id: UUID
    course_id: UUID
    course_title: str
    room_number: str
    branch_name: str
    start_time: time
    end_time: time
    instructor_name: Optional[str] = None


class WeekScheduleResponse(BaseModel):
    monday: List[WeekScheduleItem] = Field(default_factory=list)
    tuesday: List[WeekScheduleItem] = Field(default_factory=list)
    wednesday: List[WeekScheduleItem] = Field(default_factory=list)
    thursday: List[WeekScheduleItem] = Field(default_factory=list)
    friday: List[WeekScheduleItem] = Field(default_factory=list)
    saturday: List[WeekScheduleItem] = Field(default_factory=list)
    sunday: List[WeekScheduleItem] = Field(default_factory=list)
