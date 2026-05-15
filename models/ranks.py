from typing import List

from pydantic import BaseModel, Field


class Rank(BaseModel):
    """Model for a single rank record."""

    id: str = Field(..., description="Rank ID in format YYYYMM-rikishiId")
    basho_id: str = Field(..., alias="bashoId", description="Basho ID in YYYYMM format")
    rikishi_id: int = Field(..., alias="rikishiId", description="Rikishi ID")
    rank_value: int = Field(
        ...,
        alias="rankValue",
        description="Numerical rank value (lower is higher rank)",
    )
    rank: str = Field(..., description="Human-readable rank name")


# The API returns a list of ranks directly
RanksResponse = List[Rank]
