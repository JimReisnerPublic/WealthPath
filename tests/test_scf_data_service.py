from __future__ import annotations

from wealthpath.models.cohort import CohortRequest
from wealthpath.models.household import EducationLevel, HouseholdProfile
from wealthpath.services.scf_data_service import SCFDataService


def test_load_and_match_cohort(scf_service: SCFDataService) -> None:
    profile = HouseholdProfile(
        age=40, income=70000, net_worth=150000, education=EducationLevel.BACHELORS
    )
    cohort = scf_service.match_cohort(profile)
    assert len(cohort) > 0
    assert all(cohort["age"] >= 35)
    assert all(cohort["age"] <= 45)


def test_compare(scf_service: SCFDataService) -> None:
    request = CohortRequest(
        household=HouseholdProfile(
            age=40,
            income=70000,
            net_worth=150000,
            education=EducationLevel.BACHELORS,
        ),
        compare_fields=["income", "net_worth"],
    )
    response = scf_service.compare(request)
    assert response.cohort_size > 0
    assert len(response.stats) == 2
    for stat in response.stats:
        assert stat.cohort_p25 <= stat.cohort_median <= stat.cohort_p75


def test_fallback_to_full_dataset(scf_service: SCFDataService) -> None:
    """If no cohort matches, should fall back to the full dataset."""
    profile = HouseholdProfile(
        age=99, income=10000, net_worth=0, education=EducationLevel.NO_HIGH_SCHOOL
    )
    cohort = scf_service.match_cohort(profile)
    assert len(cohort) > 0  # fell back to full dataset
