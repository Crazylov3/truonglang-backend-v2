from sqlalchemy import Column, String, ForeignKey, UniqueConstraint, Integer, text, Time, Enum as SQLAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from enum import Enum
from .base import BaseModel


class DayOfWeek(str, Enum):
    MONDAY = "MONDAY"
    TUESDAY = "TUESDAY"
    WEDNESDAY = "WEDNESDAY"
    THURSDAY = "THURSDAY"
    FRIDAY = "FRIDAY"
    SATURDAY = "SATURDAY"
    SUNDAY = "SUNDAY"


class Branch(BaseModel):
    __tablename__ = "branches"
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"), index=True)
    name = Column(String(255), unique=True, nullable=False, comment='Tên cơ sở, ví dụ: "Cơ sở Cầu Giấy"')
    address = Column(String(500), nullable=False)
    contact_info = Column(String(255), nullable=True)
    
    # Relationships
    rooms = relationship("Room", back_populates="branch")
    courses = relationship("Course", back_populates="branch")
    
    def __repr__(self):
        return f"<Branch(id={self.id}, name='{self.name}')>"


class Room(BaseModel):
    __tablename__ = "rooms"
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"), index=True)
    branch_id = Column(UUID(as_uuid=True), ForeignKey("branches.id"), nullable=False)
    room_number = Column(String(50), nullable=False, comment='Số phòng hoặc tên phòng, ví dụ: "P101"')
    capacity = Column(Integer, nullable=True)
    
    # Relationships
    branch = relationship("Branch", back_populates="rooms")
    course_schedules = relationship("CourseSchedule", back_populates="room")
    
    # Unique constraint
    __table_args__ = (
        UniqueConstraint('branch_id', 'room_number', name='unique_branch_room'),
    )
    
    def __repr__(self):
        return f"<Room(id={self.id}, branch_id={self.branch_id}, room_number='{self.room_number}')>"


class CourseSchedule(BaseModel):
    __tablename__ = "course_schedules"
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"), index=True)
    course_id = Column(UUID(as_uuid=True), ForeignKey("courses.id"), nullable=False)
    room_id = Column(UUID(as_uuid=True), ForeignKey("rooms.id"), nullable=False)
    day_of_week = Column(SQLAEnum(DayOfWeek), nullable=False)
    start_time = Column(Time, nullable=False, comment="e.g., 17:00:00")
    end_time = Column(Time, nullable=False, comment="e.g., 18:30:00")
    
    # Relationships
    course = relationship("Course", foreign_keys=[course_id])
    room = relationship("Room", back_populates="course_schedules")
    
    # Unique constraint - a course cannot be scheduled twice on the same day/time
    __table_args__ = (
        UniqueConstraint('course_id', 'day_of_week', 'start_time', name='unique_course_schedule'),
    )
    
    def __repr__(self):
        return f"<CourseSchedule(id={self.id}, course_id={self.course_id}, day={self.day_of_week}, time={self.start_time}-{self.end_time})>"