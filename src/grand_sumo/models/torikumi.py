"""Models for the torikumi endpoint."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from grand_sumo.models.match import Match


class YushoWinner(BaseModel):
    """Model for a yusho winner."""

    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(..., description="Rikishi ID")
    shikona_en: str = Field(
        ..., alias="shikonaEn", description="Rikishi's English shikona"
    )
    shikona_jp: str = Field(
        ..., alias="shikonaJp", description="Rikishi's Japanese shikona"
    )
    rank: str = Field(..., description="Rikishi's rank")
    record: str = Field(..., description="Rikishi's record in the basho")


class SpecialPrize(BaseModel):
    """Model for a special prize winner."""

    model_config = ConfigDict(populate_by_name=True)

    type: str = Field(..., description="Prize type")
    rikishi_id: str = Field(..., alias="rikishiId", description="Rikishi's ID")
    shikona_en: str = Field(
        ..., alias="shikonaEn", description="Rikishi's English shikona"
    )
    shikona_jp: str = Field(
        ..., alias="shikonaJp", description="Rikishi's Japanese shikona"
    )


class Torikumi(BaseModel):
    """Model for the torikumi response."""

    model_config = ConfigDict(populate_by_name=True)

    basho_id: str = Field(..., alias="bashoId", description="Basho ID in YYYYMM format")
    division: str = Field(..., description="Division name")
    day: int = Field(..., description="Day of the tournament (1-15)")
    matches: List[Match] = Field(..., description="List of matches for the day")
    yusho_winners: Optional[List[YushoWinner]] = Field(
        None, alias="yushoWinners", description="List of yusho winners"
    )
    special_prizes: Optional[List[SpecialPrize]] = Field(
        default_factory=list, alias="specialPrizes", description="List of special prize winners"
    )
    date: Optional[str] = Field(None, description="Basho date in YYYYMM format")
    location: Optional[str] = Field(None, description="Tournament location")
    start_date: Optional[datetime] = Field(
        None, alias="startDate", description="Tournament start date"
    )
    end_date: Optional[datetime] = Field(None, alias="endDate", description="Tournament end date")

    @model_validator(mode="before")
    @classmethod
    def extract_matches(cls, data: dict) -> dict:
        """Extract matches from the torikumi field."""
        if "torikumi" in data:
            data["matches"] = data.pop("torikumi")
        return data
