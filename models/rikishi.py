"""Models for rikishi data."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field
from zoneinfo import ZoneInfo


class Rikishi(BaseModel):
    """Model representing a sumo wrestler."""

    model_config = ConfigDict(
        populate_by_name=True,
        json_encoders={datetime: lambda dt: dt.astimezone(ZoneInfo("UTC")).isoformat()},
    )

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


class RikishiList(BaseModel):
    """Model representing a list of rikishi with pagination."""

    model_config = ConfigDict(
        populate_by_name=True,
        json_encoders={datetime: lambda dt: dt.astimezone(ZoneInfo("UTC")).isoformat()},
    )

    limit: int
    skip: int
    total: int
    records: List[Rikishi]
