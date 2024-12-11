import scrapy
from scrapy.spiders import SitemapSpider
import csv
import logging
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings


# Add CSV Pipeline
class CSVPipeline:
    def __init__(self):
        self.file = None
        self.writer = None

    def open_spider(self, spider):
        self.file = open("meadoworks_data.csv", "w", newline="", encoding="utf-8")
        self.writer = csv.DictWriter(
            self.file, fieldnames=["url", "type", "title", "content"]
        )
        self.writer.writeheader()

    def close_spider(self, spider):
        self.file.close()

    def process_item(self, item, spider):
        self.writer.writerow(item)
        return item


class MeadoworksSpider(SitemapSpider):
    name = "meadoworks"
    allowed_domains = ["meadoworks.com"]
    sitemap_urls = ["https://www.meadoworks.com/sitemap.xml"]

    # Define rules for different URL patterns
    sitemap_rules = [
        ("/equipment/", "parse_equipment"),  # Equipment pages
        ("", "parse_generic"),  # All other pages
    ]

    def parse_equipment(self, response):
        """Parse equipment detail pages"""
        try:
            # Extract content using CSS selectors (adjust these based on the actual HTML structure)
            title = response.css("h1::text").get("").strip()
            content = " ".join(
                [p.strip() for p in response.css("div.entry-content p::text").getall()]
            )

            yield {
                "url": response.url,
                "type": "equipment",
                "title": title,
                "content": content,
            }
        except Exception as e:
            logging.error(f"Error parsing equipment page {response.url}: {str(e)}")

    def parse_generic(self, response):
        """Parse all other pages"""
        try:
            title = response.css("h1::text").get("").strip()
            content = " ".join(
                [p.strip() for p in response.css("div.entry-content p::text").getall()]
            )

            yield {
                "url": response.url,
                "type": "generic",
                "title": title,
                "content": content,
            }
        except Exception as e:
            logging.error(f"Error parsing page {response.url}: {str(e)}")


def main():
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler("meadoworks_crawler.log"),
            logging.StreamHandler(),
        ],
    )

    # Configure settings
    settings = get_project_settings()
    settings.set("ITEM_PIPELINES", {CSVPipeline: 300})

    # Run the spider using CrawlerProcess

    process = CrawlerProcess(settings)
    process.crawl(MeadoworksSpider)
    process.start()


if __name__ == "__main__":
    main()
