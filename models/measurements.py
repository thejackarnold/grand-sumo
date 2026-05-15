from typing import List

from pydantic import BaseModel, Field


class Measurement(BaseModel):
    """Model for a single measurement record."""

    id: str = Field(..., description="Measurement ID in format YYYYMM-rikishiId")
    basho_id: str = Field(..., alias="bashoId", description="Basho ID in YYYYMM format")
    rikishi_id: int = Field(..., alias="rikishiId", description="Rikishi ID")
    height: float = Field(..., description="Height in centimeters")
    weight: float = Field(..., description="Weight in kilograms")


# The API returns a list of measurements directly
MeasurementsResponse = List[Measurement]
