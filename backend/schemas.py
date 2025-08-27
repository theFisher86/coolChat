from pydantic import BaseModel


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
