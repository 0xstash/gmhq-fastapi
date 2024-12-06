import logging
import requests
from attrs import define, field
from griptape.artifacts import TextArtifact
from griptape.drivers import BaseWebScraperDriver


@define
class JinaWebScraperDriver(BaseWebScraperDriver):
    api_key: str = field(default="", kw_only=True)

    def fetch_url(self, url: str) -> str:
        headers = {"Authorization": f"Bearer {self.api_key}"}
        response = requests.get(f"https://r.jina.ai/{url}", headers=headers)

        if response.status_code != 200:
            logging.error(
                f"Error fetching URL: {response.status_code} - {response.text}"
            )
            raise Exception(
                f"Error fetching URL: {response.status_code} - {response.text}"
            )

        # Assuming the response is plain text as per the example provided
        page = response.text
        return page

    def extract_page(self, page: str) -> TextArtifact:
        # Directly return the page as TextArtifact since it's plain text
        return TextArtifact(page)
