from __future__ import annotations
from griptape.artifacts import ListArtifact, ErrorArtifact, TextArtifact
from griptape.tools import BaseTool
from griptape.utils.decorators import activity
from schema import Schema, Literal
from attr import define, field
import requests
import logging


@define
class ApolloClient(BaseTool):
    ENDPOINT = "https://api.apollo.io/v1/mixed_people/search"

    api_key: str = field(kw_only=True)
    timeout: int = field(default=10, kw_only=True)

    @activity(
        config={
            "description": "Searches for people on Apollo.io based on specified criteria",
            "schema": Schema(
                {
                    Literal(
                        "person_titles",
                        description="Job titles held by the people you want to find (e.g., ['marketing manager', 'research analyst'])",
                    ): [str],
                    Literal(
                        "person_locations",
                        description="Locations where people live (e.g., ['chicago', 'london'])",
                    ): [str],
                    Literal(
                        "organization_locations",
                        description="Headquarters locations of companies (e.g., ['london', 'chicago'])",
                    ): [str],
                    Literal(
                        "organization_num_employees_ranges",
                        description="Company size ranges (e.g., ['1,10', '11,50', '51,200'])",
                    ): [str],
                    Literal(
                        "organization_keyword_tags",
                        description="Keywords to filter the search results (e.g., ['software', 'sales'])",
                    ): [str],
                }
            ),
        }
    )
    def search_people(self, params: dict) -> ListArtifact | ErrorArtifact:
        payload = {}

        # Handle person titles
        if person_titles := params["values"].get("person_titles"):
            payload["person_titles"] = person_titles

        # Handle person locations
        if person_locations := params["values"].get("person_locations"):
            payload["person_locations"] = person_locations

        # Handle organization locations
        if org_locations := params["values"].get("organization_locations"):
            payload["organization_locations"] = org_locations

        # Handle organization employee ranges
        if emp_ranges := params["values"].get("organization_num_employees_ranges"):
            payload["organization_num_employees_ranges"] = emp_ranges

        # Handle keywords
        if keywords := params["values"].get("organization_keyword_tags"):
            payload["organization_keyword_tags"] = ", ".join(keywords)

        # Set fixed pagination parameters
        payload["page"] = 1
        payload["per_page"] = 10
        payload["contact_email_status[]"] = ["verified"]

        headers = {
            "accept": "application/json",
            "Cache-Control": "no-cache",
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
        }

        try:
            response = requests.post(
                self.ENDPOINT, json=payload, headers=headers, timeout=self.timeout
            )
            logging.info(f"Request payload: {payload}")
            response.raise_for_status()
            data = response.json()
            logging.info(f"Response data: {data}")
            pagination = data.get("pagination", {})
            total_entries = pagination.get("total_entries", 0)
            total_pages = pagination.get("total_pages", 0)
            logging.info(f"Total entries: {total_entries}")
            # Assuming the response contains a list of people
            people_data = data.get("people", [])
            logging.info(f"People data length: {len(people_data)}")
            formatted_people = []

            # Add pagination information as the first item in the list
            pagination_info = TextArtifact(
                f"""
                Pagination Information:
                - Total Profiles Found: {total_entries}
                - Total Pages: {total_pages}
                - Current Page: {pagination.get('page', 1)}
                - Results Per Page: {pagination.get('per_page', 10)}
                """
            )
            formatted_people.append(pagination_info)

            for person in people_data:
                org = person.get("organization", {})
                formatted_person = {
                    "name": person.get("name"),
                    "title": person.get("title"),
                    "headline": person.get("headline"),
                    "email_status": person.get("email_status"),
                    "linkedin_url": person.get("linkedin_url"),
                    "location": f"{person.get('city', '')}, {person.get('state', '')}, {person.get('country', '')}",
                    "company": {
                        "name": org.get("name"),
                        "website": org.get("website_url"),
                        "linkedin": org.get("linkedin_url"),
                    },
                    "seniority": person.get("seniority"),
                    "departments": person.get("departments", []),
                    "functions": person.get("functions", []),
                }
                formatted_people.append(
                    TextArtifact(
                        f"""
                    Name: {formatted_person['name']}
                    Title: {formatted_person['title']}
                    Headline: {formatted_person['headline']}
                    Email Status: {formatted_person['email_status']}
                    LinkedIn: {formatted_person['linkedin_url']}
                    Location: {formatted_person['location']}
                    Company: {formatted_person['company']['name']}
                    Company Website: {formatted_person['company']['website']}
                    Company LinkedIn: {formatted_person['company']['linkedin']}
                    Seniority: {formatted_person['seniority']}
                    Departments: {', '.join(formatted_person['departments'])}
                    Functions: {', '.join(formatted_person['functions'])}
                    """
                    )
                )

            return ListArtifact(formatted_people)
        except requests.exceptions.RequestException as e:
            logging.error(f"Request failed: {e}")
            logging.error(f"Response content: {response.text}")
            return ErrorArtifact(f"Request failed: {e}")
        except ValueError:
            logging.error("Failed to decode JSON from response")
            return ErrorArtifact("Failed to decode JSON from response")
