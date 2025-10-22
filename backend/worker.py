"""
Temporal worker for executing workflows and activities.

This module starts a Temporal worker that processes company search workflows.
"""

import asyncio
import logging

from temporalio.client import Client
from temporalio.worker import Worker

from config import settings
from workflows import CompanySearchWorkflow, CompanyDetailWorkflow
from activities import (
    search_companies,
    parse_company_input,
    get_detailed_company_info,
    infer_presumptive_config,
    infer_questionnaire_answers
)


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main() -> None:
    """Start the Temporal worker."""
    logger.info(f"Connecting to Temporal server at {settings.temporal_host}")

    # Connect to Temporal server
    client = await Client.connect(
        settings.temporal_host,
        namespace=settings.temporal_namespace,
    )

    logger.info(f"Starting worker for task queue: {settings.temporal_task_queue}")

    # Create and start worker
    worker = Worker(
        client,
        task_queue=settings.temporal_task_queue,
        workflows=[CompanySearchWorkflow, CompanyDetailWorkflow],
        activities=[
            search_companies,
            parse_company_input,
            get_detailed_company_info,
            infer_presumptive_config,
            infer_questionnaire_answers
        ],
    )

    logger.info("Worker started successfully")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
