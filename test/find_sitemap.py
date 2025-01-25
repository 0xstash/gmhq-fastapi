from trafilatura import fetch_url
from trafilatura.sitemaps import sitemap_search


def get_sitemap_urls(domain):
    """
    Fetch and parse sitemap URLs from a given domain

    Args:
        domain (str): The website domain to fetch sitemap from

    Returns:
        list: List of URLs found in the sitemap
    """
    # Fetch all URLs from potential sitemaps
    urls = sitemap_search(domain)

    if urls:
        print(f"Found {len(urls)} URLs in sitemap:")
        for url in urls:
            print(f"- {url}")
        return urls
    else:
        print(f"No sitemap found for {domain}")
        return []


if __name__ == "__main__":
    # Domain to analyze
    # domain = "https://www.origamiagents.com/"
    domain = "https://www.operator.ai/"

    # Get sitemap URLs
    sitemap_urls = get_sitemap_urls(domain)
