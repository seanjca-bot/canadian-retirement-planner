"""
Data models for household and individual retirement planning.
"""

from typing import Optional, Dict, Any
from dataclasses import dataclass, field


@dataclass
class Person:
    """
    Represents an individual in retirement planning.

    Contains all personal, financial, and government benefit parameters
    needed for comprehensive retirement planning.
    """
    # Personal Information
    name: str
    current_age: int
    retirement_age: int
    years_in_canada: int = 40  # Current accumulated years after age 18 (will increase in projections)

    # Account Balances
    rrsp_balance: float = 0.0
    tfsa_balance: float = 0.0
    nonreg_balance: float = 0.0

    # Income and Savings
    annual_income: float = 0.0  # Current employment income
    annual_savings: float = 0.0  # Annual contributions to retirement accounts

    # CPP Parameters
    cpp_start_age: int = 65
    cpp_contribution_years: int = 40
    cpp_earnings_ratio: float = 1.0  # Ratio of average earnings to YMPE

    # OAS Parameters
    oas_start_age: int = 65

    def __post_init__(self):
        """Validate person parameters."""
        if self.current_age < 18 or self.current_age > 100:
            raise ValueError(f"Current age must be between 18 and 100, got {self.current_age}")

        if self.retirement_age < 50 or self.retirement_age > 75:
            raise ValueError(f"Retirement age must be between 50 and 75, got {self.retirement_age}")

        if self.cpp_start_age < 60 or self.cpp_start_age > 70:
            raise ValueError(f"CPP start age must be between 60 and 70, got {self.cpp_start_age}")

        if self.oas_start_age < 65 or self.oas_start_age > 70:
            raise ValueError(f"OAS start age must be between 65 and 70, got {self.oas_start_age}")

        if self.cpp_earnings_ratio < 0 or self.cpp_earnings_ratio > 1:
            raise ValueError(f"CPP earnings ratio must be between 0 and 1, got {self.cpp_earnings_ratio}")

    @property
    def total_savings(self) -> float:
        """Total of all retirement accounts."""
        return self.rrsp_balance + self.tfsa_balance + self.nonreg_balance

    @property
    def years_to_retirement(self) -> int:
        """Years until retirement."""
        return max(0, self.retirement_age - self.current_age)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for easy serialization."""
        return {
            'name': self.name,
            'current_age': self.current_age,
            'retirement_age': self.retirement_age,
            'years_in_canada': self.years_in_canada,
            'rrsp_balance': self.rrsp_balance,
            'tfsa_balance': self.tfsa_balance,
            'nonreg_balance': self.nonreg_balance,
            'annual_income': self.annual_income,
            'annual_savings': self.annual_savings,
            'cpp_start_age': self.cpp_start_age,
            'cpp_contribution_years': self.cpp_contribution_years,
            'cpp_earnings_ratio': self.cpp_earnings_ratio,
            'oas_start_age': self.oas_start_age,
        }


@dataclass
class Household:
    """
    Represents a household for retirement planning.

    Can be a single person or a couple. Provides household-level
    operations and convenience methods for couple planning.
    """
    person1: Person
    person2: Optional[Person] = None
    household_annual_spending: float = 0.0
    apply_income_splitting: bool = True
    survivor_spending_ratio: float = 0.70  # 70% of couple spending when one passes

    def __post_init__(self):
        """Validate household parameters."""
        if self.survivor_spending_ratio < 0.5 or self.survivor_spending_ratio > 1.0:
            raise ValueError(f"Survivor spending ratio must be between 0.5 and 1.0, got {self.survivor_spending_ratio}")

    @property
    def is_couple(self) -> bool:
        """True if this is a couple, False if single person."""
        return self.person2 is not None

    @property
    def total_household_savings(self) -> float:
        """Combined savings of both people."""
        total = self.person1.total_savings
        if self.is_couple:
            total += self.person2.total_savings
        return total

    @property
    def age_difference(self) -> int:
        """Age difference between spouses (always positive)."""
        if not self.is_couple:
            return 0
        return abs(self.person1.current_age - self.person2.current_age)

    def get_older_person(self) -> Person:
        """Return the older person in the household."""
        if not self.is_couple:
            return self.person1
        return self.person1 if self.person1.current_age >= self.person2.current_age else self.person2

    def get_younger_person(self) -> Person:
        """Return the younger person in the household."""
        if not self.is_couple:
            return self.person1
        return self.person1 if self.person1.current_age < self.person2.current_age else self.person2

    def both_age_65_or_older(self, year_offset: int = 0) -> bool:
        """
        Check if both spouses are 65+ (for income splitting eligibility).

        Args:
            year_offset: Number of years in the future to check
        """
        if not self.is_couple:
            return (self.person1.current_age + year_offset) >= 65

        person1_age = self.person1.current_age + year_offset
        person2_age = self.person2.current_age + year_offset

        return person1_age >= 65 and person2_age >= 65

    def both_retired(self, year_offset: int = 0) -> bool:
        """
        Check if both spouses are retired.

        Args:
            year_offset: Number of years in the future to check
        """
        if not self.is_couple:
            return (self.person1.current_age + year_offset) >= self.person1.retirement_age

        person1_age = self.person1.current_age + year_offset
        person2_age = self.person2.current_age + year_offset

        return (person1_age >= self.person1.retirement_age and
                person2_age >= self.person2.retirement_age)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for easy serialization."""
        result = {
            'person1': self.person1.to_dict(),
            'is_couple': self.is_couple,
            'household_annual_spending': self.household_annual_spending,
            'apply_income_splitting': self.apply_income_splitting,
            'survivor_spending_ratio': self.survivor_spending_ratio,
        }
        if self.is_couple:
            result['person2'] = self.person2.to_dict()
        return result


def create_person_from_dict(data: Dict[str, Any]) -> Person:
    """Create a Person object from a dictionary."""
    return Person(**data)


def create_household_from_dict(data: Dict[str, Any]) -> Household:
    """Create a Household object from a dictionary."""
    person1 = create_person_from_dict(data['person1'])
    person2 = None
    if 'person2' in data and data['person2'] is not None:
        person2 = create_person_from_dict(data['person2'])

    return Household(
        person1=person1,
        person2=person2,
        household_annual_spending=data.get('household_annual_spending', 0.0),
        apply_income_splitting=data.get('apply_income_splitting', True),
        survivor_spending_ratio=data.get('survivor_spending_ratio', 0.70),
    )
