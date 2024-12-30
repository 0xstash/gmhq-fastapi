import sys
import os
import pytest
from unittest.mock import Mock, patch

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from extension.tools.apollo.apollo_tool import ApolloClient
from griptape.artifacts import ListArtifact, ErrorArtifact, TextArtifact


@pytest.fixture
def apollo_client():
    return ApolloClient(api_key="test_key")


@pytest.fixture
def mock_response():
    return {
        "pagination": {"total_entries": 2, "total_pages": 1, "page": 1, "per_page": 25},
        "people": [
            {
                "name": "John Doe",
                "title": "Marketing Manager",
                "email_status": "verified",
                "linkedin_url": "https://linkedin.com/in/johndoe",
                "city": "San Francisco",
                "state": "CA",
                "country": "United States",
                "organization": {
                    "name": "Tech Corp",
                    "website_url": "https://techcorp.com",
                    "linkedin_url": "https://linkedin.com/company/techcorp",
                },
                "seniority": "Director",
                "departments": ["Marketing"],
                "functions": ["Marketing"],
            }
        ],
    }


def test_search_people_success(apollo_client, mock_response):
    with patch("requests.post") as mock_post:
        mock_post.return_value.json.return_value = mock_response
        mock_post.return_value.raise_for_status.return_value = None

        test_params = {
            "values": {
                "person_titles": ["Marketing Manager"],
                "person_locations": ["San Francisco"],
                "organization_locations": ["United States"],
                "organization_num_employees_ranges": ["1,500"],
                "q_keywords": ["software", "ai"],
            }
        }

        result = apollo_client.search_people(test_params)

        # Print the results
        print("\nTest Results:")
        print("-------------")
        for item in result.value:
            print(item.value)
            print("-------------")

        assert isinstance(result, ListArtifact)
        assert len(result.value) == 2  # Pagination info + 1 person
        assert "Total Profiles Found: 2" in result.value[0].value
        assert "Name: John Doe" in result.value[1].value


def test_search_people_error(apollo_client):
    with patch("requests.post") as mock_post:
        mock_post.side_effect = Exception("API Error")

        test_params = {"values": {"person_titles": ["Marketing Manager"]}}

        result = apollo_client.search_people(test_params)

        # Print the error result
        print("\nError Test Result:")
        print("------------------")
        print(result.value)

        assert isinstance(result, ErrorArtifact)
        assert "Request failed" in result.value


def test_payload_formatting(apollo_client):
    with patch("requests.post") as mock_post:
        mock_post.return_value.json.return_value = {"people": []}
        mock_post.return_value.raise_for_status.return_value = None

        test_params = {
            "values": {
                "person_titles": ["CEO", "CTO"],
                "organization_num_employees_ranges": ["1,10", "11,50"],
                "q_keywords": ["ai", "ml"],
            }
        }

        result = apollo_client.search_people(test_params)

        # Print the formatted payload
        print("\nPayload Formatting Test:")
        print("------------------------")
        print("Called payload:", mock_post.call_args[1]["json"])

        called_payload = mock_post.call_args[1]["json"]
        assert called_payload["person_titles[]"] == ["CEO", "CTO"]
        assert called_payload["organization_num_employees_ranges[]"] == [
            "1,10",
            "11,50",
        ]
        assert called_payload["q_keywords"] == "ai, ml"
        assert called_payload["contact_email_status[]"] == ["verified"]
