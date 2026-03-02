from __future__ import annotations

from typing import TYPE_CHECKING

from langchain_core.tools import tool

if TYPE_CHECKING:
    from wealthpath.services.scf_data_service import SCFDataService


def build_cohort_tools(scf_service: SCFDataService) -> list:
    """
    Factory that creates LangChain tools wrapping SCF cohort queries.

    Replaces Semantic Kernel's CohortPlugin / @kernel_function:

        SK:   kernel.add_plugin(CohortPlugin(scf_service), plugin_name="cohort")
              # Plugin methods become callable tools for the LLM via the Kernel

        LC:   tools = build_cohort_tools(scf_service)
              # Tools are plain callables in a list; passed directly to agent

    The @tool decorator reads the function's docstring as the tool description
    and inspects the type annotations to build the input schema — the same
    information SK captured via @kernel_function's name/description parameters.
    """

    @tool
    def get_cohort_median_income(age: int, education: str) -> str:
        """
        Get the median income for households similar to the user.

        Args:
            age: Age of the household head.
            education: Education level — one of: no_high_school, high_school,
                some_college, bachelors, graduate.
        """
        from wealthpath.models.household import EducationLevel, HouseholdProfile

        try:
            edu = EducationLevel(education)
        except ValueError:
            edu = EducationLevel.BACHELORS

        profile = HouseholdProfile(age=age, income=0, net_worth=0, education=edu)
        cohort = scf_service.match_cohort(profile)
        if "income" in cohort.columns:
            median = cohort["income"].median()
            return f"Median income for cohort: ${median:,.0f}"
        return "Income data not available for this cohort."

    @tool
    def get_cohort_median_net_worth(age: int, education: str) -> str:
        """
        Get the median net worth for households similar to the user.

        Args:
            age: Age of the household head.
            education: Education level — one of: no_high_school, high_school,
                some_college, bachelors, graduate.
        """
        from wealthpath.models.household import EducationLevel, HouseholdProfile

        try:
            edu = EducationLevel(education)
        except ValueError:
            edu = EducationLevel.BACHELORS

        profile = HouseholdProfile(age=age, income=0, net_worth=0, education=edu)
        cohort = scf_service.match_cohort(profile)
        if "net_worth" in cohort.columns:
            median = cohort["net_worth"].median()
            return f"Median net worth for cohort: ${median:,.0f}"
        return "Net worth data not available for this cohort."

    return [get_cohort_median_income, get_cohort_median_net_worth]
