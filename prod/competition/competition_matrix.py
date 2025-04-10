import json
import os
from dotenv import load_dotenv


def fetch_lookalike_companies_via_companyenrich(company_domain):
    import requests

    url = "https://api.companyenrich.com/companies/similar"
    payload = {"domain": company_domain, "page": 1, "pageSize": 5}

    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "Authorization": "Bearer " + os.getenv("COMPANYENRICH_API_KEY"),
    }

    try:
        req = requests.post(url, json=payload, headers=headers)
        response = req.json()
        items = response.get("items", [])
    except Exception as e:
        print("Lookalike company fetching failed: " + str(e))
        return []

    return items


def generate_competition_matrix(user_company_domain):
    import json

    from griptape.loaders import WebLoader
    from griptape.tools import WebSearchTool, WebScraperTool
    from griptape.structures import Agent
    from griptape.drivers.prompt.openai import OpenAiChatPromptDriver
    from griptape.tasks import ToolkitTask

    from extension.drivers.serper_web_search_driver.serper_web_search_driver import (
        SerperWebSearchDriver,
    )
    from extension.drivers.jina_web_scraper_driver.jina_web_scraper_driver import (
        JinaWebScraperDriver,
    )

    lookalike_companies = fetch_lookalike_companies_via_companyenrich(user_company_domain)
    if not lookalike_companies or not isinstance(lookalike_companies, list) or len(lookalike_companies) == 0:
        return None

    competitor_index = 1
    competitor_data = ""

    for lookalike in lookalike_companies:
        company_name = lookalike.get("name")
        website_url = lookalike.get("website")
        description = lookalike.get("description")

        if not company_name or not website_url:
            continue

        competitor_data += f"Name of Competitor #{competitor_index}: {company_name}\n"
        competitor_data += f"Website of Competitor #{competitor_index}: {website_url}\n"
        competitor_data += f"Description of Competitor #{competitor_index}: {description}\n\n"
        competitor_index += 1

    if len(competitor_data) == 0:
        return None

    web_search_tool = WebSearchTool(
        web_search_driver=SerperWebSearchDriver(
            api_key=os.getenv("SERPER_API_KEY"), type="search"
        )
    )
    web_scraper_tool = WebScraperTool(
        web_loader=WebLoader(
            web_scraper_driver=JinaWebScraperDriver(api_key=os.getenv("JINA_API_KEY"))
        )
    )
    prompt = """You are an AI assistant tasked with generating a competition matrix among the user's own company and some other competitor companies. Your goal is to make a research about all the given companies and generate a competition matrix to promote the user's company.

    Information about the user's company:
    - Company website: {{user_company_domain}}

    Information about the competitors:
    {{competitor_data}}

    Your output needs to be formatted as follows:
    - Your output should include ONLY a JSON object and nothing else.
    - Each key in the JSON object represents a feature/spec to be compared across the given companies
    - The value of the keys is another JSON object where the keys correspond to each company (Starting with the user's company) and their values are simply boolean values representing whether the given company does have the feature/spec or not."""

    competition_analysis_task = ToolkitTask(
        input=prompt,
        id=f"competition_analysis",
        prompt_driver=OpenAiChatPromptDriver(model="gpt-4o-mini", api_key=os.getenv("OPENAI_API_KEY")),
        context={
            "user_company_domain": user_company_domain,
            "competitor_data": competitor_data
        },
        tools=[
            web_search_tool,
            web_scraper_tool
        ]
    )

    agent = Agent(
        tasks=[competition_analysis_task]
    )

    try:
        agent.run()
    except:
        return None

    response = agent.task_outputs.get("competition_analysis")
    if not response or not response.value:
        return None

    response = response.value

    try:
        new_response = "{" + response.lstrip().rstrip().split("{", 1)[1].rsplit("}", 1)[0] + "}"
        task_output = json.loads(new_response, strict=False)
    except Exception as e:
        print("Competition parsing failed: " + str(e))
        return None

    return task_output


load_dotenv()
domain = "godmodehq.com"
matrix = generate_competition_matrix(domain)
print(json.dumps(matrix))
