"""
RAG-Enhanced Prediction Activity.

This module provides Temporal activities for making predictions with RAG support.
Processes questions sequentially, one at a time, with context accumulation.
"""

import json
import logging
from typing import Dict, Any, List, Optional
from temporalio import activity
import google.generativeai as genai

from config import settings
from services import (
    get_rag_client,
    get_rag_filter,
    get_or_create_context
)

logger = logging.getLogger(__name__)


@activity.defn
async def predict_single_question_with_rag(
    question_id: str,
    question_data: Dict[str, Any],
    company_data: Dict[str, Any],
    configuration: Dict[str, Any],
    session_id: str,
    context_summary: Optional[str] = None
) -> Dict[str, Any]:
    """
    Predict answer for a single question with RAG enhancement.

    This is the core activity that:
    1. Checks if RAG should be used for this question
    2. Retrieves relevant document chunks if needed
    3. Builds context from company data + RAG + previous predictions
    4. Calls Gemini to make prediction
    5. Returns prediction with metadata

    Args:
        question_id: Question identifier (e.g., "CL_Q1")
        question_data: Question details (text, options, type)
        company_data: Company information
        configuration: Presumptive config (cloud provider, etc.)
        session_id: Session identifier for context tracking
        context_summary: Previous predictions context (optional)

    Returns:
        Dictionary containing:
            - success: bool
            - question_id: str
            - prediction: str or list
            - reasoning: str
            - confidence: str
            - rag_used: bool
            - rag_sources: list
            - rag_metadata: dict
            - error: str (if failed)
    """
    activity.logger.info(f"Processing question {question_id} with RAG enhancement")

    try:
        # Extract question details
        question_text = question_data.get('question', '')
        question_type = question_data.get('type', 'single')
        options = question_data.get('options', [])

        # Step 1: Determine if RAG should be used
        rag_filter = get_rag_filter()
        rag_decision = rag_filter.should_use_rag(
            question_id=question_id,
            question_text=question_text,
            question_type=question_type
        )

        should_use_rag = rag_decision.get('use_rag', False)
        rag_reason = rag_decision.get('reason', '')

        activity.logger.info(
            f"RAG decision for {question_id}: "
            f"{'YES' if should_use_rag else 'NO'} - {rag_reason}"
        )

        rag_context = ""
        rag_sources = []
        rag_chunks = []
        rag_metadata = {"rag_decision": rag_decision}

        # Step 2: Retrieve RAG context if needed
        if should_use_rag:
            activity.logger.info(f"Retrieving RAG context for {question_id}")

            rag_client = get_rag_client()
            rag_settings = rag_filter.get_rag_settings()

            # Build RAG query (combine question with company context)
            rag_query = _build_rag_query(
                question_text=question_text,
                company_data=company_data,
                configuration=configuration
            )

            # Call RAG API
            rag_result = rag_client.retrieve_chunks(
                query=rag_query,
                top_k=rag_settings.get('top_k', 5),
                timeout=rag_settings.get('timeout_seconds', 10),
                retry=rag_settings.get('retry_attempts', 1) > 0
            )

            if rag_result.get('success'):
                rag_chunks = rag_result.get('chunks', [])
                rag_sources = rag_client.extract_sources(rag_chunks)
                rag_context = rag_client.format_chunks_as_context(
                    rag_chunks,
                    include_sources=True,
                    include_similarity=False
                )
                rag_metadata['retrieval_time'] = rag_result.get('retrieval_time')
                rag_metadata['total_chunks'] = len(rag_chunks)

                activity.logger.info(
                    f"Retrieved {len(rag_chunks)} chunks from "
                    f"{len(rag_sources)} sources"
                )
            else:
                activity.logger.warning(
                    f"RAG retrieval failed: {rag_result.get('error')}"
                )
                rag_metadata['error'] = rag_result.get('error')

        # Step 3: Build comprehensive prompt
        prompt = _build_prediction_prompt(
            question_id=question_id,
            question_text=question_text,
            question_type=question_type,
            options=options,
            company_data=company_data,
            configuration=configuration,
            rag_context=rag_context,
            previous_context=context_summary
        )

        # Step 4: Call Gemini for prediction
        genai.configure(api_key=settings.google_api_key)
        model = genai.GenerativeModel(model_name=settings.gemini_model)

        generation_config = genai.types.GenerationConfig(
            temperature=0.4,  # Lower for more consistent predictions
            max_output_tokens=2048,
        )

        response = await model.generate_content_async(
            prompt,
            generation_config=generation_config
        )

        activity.logger.info(f"Received prediction from Gemini for {question_id}")

        # Step 5: Parse response
        result_text = response.text

        # Try to extract JSON
        try:
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0]
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0]

            prediction_data = json.loads(result_text.strip())

            prediction = prediction_data.get('prediction')
            reasoning = prediction_data.get('reasoning', '')
            confidence = prediction_data.get('confidence', 'medium')

        except (json.JSONDecodeError, IndexError) as e:
            activity.logger.warning(
                f"Failed to parse JSON response: {e}. Using fallback."
            )
            # Fallback: use raw text as reasoning
            prediction = None
            reasoning = result_text
            confidence = 'low'

        # Step 6: Store in context
        prediction_context = get_or_create_context(session_id)
        prediction_context.add_prediction(
            question_id=question_id,
            question_text=question_text,
            predicted_answer=prediction,
            reasoning=reasoning,
            confidence=confidence,
            rag_used=should_use_rag,
            rag_sources=rag_sources,
            rag_chunks=rag_chunks,
            metadata=rag_metadata
        )

        return {
            "success": True,
            "question_id": question_id,
            "prediction": prediction,
            "reasoning": reasoning,
            "confidence": confidence,
            "rag_used": should_use_rag,
            "rag_sources": rag_sources,
            "rag_metadata": rag_metadata
        }

    except Exception as e:
        activity.logger.error(
            f"Error predicting question {question_id}: {str(e)}"
        )
        return {
            "success": False,
            "question_id": question_id,
            "error": str(e),
            "rag_used": False
        }


