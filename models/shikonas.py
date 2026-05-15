from typing import List

from pydantic import BaseModel, Field


class Shikona(BaseModel):
    """Model for a single shikona record."""

    id: str = Field(..., description="Shikona ID in format YYYYMM-rikishiId")
    basho_id: str = Field(..., alias="bashoId", description="Basho ID in YYYYMM format")
    rikishi_id: int = Field(..., alias="rikishiId", description="Rikishi ID")
    shikona_en: str = Field(..., alias="shikonaEn", description="English shikona name")
    shikona_jp: str = Field(..., alias="shikonaJp", description="Japanese shikona name")


# The API returns a list of shikonas directly
ShikonasResponse = List[Shikona]
