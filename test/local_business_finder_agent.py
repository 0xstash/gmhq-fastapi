import requests
import json
import questionary
import rich
import time
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, TextColumn


url = "https://google.serper.dev/places"

query = questionary.text("What kind of local business are you looking for ?").ask()

payload = json.dumps({"q": query})
headers = {
    "X-API-KEY": "e34fbe2f7e92e49bea180b5f607771c6c0287e21",
    "Content-Type": "application/json",
}

console = Console()

# Add loading animation
with Progress(
    SpinnerColumn(),
    TextColumn("[bold blue]Searching for businesses..."),
    transient=True,
) as progress:
    progress.add_task("searching", total=None)
    response = requests.request("POST", url, headers=headers, data=payload)
    # Add a 3 second delay
    time.sleep(3)


def print_search_results(data):
    # Print search parameters in a panel
    search_params = Text.assemble(
        ("Search Query: ", "bold cyan"),
        (f"{data['searchParameters']['q']}\n", "white"),
        ("Type: ", "bold cyan"),
        (f"{data['searchParameters']['type']}\n", "white"),
        ("Engine: ", "bold cyan"),
        (f"{data['searchParameters']['engine']}", "white"),
    )
    console.print(Panel(search_params, title="Search Parameters", border_style="blue"))

    # Create table for places
    table = Table(show_header=True, header_style="bold magenta", border_style="blue")
    table.add_column("#", style="dim", width=3)
    table.add_column("Business", style="cyan")
    table.add_column("Category", style="yellow")
    table.add_column("Address", style="green")
    table.add_column("Rating", justify="center")
    table.add_column("Phone", style="yellow")
    table.add_column("Website", style="blue")

    # Add rows to table
    for place in data["places"]:
        table.add_row(
            str(place["position"]),
            place["title"],
            place.get("category", "N/A"),
            place.get("address", "N/A"),
            f"⭐ {place.get('rating', 'N/A')}/5.0 ({place.get('ratingCount', 'N/A')})",
            place.get("phoneNumber", "N/A"),
            place.get("website", "N/A"),
        )

    # Print the table
    console.print("\n")
    console.print(Panel(table, title="Business Results", border_style="blue"))


# Use the function with your JSON response
print_search_results(response.json())