def _build_rag_query(
    question_text: str,
    company_data: Dict[str, Any],
    configuration: Dict[str, Any]
) -> str:
    """
    Build optimized RAG query including company context for better chunk retrieval.

    Args:
        question_text: The question to answer
        company_data: Company information
        configuration: Config data

    Returns:
        RAG query string with company context
    """
    company_name = company_data.get('Company name', 'the organization')
    sector = company_data.get('Sector', 'technology')
    compliance = company_data.get('Compliance Requirements', [])
    cloud_provider = configuration.get('cloud_provider', 'AWS')

    # Format compliance as string
    if isinstance(compliance, list):
        compliance_str = ", ".join(compliance) if compliance else "standard compliance"
    else:
        compliance_str = str(compliance) if compliance else "standard compliance"

    # Build enhanced query with company context
    query = f"""
Company: {company_name}
Industry: {sector}
Cloud Provider: {cloud_provider}
Compliance Requirements: {compliance_str}

Question: {question_text}

Find relevant {cloud_provider} best practices, compliance guidelines, security recommendations, and technical implementation guidance specific to {sector} industry with {compliance_str} requirements.
""".strip()

    return query


def _build_prediction_prompt(
    question_id: str,
    question_text: str,
    question_type: str,
    options: List[Dict],
    company_data: Dict[str, Any],
    configuration: Dict[str, Any],
    rag_context: str,
    previous_context: Optional[str]
) -> str:
    """
    Build comprehensive prompt for Gemini prediction.

    Args:
        question_id: Question ID
        question_text: Question text
        question_type: single/multi/input
        options: Available options
        company_data: Company info
        configuration: Config data
        rag_context: RAG document context
        previous_context: Previous predictions

    Returns:
        Complete prompt string
    """
    # Extract company details
    company_name = company_data.get('Company name', 'Unknown')
    sector = company_data.get('Sector', '')
    global_presence = company_data.get('Global presence', '')
    compliance = company_data.get('Compliance Requirements', [])
    cloud_provider = configuration.get('cloud_provider', 'AWS')

    # Format options
    if options:
        options_str = "\n".join([f"  - {opt.get('label', opt)}" for opt in options])
    else:
        options_str = "N/A (text input question)"

    # Build prompt sections
    prompt = f"""
You are an expert {cloud_provider} Landing Zone architect. Analyze the question and predict the most appropriate answer based on company context.

**Company Information:**
- Company Name: {company_name}
- Sector: {sector}
- Global Presence: {global_presence}
- Cloud Provider: {cloud_provider}
- Compliance Requirements: {compliance}

**Previous Selections:**
{previous_context if previous_context else "None yet - this is the first question."}
"""

    # Add RAG context if available
    if rag_context:
        prompt += f"""

**Relevant {cloud_provider} Documentation and Best Practices:**
{rag_context}

IMPORTANT: The above documentation has been retrieved specifically for this question. You MUST reference these documents in your reasoning.
"""

    prompt += f"""

**Current Question [{question_id}]:**
{question_text}

**Available Options:**
{options_str}

**Task:**
Analyze the company's characteristics, compliance requirements, previous selections, and the retrieved documentation to predict the most appropriate answer.

**Response Format Requirements:**

1. Your "reasoning" MUST follow this format if RAG documentation was provided:
   - START with: "✅ Based on Retrieved {cloud_provider} Documentation:"
   - List the document names that informed your decision
   - Then provide key points in BULLET FORMAT (use • bullets)
   - Keep each bullet concise and focused on ONE key factor
   - DO NOT repeat company name or compliance requirements in bullets unless absolutely necessary
   - Focus on technical recommendations and specific findings

2. Example reasoning format:
   "✅ Based on Retrieved {cloud_provider} Documentation:\\nReferenced: [document names]\\n\\n• Recommends regional account separation for multi-region deployments\\n• Enhances compliance posture through isolation and control\\n• Aligns with security best practices for workload segregation\\n• Facilitates network isolation between environments"

**JSON Response Format:**
{{
    "prediction": "selected option label" | ["option1", "option2"] | "text answer",
    "reasoning": "MUST start with '✅ Based on Retrieved {cloud_provider} Documentation:' if RAG context provided, followed by Referenced: [docs], then bullet points (• format) with concise technical findings. DO NOT repeat company name/compliance in bullets.",
    "confidence": "high" | "medium" | "low"
}}

Respond with ONLY the JSON object, no additional text.
"""

    return prompt


# Export activities
__all__ = [
    'predict_single_question_with_rag'
]
