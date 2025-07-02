from sqlalchemy import Column, Integer, String, Text, Date, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from .base import BaseModel


class UserProfile(BaseModel):
    __tablename__ = "user_profiles"
    
    # Both Primary Key and Foreign Key
    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    
    # Basic Info
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    display_name = Column(String(100), nullable=True, comment="Publicly visible name. Can default to first_name + last_name")
    date_of_birth = Column(Date, nullable=True)
    
    # Rich Profile Info
    headline = Column(String(255), nullable=True, comment='A short, one-line bio. e.g., "Full-Stack Developer | Lifelong Learner"')
    bio = Column(Text, nullable=True)
    avatar_url = Column(String(255), nullable=True, comment="URL to the user profile image")
    
    # Location & Localization
    location = Column(String(100), nullable=True, comment='e.g., "San Francisco, CA"')
    language = Column(String(10), default="en-US", comment="Preferred language for the UI (e.g., en-US, es-ES)")
    timezone = Column(String(50), default="UTC", comment='Important for displaying deadlines correctly (e.g., "America/New_York")')
    
    # Social & Professional Links
    website_url = Column(String(255), nullable=True)
    linkedin_url = Column(String(255), nullable=True)
    twitter_handle = Column(String(50), nullable=True, comment="Store just the handle, not the full URL")
    github_url = Column(String(255), nullable=True)
    
    # Timestamps
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="profile")

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def public_name(self):
        return self.display_name if self.display_name else self.full_name

    def __repr__(self):
        return f"<UserProfile(user_id={self.user_id}, name='{self.full_name}')>" 