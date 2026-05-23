"""Models for rikishi data."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_serializer
from zoneinfo import ZoneInfo


class Rikishi(BaseModel):
    """Model representing a sumo wrestler."""

    model_config = ConfigDict(populate_by_name=True)

    id: int
    sumodb_id: int = Field(alias="sumodbId")
    nsk_id: Optional[int] = Field(alias="nskId", default=0)
    shikona_en: str = Field(alias="shikonaEn")
    shikona_jp: Optional[str] = Field(alias="shikonaJp", default="")
    current_rank: Optional[str] = Field(alias="currentRank", default="")
    heya: str
    birth_date: datetime = Field(alias="birthDate")
    shusshin: str
    height: int
    weight: int
    debut: str
    intai: Optional[datetime] = None
    updated_at: Optional[datetime] = Field(alias="updatedAt", default=None)

    @field_serializer("birth_date", "intai", "updated_at")
    def _serialize_dt(self, v: datetime) -> str:
        return v.astimezone(ZoneInfo("UTC")).isoformat()


class RikishiList(BaseModel):
    """Model representing a list of rikishi with pagination."""

    model_config = ConfigDict(populate_by_name=True)

    limit: int
    skip: int
    total: int
    records: List[Rikishi]
