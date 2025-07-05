from sqlalchemy import Column, Integer, String, Date, ForeignKey
from sqlalchemy.orm import relationship
from .base import BaseModel


class UserProfile(BaseModel):
    __tablename__ = "user_profiles"
    
    # Both Primary Key and Foreign Key
    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    
    # Basic Info
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    date_of_birth = Column(Date, nullable=True)

    # avatar
    avatar = Column(String(255), nullable=True)
    
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