"""Models for basho data."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class RikishiPrize(BaseModel):
    """Model representing a rikishi who won a prize."""

    type: str
    rikishi_id: int = Field(alias="rikishiId")
    shikona_en: str = Field(alias="shikonaEn")
    shikona_jp: str = Field(alias="shikonaJp")


class Basho(BaseModel):
    """Model representing a basho tournament.

    Note: location, yusho, and special_prizes are only present after
    the tournament concludes. During an ongoing basho the API returns
    only date, startDate, and endDate.
    """

    date: str  # YYYYMM format
    location: Optional[str] = None
    start_date: datetime = Field(alias="startDate")
    end_date: datetime = Field(alias="endDate")
    yusho: Optional[List[RikishiPrize]] = None
    special_prizes: Optional[List[RikishiPrize]] = Field(
        default=None, alias="specialPrizes"
    )
