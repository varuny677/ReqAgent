"""
Company search workflow for Temporal.

This module defines the main workflow for searching companies
using Google ADK and Gemini.
"""

from datetime import timedelta
from typing import Dict, Any

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from activities import search_companies, parse_company_input


@workflow.defn
class CompanySearchWorkflow:
    """
    Workflow for searching companies.

    This workflow orchestrates the company search process using
    Google ADK and Gemini with Google Search tool.
    """

    @workflow.run
    async def run(self, user_input: str) -> Dict[str, Any]:
        """
        Execute the company search workflow.

        Args:
            user_input: User input containing company names

        Returns:
            Dictionary containing search results
        """
        workflow.logger.info(f"Starting company search workflow: {user_input}")

        # Step 1: Parse company names from input
        company_names = await workflow.execute_activity(
            parse_company_input,
            user_input,
            start_to_close_timeout=timedelta(seconds=10),
        )

        workflow.logger.info(f"Parsed companies: {company_names}")

        # Step 2: Search for companies using Gemini with Google Search
        search_results = await workflow.execute_activity(
            search_companies,
            user_input,
            start_to_close_timeout=timedelta(seconds=60),
        )

        workflow.logger.info(f"Search completed: {search_results.get('count', 0)} results")

        return {
            "user_input": user_input,
            "parsed_companies": company_names,
            "search_results": search_results,
            "workflow_id": workflow.info().workflow_id,
        }
