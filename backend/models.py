from sqlalchemy import Column, Integer, String

from .database import Base


class CharacterCard(Base):
    __tablename__ = "character_cards"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    avatar_url = Column(String, nullable=True)
