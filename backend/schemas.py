from pydantic import BaseModel
from datetime import datetime


class CharacterCardBase(BaseModel):
    name: str
    description: str | None = None
    avatar_url: str | None = None


class CharacterCardCreate(CharacterCardBase):
    pass


class CharacterCard(CharacterCardBase):
    id: int

    class Config:
        orm_mode = True


class CircuitBase(BaseModel):
    name: str
    description: str | None = None
    data: dict


class CircuitCreate(CircuitBase):
    pass


class Circuit(CircuitBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True
