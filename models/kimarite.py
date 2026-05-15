from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class KimariteRecord(BaseModel):
    """Model for a single kimarite record."""

    count: int = Field(..., description="Number of times this kimarite has been used")
    last_usage: str = Field(
        ...,
        alias="lastUsage",
        description="Last basho and day this kimarite was used (format: YYYYMM-DD)",
    )
    kimarite: str = Field(..., description="Name of the kimarite")


class KimariteResponse(BaseModel):
    """Model for the kimarite endpoint response."""

    limit: Optional[int] = Field(None, description="Number of records to return")
    skip: Optional[int] = Field(0, description="Number of records to skip")
    sort_field: Optional[str] = Field(
        None, alias="sortField", description="Field to sort by"
    )
    sort_order: Optional[Literal["asc", "desc"]] = Field(
        "asc", alias="sortOrder", description="Sort order"
    )
    records: List[KimariteRecord] = Field(..., description="List of kimarite records")


class KimariteMatch(BaseModel):
    """Model for a single match where a kimarite was used."""

    id: str = Field(
        ..., description="Match ID in format YYYYMM-day-matchNo-eastId-westId"
    )
    basho_id: str = Field(..., alias="bashoId", description="Basho ID in YYYYMM format")
    division: str = Field(..., description="Division name")
    day: int = Field(..., description="Day of the tournament (1-15)")
    match_no: int = Field(..., alias="matchNo", description="Match number for the day")
    east_id: int = Field(..., alias="eastId", description="East rikishi's ID")
    east_shikona: str = Field(
        ..., alias="eastShikona", description="East rikishi's shikona"
    )
    east_rank: str = Field(..., alias="eastRank", description="East rikishi's rank")
    west_id: int = Field(..., alias="westId", description="West rikishi's ID")
    west_shikona: str = Field(
        ..., alias="westShikona", description="West rikishi's shikona"
    )
    west_rank: str = Field(..., alias="westRank", description="West rikishi's rank")
    kimarite: str = Field(..., description="Winning technique used")
    winner_id: int = Field(..., alias="winnerId", description="Winner's ID")
    winner_en: str = Field(..., alias="winnerEn", description="Winner's English name")
    winner_jp: str = Field(..., alias="winnerJp", description="Winner's Japanese name")


class KimariteMatchesResponse(BaseModel):
    """Model for the kimarite matches endpoint response."""

    limit: Optional[int] = Field(None, description="Number of records to return")
    skip: Optional[int] = Field(0, description="Number of records to skip")
    total: int = Field(..., description="Total number of matches found")
    records: List[KimariteMatch] = Field(
        ..., description="List of matches where the kimarite was used"
    )
