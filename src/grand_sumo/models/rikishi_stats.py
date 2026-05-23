"""Models for rikishi statistics."""

from pydantic import BaseModel, Field


class DivisionStats(BaseModel):
    """Model representing statistics by division."""

    Jonokuchi: int = 0
    Jonidan: int = 0
    Sandanme: int = 0
    Makushita: int = 0
    Juryo: int = 0
    Makuuchi: int = 0


class Sansho(BaseModel):
    """Model representing special prizes (sansho)."""

    Gino_sho: int = Field(alias="Gino-sho", default=0)
    Kanto_sho: int = Field(alias="Kanto-sho", default=0)
    Shukun_sho: int = Field(alias="Shukun-sho", default=0)


class RikishiStats(BaseModel):
    """Model representing comprehensive statistics for a rikishi."""

    basho: int
    total_matches: int = Field(alias="totalMatches")
    total_wins: int = Field(alias="totalWins")
    total_losses: int = Field(alias="totalLosses")
    total_absences: int = Field(alias="totalAbsences")
    yusho: int
    absence_by_division: DivisionStats = Field(alias="absenceByDivision")
    basho_by_division: DivisionStats = Field(alias="bashoByDivision")
    loss_by_division: DivisionStats = Field(alias="lossByDivision")
    total_by_division: DivisionStats = Field(alias="totalByDivision")
    wins_by_division: DivisionStats = Field(alias="winsByDivision")
    yusho_by_division: DivisionStats = Field(alias="yushoByDivision")
    sansho: Sansho
