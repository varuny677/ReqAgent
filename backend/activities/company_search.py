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

    IMPORTANT: Return EXACTLY 3 companies maximum. Choose the 3 most relevant matches.

    For each company name provided, please:
    1. Search for companies with exact or similar names
    2. Include variations, subsidiaries, or related companies
    3. Select the TOP 3 most relevant matches
    4. Provide the following information for each match:
       - Official company name
       - Brief description (1-2 sentences)
       - Industry/sector
       - Location/headquarters (if available)
       - Website (if available)

    Format your response as a JSON array of company objects with EXACTLY 3 entries.
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

            # Ensure we return exactly 3 companies maximum
            if isinstance(companies, list) and len(companies) > 3:
                companies = companies[:3]
                activity.logger.info(f"Limited results to 3 companies")

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


@activity.defn
async def get_detailed_company_info(company_name: str, company_website: str = None) -> Dict[str, Any]:
    """
    Get detailed information about a specific company using Google Gemini with grounding.

    Args:
        company_name: The official company name
        company_website: Optional company website URL for better search

    Returns:
        Dictionary containing detailed company information in JSON format
    """
    activity.logger.info(f"Getting detailed info for company: {company_name}")

    # Configure Gemini
    genai.configure(api_key=settings.google_api_key)

    # Create the model
    model = genai.GenerativeModel(
        model_name=settings.gemini_model
    )

    # Craft a detailed prompt
    website_info = f" (Website: {company_website})" if company_website else ""
    prompt = f"""
    You are a business intelligence assistant. Please search for detailed information about the company: {company_name}{website_info}

    Provide comprehensive information in the following JSON format:

    {{
        "Company name": "<official company name>",
        "Sector": "<primary business sector, e.g., Technology, Healthcare, Finance>",
        "Sub Sector": "<specific industry/sub-sector>",
        "Networth": "<market cap, valuation, or net worth with currency>",
        "No of Employees": "<approximate number of employees>",
        "Country of origin": "<country where company was founded>",
        "Global presence": "<Yes/No and brief description of international operations>",
        "List of countries they operate in": ["<country1>", "<country2>", "..."],
        "brief about company": "<2-3 sentence summary of what the company does>",
        "Compliance Requirements": ["<relevant compliance frameworks like GDPR, HIPAA, SOC2, ISO27001, etc.>"]
    }}

    Important instructions:
    1. Use your web search capabilities to find the most accurate and up-to-date information
    2. For "Compliance Requirements", infer based on the company's industry:
       - Healthcare companies: HIPAA, HITRUST
       - Financial services: PCI-DSS, SOX, GLBA
       - Technology/SaaS: SOC2, ISO27001, GDPR
       - Government contractors: FedRAMP, NIST
       - General: GDPR (if EU operations), CCPA (if California operations)
    3. If specific information is not available, use "Insufficient data" for that field
    4. Ensure the JSON is properly formatted
    5. For "List of countries they operate in", provide an actual array, not a string
    """

    try:
        # Generate response with higher token limit for detailed info
        generation_config = {
            'temperature': 0.5,  # Lower temperature for more factual responses
            'top_p': 0.95,
            'max_output_tokens': 3072,
        }

        response = model.generate_content(
            prompt,
            generation_config=generation_config
        )

        activity.logger.info("Detailed company info received from Gemini")

        # Extract and parse JSON
        result_text = response.text

        try:
            # Remove markdown code blocks if present
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0]
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0]

            company_info = json.loads(result_text.strip())

            return {
                "success": True,
                "company_name": company_name,
                "data": company_info
            }

        except (json.JSONDecodeError, IndexError) as e:
            activity.logger.warning(f"Could not parse JSON: {e}")
            activity.logger.warning(f"Raw response: {result_text}")
            return {
                "success": False,
                "company_name": company_name,
                "error": "Failed to parse response",
                "raw_response": result_text
            }

    except Exception as e:
        activity.logger.error(f"Error getting detailed company info: {str(e)}")
        return {
            "success": False,
            "company_name": company_name,
            "error": str(e)
        }


