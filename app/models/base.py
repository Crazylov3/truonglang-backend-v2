from app.database import Base as DatabaseBase


class BaseModel(DatabaseBase):
    __abstract__ = True
    