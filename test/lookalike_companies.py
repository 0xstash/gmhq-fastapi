import requests
import json
import os
from datetime import datetime
from dotenv import load_dotenv
import questionary
from typing import List, Optional
import sys

load_dotenv()


def validate_api_key():
    """Validate that API key exists and is set"""
    api_key = os.getenv("COMPANYENRICH_API_KEY")
    if not api_key:
        print("Error: COMPANYENRICH_API_KEY not found in environment variables")
        print("Please add your API key to the .env file like this:")
        print("COMPANYENRICH_API_KEY=your_api_key_here")
        return False
    return True


def get_form_inputs() -> dict:
    """Get user inputs using questionary forms"""

    # Basic parameters
    domain = questionary.text(
        "Enter the domain to find similar companies for", default="godmodehq.com"
    ).ask()

    page = questionary.text(
        "Enter the page number (1-100)",
        default="1",
        validate=lambda val: val.isdigit() and 1 <= int(val) <= 100,
    ).ask()

    page_size = questionary.text(
        "Enter the number of results per page (1-100)",
        default="10",
        validate=lambda val: val.isdigit() and 1 <= int(val) <= 100,
    ).ask()

    # Optional filters
    use_filters = questionary.confirm(
        "Would you like to add filters?", default=False
    ).ask()

    filters = {}
    if use_filters:
        # Countries filter
        if questionary.confirm("Add country filters?").ask():
            countries = questionary.checkbox(
                "Select countries (space to select, enter to confirm)",
                choices=["US", "CA", "GB", "DE", "FR", "ES", "IT", "NL", "AU", "IN"],
            ).ask()
            if countries:
                filters["countries"] = countries

        # Company type filter
        if questionary.confirm("Add company type filters?").ask():
            types = questionary.checkbox(
                "Select company types",
                choices=[
                    "b2b",
                    "b2c",
                    "b2g",
                    "ecommerce",
                    "enterprise",
                    "saas",
                    "marketplace",
                ],
            ).ask()
            if types:
                filters["type"] = types

        # Employee count filter
        if questionary.confirm("Add employee count filters?").ask():
            employees = questionary.checkbox(
                "Select employee ranges",
                choices=[
                    "1-10",
                    "11-50",
                    "51-200",
                    "201-500",
                    "501-1000",
                    "1001-5000",
                    "5001-10000",
                    "10001+",
                ],
            ).ask()
            if employees:
                filters["employees"] = employees

        # Revenue filter
        if questionary.confirm("Add revenue filters?").ask():
            revenue = questionary.checkbox(
                "Select revenue ranges",
                choices=[
                    "1M-10M",
                    "11M-50M",
                    "51M-100M",
                    "101M-500M",
                    "501M-1B",
                    "1B+",
                ],
            ).ask()
            if revenue:
                filters["revenue"] = revenue

    return {"domain": domain, "page": int(page), "pageSize": int(page_size), **filters}


def fetch_similar_companies(payload: dict):
    """
    Fetch similar companies using the CompanyEnrich API

    Args:
        payload (dict): API request payload with parameters and filters
    """
    api_key = os.getenv("COMPANYENRICH_API_KEY")

    # API configuration
    url = "https://api.companyenrich.com/companies/similar"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "accept": "application/json",
        "Content-Type": "application/json",
    }

    try:
        # Make API request
        response = requests.post(url, headers=headers, json=payload)

        # Handle different error cases
        if response.status_code == 401:
            print("Error: Unauthorized. Please check your API key.")
            print(f"Current API key: {api_key[:5]}...{api_key[-5:] if api_key else ''}")
            return None
        elif response.status_code == 402:
            print("Error: Payment Required. Please check your account credits.")
            return None
        elif response.status_code == 429:
            print("Error: Too Many Requests. Please try again later.")
            return None

        response.raise_for_status()

        # Parse response
        data = response.json()

        # Create data directory if it doesn't exist
        data_dir = os.path.join(os.path.dirname(__file__), "data")
        os.makedirs(data_dir, exist_ok=True)

        # Use a fixed filename for storing all results
        filename = os.path.join(data_dir, "similar_companies_history.json")

        # Load existing data or create empty list
        existing_data = []
        if os.path.exists(filename):
            try:
                with open(filename, "r") as f:
                    existing_data = json.load(f)
            except json.JSONDecodeError:
                existing_data = []

        # Add timestamp to new data
        timestamped_data = {"timestamp": datetime.now().isoformat(), "data": data}

        # Append new data to existing data
        existing_data.append(timestamped_data)

        # Save updated data back to file
        with open(filename, "w") as f:
            json.dump(existing_data, f, indent=4)

        print(f"Data successfully appended to {filename}")
        return data

    except requests.exceptions.RequestException as e:
        print(f"Error making API request: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error: {e}")
        return None


if __name__ == "__main__":
    # Validate API key before proceeding
    if not validate_api_key():
        sys.exit(1)

    # Get parameters from user input
    params = get_form_inputs()

    # Show summary of selected parameters
    print("\nSelected parameters:")
    print(json.dumps(params, indent=2))

    # Confirm before making API call
    if questionary.confirm("Make API call with these parameters?", default=True).ask():
        fetch_similar_companies(params)
    else:
        print("Operation cancelled")
