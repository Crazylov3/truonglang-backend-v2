from sqlalchemy import Column, String, Date, ForeignKey, DECIMAL
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from .base import BaseModel


class UserProfile(BaseModel):
    __tablename__ = "user_profiles"
    
    # Both Primary Key and Foreign Key
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True)
    
    # Basic Info
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    date_of_birth = Column(Date, nullable=True)
    
    # Avatar
    avatar = Column(String(255), nullable=True)
    
    # School Info
    current_school = Column(String(255), nullable=True, comment="Trường học sinh đang theo học")
    current_grade = Column(String(50), nullable=True, comment="Lớp chính khóa của học sinh (vd: 10A1)")
    
    # Discount
    default_discount_percentage = Column(DECIMAL(5, 2), nullable=True, default=0, comment="Mức giảm giá mặc định từ trung tâm cho học sinh này")
    
    # Relationships
    user = relationship("User", back_populates="profile")

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def public_name(self):
        return self.full_name

    def __repr__(self):
        return f"<UserProfile(user_id={self.user_id}, name='{self.full_name}')>" 