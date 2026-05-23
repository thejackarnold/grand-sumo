"""Models for the banzuke endpoint."""

from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from grand_sumo.models.match import Match


class RikishiBanzuke(BaseModel):
    """Model for a rikishi's banzuke entry."""

    model_config = ConfigDict(populate_by_name=True)

    side: str = Field(..., description="Side (East or West)")
    rikishi_id: int = Field(..., alias="rikishiID", description="Rikishi ID")
    shikona_en: str = Field(
        ..., alias="shikonaEn", description="Rikishi's English shikona"
    )
    shikona_jp: Optional[str] = Field(
        None, alias="shikonaJp", description="Rikishi's Japanese shikona"
    )
    rank_value: Optional[int] = Field(None, description="Numerical rank value")
    rank: str = Field(..., description="Rikishi's rank")
    wins: int = Field(0, description="Number of wins")
    losses: int = Field(0, description="Number of losses")
    absences: int = Field(0, description="Number of absences")
    record: List[Match] = Field(
        default_factory=list, description="List of matches for this rikishi"
    )


class Banzuke(BaseModel):
    """Model for the banzuke response."""

    model_config = ConfigDict(populate_by_name=True)

    basho_id: str = Field(..., alias="bashoId", description="Basho ID in YYYYMM format")
    division: str = Field(..., description="Division name")
    east: List[RikishiBanzuke] = Field(
        ..., description="List of rikishi on the east side"
    )
    west: List[RikishiBanzuke] = Field(
        ..., description="List of rikishi on the west side"
    )
