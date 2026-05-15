"""Models for the rikishi matches endpoint."""

from typing import List

from pydantic import BaseModel, ConfigDict, Field

from models.match import Match


class RikishiMatchesResponse(BaseModel):
    """Model for the rikishi matches response."""

    model_config = ConfigDict(populate_by_name=True)

    limit: int = Field(..., description="The maximum number of records returned")
    skip: int = Field(..., description="The number of records skipped")
    total: int = Field(..., description="The total number of records")
    records: List[Match] = Field(..., description="List of matches for the rikishi")


class RikishiOpponentMatchesResponse(BaseModel):
    """Model for the rikishi opponent matches response."""

    model_config = ConfigDict(populate_by_name=True)

    total: int = Field(
        ..., description="The total number of matches between the rikishi"
    )
    rikishi_wins: int = Field(
        ..., alias="rikishiWins", description="Number of wins for the first rikishi"
    )
    opponent_wins: int = Field(
        ..., alias="opponentWins", description="Number of wins for the opponent"
    )
    kimarite_wins: dict[str, int] = Field(
        ...,
        alias="kimariteWins",
        description="Dictionary of winning kimarite techniques and their counts",
    )
    kimarite_losses: dict[str, int] = Field(
        ...,
        alias="kimariteLosses",
        description="Dictionary of losing kimarite techniques and their counts",
    )
    matches: List[Match] = Field(
        ..., description="List of matches between the two rikishi"
    )
