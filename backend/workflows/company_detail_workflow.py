"""
Company detail workflow for Temporal.

This module defines the workflow for getting detailed information
about a specific company using Google ADK and Gemini.
"""

from datetime import timedelta
from typing import Dict, Any

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from activities import get_detailed_company_info


@workflow.defn
class CompanyDetailWorkflow:
    """
    Workflow for getting detailed company information.

    This workflow fetches comprehensive information about a selected company
    using Google ADK and Gemini with Google Search tool.
    """

    @workflow.run
    async def run(self, company_name: str, company_website: str = None) -> Dict[str, Any]:
        """
        Execute the company detail workflow.

        Args:
            company_name: The official company name
            company_website: Optional company website URL

        Returns:
            Dictionary containing detailed company information
        """
        workflow.logger.info(f"Starting company detail workflow for: {company_name}")

        # Get detailed company information
        detailed_info = await workflow.execute_activity(
            get_detailed_company_info,
            args=[company_name, company_website],
            start_to_close_timeout=timedelta(seconds=90),
        )

        workflow.logger.info(f"Detail fetch completed for: {company_name}")

        return {
            "company_name": company_name,
            "detailed_info": detailed_info,
            "workflow_id": workflow.info().workflow_id,
        }
