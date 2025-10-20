"""
Company search activities for Temporal workflows.

This module contains activities that perform company searches using
Google ADK and Gemini.
"""

import json
from typing import List, Dict, Any

from temporalio import activity
import google.generativeai as genai

from config import settings


@activity.defn
async def search_companies(company_names: str) -> Dict[str, Any]:
    """
    Search for companies using Google Gemini with grounding.

    Args:
        company_names: Comma or space-separated company names

    Returns:
        Dictionary containing search results and metadata
    """
    activity.logger.info(f"Searching for companies: {company_names}")

    # Configure Gemini
    genai.configure(api_key=settings.google_api_key)

    # Create the model - Gemini 2.0 Flash has built-in search capabilities
    model = genai.GenerativeModel(
        model_name=settings.gemini_model
    )

    # Craft the prompt
    prompt = f"""
    You are a helpful assistant that searches for company information.

    I need you to search for the following companies: {company_names}

    For each company name provided, please:
    1. Search for companies with exact or similar names
    2. Include variations, subsidiaries, or related companies
    3. Provide the following information for each match:
       - Official company name
       - Brief description (1-2 sentences)
       - Industry/sector
       - Location/headquarters (if available)
       - Website (if available)

    Format your response as a JSON array of company objects.
    Each object should have: name, description, industry, location, website

    If a field is not available, use null.
    """

    try:
        # Generate response with Gemini
        generation_config = {
            'temperature': 0.7,
            'top_p': 0.95,
            'max_output_tokens': 2048,
        }

        response = model.generate_content(
            prompt,
            generation_config=generation_config
        )

        activity.logger.info(f"Gemini response received")

        # Extract text from response
        result_text = response.text

        # Try to parse JSON from the response
        try:
            # Remove markdown code blocks if present
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0]
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0]

            companies = json.loads(result_text.strip())
        except (json.JSONDecodeError, IndexError):
            # If parsing fails, return the raw text
            activity.logger.warning(
                "Could not parse JSON from response, returning raw text"
            )
            companies = {
                "raw_response": result_text,
                "parsed": False
            }

        return {
            "success": True,
            "query": company_names,
            "results": companies,
            "count": len(companies) if isinstance(companies, list) else 0
        }

    except Exception as e:
        activity.logger.error(f"Error searching companies: {str(e)}")
        return {
            "success": False,
            "query": company_names,
            "error": str(e),
            "results": []
        }


@activity.defn
async def parse_company_input(user_input: str) -> List[str]:
    """
    Parse user input to extract individual company names.

    Args:
        user_input: Raw user input containing company names

    Returns:
        List of individual company names
    """
    activity.logger.info(f"Parsing company input: {user_input}")

    # Split by common separators
    separators = [',', ';', '\n', '|']
    companies = [user_input]

    for sep in separators:
        if sep in user_input:
            companies = user_input.split(sep)
            break

    # Clean up the names
    companies = [name.strip() for name in companies if name.strip()]

    activity.logger.info(f"Parsed companies: {companies}")

    return companies
