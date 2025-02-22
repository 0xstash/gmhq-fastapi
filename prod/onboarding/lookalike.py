import os
import sys
import logging
import questionary
from rich.pretty import pprint
from datetime import datetime
from dotenv import load_dotenv
import requests
import json

# Add the project root directory to Python path
sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

from griptape.configs.logging import JsonFormatter
from griptape.structures import Agent
from griptape.utils import StructureVisualizer
from griptape.configs import Defaults
from griptape.loaders import WebLoader
from griptape.tools import (
    WebSearchTool,
    WebScraperTool,
)
from griptape.configs.drivers import OpenAiDriversConfig
from griptape.drivers import OpenAiChatPromptDriver
from griptape.tasks import PromptTask

# tools
from extension.drivers.serper_web_search_driver.serper_web_search_driver import (
    SerperWebSearchDriver,
)
from extension.drivers.jina_web_scraper_driver.jina_web_scraper_driver import (
    JinaWebScraperDriver,
)

from griptape.events import (
    BaseEvent,
    EventBus,
    EventListener,
    FinishActionsSubtaskEvent,
    FinishPromptEvent,
    FinishTaskEvent,
    StartActionsSubtaskEvent,
    StartPromptEvent,
    StartTaskEvent,
)
from griptape.tools import (
    PromptSummaryTool,
)
from griptape.utils import Chat, Stream
from griptape.tasks import ToolkitTask

load_dotenv()


def setup_onboarding_logger():
    """
    Sets up a dedicated logger for onboarding process
    """
    # Create logs directory if it doesn't exist
    log_dir = os.path.join(os.path.dirname(__file__), "logs")
    os.makedirs(log_dir, exist_ok=True)

    # Create a new logger for onboarding
    onboarding_logger = logging.getLogger("onboarding")

    # Clear any existing handlers to prevent duplicate logs
    if onboarding_logger.handlers:
        onboarding_logger.handlers.clear()

    onboarding_logger.setLevel(logging.INFO)

    # Create file handler
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(log_dir, f"onboarding_{timestamp}.log")
    file_handler = logging.FileHandler(log_file)

    # Create formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    file_handler.setFormatter(formatter)

    # Add handler to logger
    onboarding_logger.addHandler(file_handler)

    # Prevent propagation to root logger
    onboarding_logger.propagate = False

    return onboarding_logger


def find_similar_companies(domain: str) -> dict:
    """
    Find similar companies using Company Enrich API
    """
    onboarding_logger = logging.getLogger("onboarding")
    onboarding_logger.info(f"Finding similar companies for domain: {domain}")

    url = "https://api.companyenrich.com/companies/similar"

    payload = {"domain": domain, "page": 1, "pageSize": 5}

    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "Authorization": f"Bearer {os.getenv('COMPANYENRICH_API_KEY')}",
    }

    try:
        onboarding_logger.info("Sending request to Company Enrich API")
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        response_data = response.json()
        onboarding_logger.info("Successfully received similar companies data")
        onboarding_logger.debug(f"API Response: {json.dumps(response_data, indent=2)}")
        return response_data
    except requests.exceptions.RequestException as e:
        onboarding_logger.error(f"Error finding similar companies: {str(e)}")
        return {"error": str(e)}


def display_similar_companies(data: dict) -> None:
    """
    Display domains and descriptions of similar companies
    """
    if "items" not in data:
        print("No similar companies found")
        return

    print("\nSimilar Companies:")
    print("-" * 80)

    for company in data["items"]:
        print(f"Domain: {company.get('domain', 'N/A')}")
        print(f"Description: {company.get('description', 'N/A')}")
        print("-" * 80)


def save_companies_data(companies_data: dict) -> None:
    """
    Save or update companies data to a JSON file
    """
    onboarding_logger = logging.getLogger("onboarding")
    file_path = os.path.join(os.path.dirname(__file__), "similar_companies.json")

    companies_to_save = []

    if "items" in companies_data:
        for company in companies_data["items"]:
            company_info = {
                "company_name": company.get("name", "N/A"),
                "website_url": company.get("website", "N/A"),
                "description": company.get("description", "N/A"),
                "employees": company.get("employees", "N/A"),
                "revenue": company.get("revenue", "N/A"),
                "keywords": company.get("keywords", []),
                "socials": {
                    "linkedin": company.get("socials", {}).get("linkedin_url"),
                    "twitter": company.get("socials", {}).get("twitter_url"),
                    "facebook": company.get("socials", {}).get("facebook_url"),
                    "instagram": company.get("socials", {}).get("instagram_url"),
                },
            }
            companies_to_save.append(company_info)

    try:
        with open(file_path, "w") as f:
            json.dump({"companies": companies_to_save}, f, indent=2)
        onboarding_logger.info(
            f"Successfully saved {len(companies_to_save)} companies to {file_path}"
        )
    except Exception as e:
        onboarding_logger.error(f"Error saving companies data: {str(e)}")


def main():
    # Setup onboarding logger
    onboarding_logger = setup_onboarding_logger()
    onboarding_logger.info("Starting company lookup process")

    # Get domain input from user using questionary
    domain = questionary.text(
        "Please enter the company domain to analyze:",
        validate=lambda text: len(text.strip()) > 0 and "." in text,
    ).ask()

    if domain:
        onboarding_logger.info(f"User provided domain: {domain}")

        # Find similar companies
        similar_companies = find_similar_companies(domain)

        # Display domains and descriptions
        display_similar_companies(similar_companies)

        # Save companies data to JSON file
        save_companies_data(similar_companies)
    else:
        onboarding_logger.warning("No domain provided by user")
        print("No domain provided. Exiting...")

    onboarding_logger.info("Completed company lookup process")


if __name__ == "__main__":
    main()
