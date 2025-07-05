from pydantic import BaseModel
from datetime import datetime
from app.models.payment import PaymentStatus
from app.schemas.common import PaginatedResponse


class PaymentInfoResponse(BaseModel):
    id: int
    user_id: int
    course_id: int
    amount: float
    status: PaymentStatus
    created_at: datetime

    class Config:
        from_attributes = True


class PaymentListResponse(PaginatedResponse[PaymentInfoResponse]):
    """Paginated response for payments."""
    pass