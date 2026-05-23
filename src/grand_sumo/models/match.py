"""Model for sumo matches."""

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class Match(BaseModel):
    """Unified model for sumo matches across all endpoints.

    This model combines all features from the various Match models used in different endpoints:
    - Rikishi matches
    - Banzuke matches
    - Torikumi matches
    - Kimarite matches
    """

    model_config = ConfigDict(populate_by_name=True)

    # Core match identification
    id: Optional[str] = Field(
        None, description="Match ID in format YYYYMM-day-matchNo-eastId-westId"
    )
    basho_id: str = Field(..., alias="bashoId", description="Basho ID in YYYYMM format")
    division: Optional[str] = Field(None, description="Division name")
    day: int = Field(..., description="Day of the tournament (1-15)")
    match_no: Optional[int] = Field(
        None, alias="matchNo", description="Match number for the day"
    )

    # East rikishi details (required for torikumi matches)
    east_id: Optional[int] = Field(
        None, alias="eastId", description="East rikishi's ID"
    )
    east_shikona: Optional[str] = Field(
        None, alias="eastShikona", description="East rikishi's shikona"
    )
    east_rank: Optional[str] = Field(
        None, alias="eastRank", description="East rikishi's rank"
    )

    # West rikishi details (required for torikumi matches)
    west_id: Optional[int] = Field(
        None, alias="westId", description="West rikishi's ID"
    )
    west_shikona: Optional[str] = Field(
        None, alias="westShikona", description="West rikishi's shikona"
    )
    west_rank: Optional[str] = Field(
        None, alias="westRank", description="West rikishi's rank"
    )

    # Match result details (required for banzuke matches)
    result: Optional[Literal["win", "loss", "absent", "fusen loss", "fusen win", ""]] = (
        Field(
            None,
            description="Result of the match from the perspective of the current rikishi",
        )
    )
    kimarite: Optional[str] = Field(None, description="Winning technique used")
    winner_id: Optional[int] = Field(None, alias="winnerId", description="Winner's ID")
    winner_en: Optional[str] = Field(
        None, alias="winnerEn", description="Winner's English name"
    )
    winner_jp: Optional[str] = Field(
        None, alias="winnerJp", description="Winner's Japanese name"
    )

    # Opponent details (required for banzuke matches)
    opponent_id: Optional[int] = Field(
        None, alias="opponentID", description="Opponent's ID"
    )
    opponent_shikona_en: Optional[str] = Field(
        None, alias="opponentShikonaEn", description="Opponent's English shikona"
    )
    opponent_shikona_jp: Optional[str] = Field(
        None, alias="opponentShikonaJp", description="Opponent's Japanese shikona"
    )

    @classmethod
    def from_torikumi(cls, data: dict) -> "Match":
        """Create a Match instance from torikumi data."""
        return cls(
            id=data.get("id"),
            bashoId=data["bashoId"],
            division=data["division"],
            day=data["day"],
            matchNo=data["matchNo"],
            eastId=data["eastId"],
            eastShikona=data["eastShikona"],
            eastRank=data["eastRank"],
            westId=data["westId"],
            westShikona=data["westShikona"],
            westRank=data["westRank"],
            kimarite=data["kimarite"],
            winnerId=data["winnerId"],
            winnerEn=data["winnerEn"],
            winnerJp=data["winnerJp"],
        )

    @classmethod
    def from_banzuke(cls, data: dict) -> "Match":
        """Create a Match instance from banzuke data."""
        return cls(
            bashoId=data.get("bashoId", ""),  # This will be set by the client
            day=0,  # Banzuke records don't include day
            result=data["result"],
            opponentID=data["opponentID"],
            opponentShikonaEn=data["opponentShikonaEn"],
            opponentShikonaJp=data.get("opponentShikonaJp", ""),  # This might be empty
            kimarite=data["kimarite"],
        )