@activity.defn
async def infer_presumptive_config(company_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Infer presumptive configuration form values from company data using AI.

    This activity uses Gemini to intelligently determine configuration
    preferences based on company information such as sector, location,
    global presence, and operating countries.

    Args:
        company_data: Dictionary containing detailed company information
                     including Sector, Sub Sector, Country of origin,
                     Global presence, List of countries they operate in, etc.

    Returns:
        Dictionary containing presumptive form field values:
        - industry_sector: Primary industry sector
        - sub_sector: Specific sub-sector
        - cloud_provider: Recommended cloud provider (AWS/Azure/GCP)
        - target_continent: Primary target continent
        - region_strategy: Deployment region strategy
    """
    activity.logger.info("Inferring presumptive configuration from company data")

    # Configure Gemini
    genai.configure(api_key=settings.google_api_key)

    # Create the model
    model = genai.GenerativeModel(
        model_name=settings.gemini_model
    )

    # Extract relevant company information
    company_name = company_data.get("Company name", "Unknown")
    sector = company_data.get("Sector", "")
    sub_sector = company_data.get("Sub Sector", "")
    country_of_origin = company_data.get("Country of origin", "")
    global_presence = company_data.get("Global presence", "")
    operating_countries = company_data.get("List of countries they operate in", [])

    # Craft the AI prompt
    prompt = f"""
    You are an enterprise IT infrastructure consultant. Based on the following company information,
    provide intelligent presumptive recommendations for their IT infrastructure configuration.

    Company Information:
    - Company Name: {company_name}
    - Sector: {sector}
    - Sub Sector: {sub_sector}
    - Country of Origin: {country_of_origin}
    - Global Presence: {global_presence}
    - Operating Countries: {operating_countries}

    Please analyze this information and provide recommendations in the following JSON format:

    {{
        "industry_sector": "<Choose ONE from: Aerospace & Defense, Agriculture & Farming, Automotive, Banking & Financial Services, Biotechnology, Chemicals, Construction & Real Estate, Consumer Goods & Retail, Education, Energy & Utilities, Entertainment & Media, Food & Beverage, Government & Public Sector, Healthcare & Pharmaceuticals, Hospitality & Tourism, Insurance, Legal Services, Logistics & Transportation, Manufacturing, Mining & Metals, Non-Profit & NGO, Oil & Gas, Professional Services, Telecommunications, Technology & Software, Textiles & Apparel, Others>",
        "sub_sector": "<Specific sub-sector based on industry_sector choice>",
        "cloud_provider": "<Choose ONE from: AWS, Azure, GCP based on company profile and industry>",
        "target_continent": "<Choose ONE from: North America, Europe, Asia Pacific, Middle East, South America based on primary operations>",
        "region_strategy": "<Choose ONE from: Single Region, Dual Primary Regions, Primary + DR based on global presence and criticality>"
    }}

    Guidelines for recommendations:
    1. Industry Sector Mapping (Choose the most appropriate):
       - Aerospace & Defense: Aircraft, defense contractors, space technology, aviation services
       - Agriculture & Farming: Crop production, livestock, AgriTech, aquaculture
       - Automotive: Auto manufacturing, EV, auto parts, dealerships
       - Banking & Financial Services: Banking, FinTech, wealth management, payment processing
       - Biotechnology: Biopharmaceuticals, genetic engineering, gene therapy
       - Chemicals: Specialty chemicals, petrochemicals, polymers, industrial chemicals
       - Construction & Real Estate: Construction, real estate development, PropTech, REITs
       - Consumer Goods & Retail: E-commerce, retail stores, FMCG, luxury goods
       - Education: K-12, higher education, EdTech, online learning
       - Energy & Utilities: Electric utilities, renewable energy, water/waste management
       - Entertainment & Media: Film, broadcasting, streaming, gaming, publishing
       - Food & Beverage: Food processing, restaurants, beverage manufacturing
       - Government & Public Sector: Federal/state/municipal government, public safety
       - Healthcare & Pharmaceuticals: Hospitals, pharmaceutical manufacturing, medical devices
       - Hospitality & Tourism: Hotels, travel agencies, airlines, tourism
       - Insurance: Life/health/property insurance, InsurTech, reinsurance
       - Legal Services: Corporate law, litigation, legal technology
       - Logistics & Transportation: Freight, warehousing, supply chain, last-mile delivery
       - Manufacturing: Industrial manufacturing, electronics, semiconductors
       - Mining & Metals: Mining operations, metal production, mineral processing
       - Non-Profit & NGO: Charitable organizations, international development, advocacy
       - Oil & Gas: Exploration, production, refining, oilfield services
       - Professional Services: Consulting, accounting, market research, BPO
       - Telecommunications: Mobile networks, ISPs, satellite, telecom equipment
       - Technology & Software: SaaS, cloud services, cybersecurity, AI/ML, enterprise software
       - Textiles & Apparel: Textile/garment manufacturing, fashion, footwear
       - Others: Industries not covered above

    2. Sub-Sector Examples by Industry (Choose specific sub-sector):
       - Aerospace & Defense: Aircraft Manufacturing, Defense Contractors, Space Technology, Aviation Services, Defense Electronics, Military Equipment, Satellite Systems, Drones & UAV
       - Agriculture & Farming: Crop Production, Livestock & Dairy, Agricultural Equipment, AgriTech, Organic Farming, Aquaculture, Forestry, Seeds & Fertilizers
       - Automotive: Automobile Manufacturing, Auto Parts & Components, Electric Vehicles (EV), Autonomous Vehicles, Two-Wheelers, Commercial Vehicles, Auto Dealerships, Aftermarket Services
       - Banking & Financial Services: Retail Banking, Commercial Banking, Investment Banking, FinTech, Wealth Management, Asset Management, Payment Processing, Digital Banking, Microfinance, Credit Unions
       - Biotechnology: Biopharmaceuticals, Genetic Engineering, Agricultural Biotech, Industrial Biotechnology, Bioinformatics, Gene Therapy, Synthetic Biology, Biomedical Engineering
       - Chemicals: Specialty Chemicals, Petrochemicals, Agricultural Chemicals, Industrial Chemicals, Polymers & Plastics, Pharmaceuticals Chemicals, Fine Chemicals, Paint & Coatings
       - Construction & Real Estate: Residential Construction, Commercial Construction, Infrastructure Development, Real Estate Development, Property Management, REITs, Construction Materials, Architecture & Design, PropTech
       - Consumer Goods & Retail: E-commerce, Department Stores, Specialty Retail, Fast Fashion, Luxury Goods, Consumer Electronics, Home Furnishings, Supermarkets & Grocery, Direct-to-Consumer (D2C), FMCG
       - Education: K-12 Education, Higher Education, EdTech, Online Learning Platforms, Vocational Training, Test Preparation, Corporate Training, Educational Content, Student Services, International Education
       - Energy & Utilities: Electric Utilities, Water & Waste Management, Renewable Energy, Solar Power, Wind Energy, Hydroelectric Power, Nuclear Energy, Energy Storage, Smart Grid, Gas Distribution
       - Entertainment & Media: Film Production, Broadcasting, Streaming Services, Music Industry, Publishing, Gaming, Sports & Entertainment, Advertising, Digital Media, Social Media
       - Food & Beverage: Food Processing, Beverage Manufacturing, Restaurants & QSR, Food Delivery, Packaged Foods, Dairy Products, Bakery & Confectionery, Alcoholic Beverages, Non-Alcoholic Beverages, Food Tech
       - Government & Public Sector: Federal Government, State/Provincial Government, Municipal Government, Defense & Military, Public Safety, Regulatory Agencies, Public Transportation, Government IT, Civic Services
       - Healthcare & Pharmaceuticals: Hospitals & Clinics, Pharmaceutical Manufacturing, Medical Devices, Telemedicine, Health Insurance, Clinical Research, Diagnostics, Home Healthcare, Mental Health Services, Healthcare IT, Medical Equipment, Drug Discovery
       - Hospitality & Tourism: Hotels & Resorts, Travel Agencies, Airlines, Cruise Lines, Event Management, Theme Parks, Online Travel Booking, Vacation Rentals, Tourism Boards, Restaurant Chains
       - Insurance: Life Insurance, Health Insurance, Property & Casualty, Auto Insurance, InsurTech, Reinsurance, Commercial Insurance, Specialty Insurance, Insurance Brokers
       - Legal Services: Corporate Law, Litigation, Intellectual Property, Legal Technology, Legal Process Outsourcing, Compliance & Regulatory, Immigration Law, Tax Law, Real Estate Law
       - Logistics & Transportation: Freight & Shipping, Warehousing, Last-Mile Delivery, Supply Chain Management, Third-Party Logistics (3PL), Fleet Management, Rail Transport, Maritime Shipping, Air Cargo, Logistics Technology
       - Manufacturing: Industrial Manufacturing, Consumer Goods Manufacturing, Electronics Manufacturing, Textile Manufacturing, Metal Fabrication, Machinery & Equipment, Semiconductor Manufacturing, Contract Manufacturing, Additive Manufacturing (3D Printing), Process Manufacturing
       - Mining & Metals: Coal Mining, Metal Ore Mining, Gold & Precious Metals, Industrial Minerals, Steel Production, Aluminum Production, Copper Mining, Rare Earth Elements, Mining Equipment, Mineral Processing
       - Non-Profit & NGO: Charitable Organizations, International Development, Environmental Conservation, Human Rights, Education Foundations, Healthcare Charities, Disaster Relief, Social Services, Advocacy Groups, Research Foundations
       - Oil & Gas: Upstream (Exploration & Production), Midstream (Transportation & Storage), Downstream (Refining & Distribution), Oilfield Services, Petrochemicals, LNG, Offshore Drilling, Pipeline Operations, Energy Trading
       - Professional Services: Consulting, Accounting & Audit, Management Consulting, HR Consulting, Market Research, Public Relations, Business Process Outsourcing, IT Consulting, Strategy Consulting, Tax Advisory
       - Telecommunications: Mobile Network Operators, Fixed-Line Telecom, Internet Service Providers (ISP), Satellite Communications, Telecom Equipment, 5G Infrastructure, Network Security, Unified Communications, VoIP Services, Telecom Software
       - Technology & Software: Software as a Service (SaaS), Cloud Services, Cybersecurity, Artificial Intelligence & ML, Enterprise Software, Mobile Applications, DevOps & Infrastructure, Data Analytics, Blockchain, IoT (Internet of Things), E-commerce Platforms, CRM Software, ERP Systems, Business Intelligence, Software Development
       - Textiles & Apparel: Textile Manufacturing, Garment Manufacturing, Fashion Design, Footwear, Sportswear, Luxury Fashion, Fast Fashion, Technical Textiles, Home Textiles, Apparel Retail
       - Others: Environmental Services, Security Services, Facility Management, Printing & Packaging, Waste Management, Research & Development, Think Tanks, Trade Associations, Membership Organizations, Other Industries

    3. Cloud Provider Selection:
       - AWS: Most versatile, best for startups and tech companies, strong in North America
       - Azure: Best for enterprises, Windows/Microsoft stack, strong in government and healthcare
       - GCP: Best for data analytics, ML/AI workloads, strong in APAC

    4. Target Continent:
       - Base this on Country of Origin and primary Operating Countries
       - Choose the continent where the company has strongest presence

    5. Region Strategy:
       - Single Region: Small/medium companies, limited geographic scope
       - Dual Primary Regions: Large companies with significant global presence
       - Primary + DR: Critical services requiring disaster recovery (finance, healthcare)

    Provide your response as a valid JSON object only, with no additional explanation.
    """

    try:
        # Generate response with configuration for factual inference
        generation_config = {
            'temperature': 0.3,  # Lower temperature for consistent recommendations
            'top_p': 0.90,
            'max_output_tokens': 1024,
        }

        response = model.generate_content(
            prompt,
            generation_config=generation_config
        )

        activity.logger.info("Presumptive config inference received from Gemini")

        # Extract and parse JSON
        result_text = response.text

        try:
            # Remove markdown code blocks if present
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0]
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0]

            inferred_config = json.loads(result_text.strip())

            # Validate that all required fields are present
            required_fields = [
                "industry_sector",
                "sub_sector",
                "cloud_provider",
                "target_continent",
                "region_strategy"
            ]

            for field in required_fields:
                if field not in inferred_config:
                    activity.logger.warning(
                        f"Missing field {field}, using default"
                    )
                    inferred_config[field] = "Others" if field == "industry_sector" else "Not specified"

            return {
                "success": True,
                "data": inferred_config,
                "company_name": company_name
            }

        except (json.JSONDecodeError, IndexError) as e:
            activity.logger.warning(f"Could not parse JSON: {e}")
            activity.logger.warning(f"Raw response: {result_text}")

            # Return default values if parsing fails
            return {
                "success": False,
                "error": "Failed to parse AI response",
                "data": {
                    "industry_sector": "Technology & Software",
                    "sub_sector": "Enterprise Software",
                    "cloud_provider": "AWS",
                    "target_continent": "North America",
                    "region_strategy": "Single Region"
                }
            }

    except Exception as e:
        activity.logger.error(
            f"Error inferring presumptive config: {str(e)}"
        )
        # Return default values on error
        return {
            "success": False,
            "error": str(e),
            "data": {
                "industry_sector": "Technology & Software",
                "sub_sector": "Enterprise Software",
                "cloud_provider": "AWS",
                "target_continent": "North America",
                "region_strategy": "Single Region"
            }
        }


@activity.defn
async def infer_questionnaire_answers(
    question_ids: List[str],
    questions_data: Dict[str, Any],
    company_data: Dict[str, Any],
    configuration: Dict[str, Any],
    current_answers: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Dynamically infer answers for questionnaire questions based on company context.

    This activity uses Gemini AI to intelligently predict answers for landing zone
    questionnaire questions by analyzing company data, configuration, and current answers.
    The AI provides dynamic preselections that work with any question structure.

    Args:
        question_ids: List of question IDs to analyze
        questions_data: Complete questions data structure from Questions.json
        company_data: Detailed company information
        configuration: Presumptive configuration (industry, cloud provider, etc.)
        current_answers: Previously answered questions for context

    Returns:
        Dictionary containing:
        - predictions: Dict mapping question_id to predicted answer(s)
        - assumptions: Dict mapping question_id to AI reasoning (3-4 lines)
        - confidence: Dict mapping question_id to confidence level (high/medium/low)
    """
    activity.logger.info(f"Inferring answers for {len(question_ids)} questions")

    try:
        # Configure Gemini
        genai.configure(api_key=settings.google_api_key)

        # Use Gemini 2.0 Flash with moderate temperature for balanced predictions
        model = genai.GenerativeModel(model_name=settings.gemini_model)

        # Extract relevant data for context
        company_name = company_data.get("Company name", "Unknown")
        sector = company_data.get("Sector", "")
        sub_sector = company_data.get("Sub Sector", "")
        global_presence = company_data.get("Global presence", "")
        operating_countries = company_data.get("List of countries they operate in", [])
        compliance_requirements = company_data.get("Compliance Requirements", [])

        # Build questions context
        questions_context = []
        all_questions = questions_data.get("questions", [])

        for qid in question_ids:
            q = next((item for item in all_questions if item.get("id") == qid), None)
            if q and q.get("type") != "section":
                questions_context.append({
                    "id": q.get("id"),
                    "question": q.get("question"),
                    "type": q.get("type"),
                    "options": [opt.get("label") for opt in q.get("options", [])] if q.get("options") else None
                })

        # Craft the AI prompt with dynamic analysis instructions
        prompt = f"""
You are an expert AWS Landing Zone architect. Analyze the company information and predict appropriate answers for the following questionnaire questions.

**IMPORTANT INSTRUCTIONS:**
1. Your predictions must be DYNAMIC - analyze each question based on its content, not hardcoded rules
2. For questions with options, compare the company's characteristics against each option to select the best match
3. For multi-select questions, you can select multiple options that apply
4. For text input questions, provide a concise, specific answer based on company context
5. If insufficient data exists to make a confident prediction, return "NOT_ENOUGH_DATA"
6. Provide clear reasoning (3-4 lines) explaining your prediction

**Company Context:**
- Company Name: {company_name}
- Sector: {sector}
- Sub Sector: {sub_sector}
- Industry (Config): {configuration.get('industry_sector', 'N/A')}
- Cloud Provider: {configuration.get('cloud_provider', 'N/A')}
- Target Continent: {configuration.get('target_continent', 'N/A')}
- Global Presence: {global_presence}
- Operating Countries: {operating_countries}
- Compliance Requirements: {compliance_requirements}

**Previously Answered Questions (for context):**
{json.dumps(current_answers, indent=2) if current_answers else "None"}

**Questions to Analyze:**
{json.dumps(questions_context, indent=2)}

**Response Format (JSON only):**
{{
    "predictions": {{
        "QUESTION_ID": "answer" | ["answer1", "answer2"] | "NOT_ENOUGH_DATA",
        // For single choice: provide one option label as string
        // For multiple choice: provide array of option labels
        // For text input: provide a specific text answer
        // If insufficient data: use "NOT_ENOUGH_DATA"
    }},
    "assumptions": {{
        "QUESTION_ID": "3-4 line explanation of reasoning based on company characteristics and question requirements"
    }},
    "confidence": {{
        "QUESTION_ID": "high" | "medium" | "low"
    }}
}}

**Analysis Guidelines:**
1. **Business Structure Questions**: Consider company size, global presence, operating model
2. **Compliance Questions**: Look at industry regulations, compliance requirements, data residency needs
3. **Network Questions**: Analyze global operations, connectivity needs, security requirements
4. **Disaster Recovery Questions**: Consider industry criticality, compliance mandates, business continuity needs
5. **Log/Audit Questions**: Review compliance requirements and industry standards

Respond with ONLY the JSON object, no additional text or markdown.
"""

        # Generate response with appropriate temperature
        generation_config = genai.types.GenerationConfig(
            temperature=0.5,  # Balanced creativity and consistency
            max_output_tokens=4096,
        )

        response = await model.generate_content_async(
            prompt,
            generation_config=generation_config
        )

        activity.logger.info("Questionnaire inference received from Gemini")

        # Extract and parse JSON
        result_text = response.text

        try:
            # Remove markdown code blocks if present
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0]
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0]

            inference_result = json.loads(result_text.strip())

            # Validate structure
            predictions = inference_result.get("predictions", {})
            assumptions = inference_result.get("assumptions", {})
            confidence = inference_result.get("confidence", {})

            # Filter out NOT_ENOUGH_DATA responses
            filtered_predictions = {}
            filtered_assumptions = {}
            filtered_confidence = {}

            for qid in question_ids:
                pred = predictions.get(qid)
                if pred and pred != "NOT_ENOUGH_DATA":
                    filtered_predictions[qid] = pred
                    filtered_assumptions[qid] = assumptions.get(qid, "AI prediction based on company context")
                    filtered_confidence[qid] = confidence.get(qid, "medium")
                else:
                    # Provide a clear message when insufficient data
                    filtered_assumptions[qid] = "Not enough data available to make a confident prediction. Please answer manually based on your specific requirements."

            return {
                "success": True,
                "predictions": filtered_predictions,
                "assumptions": filtered_assumptions,
                "confidence": filtered_confidence
            }

        except (json.JSONDecodeError, IndexError) as e:
            activity.logger.warning(f"Could not parse JSON: {e}")
            activity.logger.warning(f"Raw response: {result_text[:500]}")

            # Return empty predictions on parse error
            return {
                "success": False,
                "error": "Failed to parse AI response",
                "predictions": {},
                "assumptions": {qid: "AI analysis failed. Please answer manually." for qid in question_ids},
                "confidence": {}
            }

    except Exception as e:
        activity.logger.error(f"Error inferring questionnaire answers: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "predictions": {},
            "assumptions": {qid: f"Error during AI analysis: {str(e)}" for qid in question_ids},
            "confidence": {}
        }
