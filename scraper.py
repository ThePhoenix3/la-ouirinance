import requests
from bs4 import BeautifulSoup
import json
import os

URL = "https://vad.proxad.net/stats/carnet.pl"

ACCOUNTS = [
    (os.environ.get("SCRAPER_USER_1", ""), os.environ.get("SCRAPER_PASS_1", "")),
    (os.environ.get("SCRAPER_USER_2", ""), os.environ.get("SCRAPER_PASS_2", "")),
]

def fetch_rows(username, password):
    response = requests.get(URL, auth=(username, password))
    response.encoding = "ISO-8859-15"
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    table = soup.find("table")

    headers = [th.get_text(strip=True) for th in table.find_all("th")]
    rows = []
    for tr in table.find_all("tr")[1:]:
        cells = [td.get_text(strip=True) for td in tr.find_all("td")]
        if cells:
            rows.append(dict(zip(headers, cells)))

    return rows

def scrape():
    all_rows = []
    for i, (user, password) in enumerate(ACCOUNTS, start=1):
        if not user:
            print(f"Account {i}: no credentials, skipping")
            continue
        rows = fetch_rows(user, password)
        print(f"Account {i} ({user}): {len(rows)} rows")
        all_rows.extend(rows)

    # Deduplicate by id_abo
    seen = set()
    unique_rows = []
    for row in all_rows:
        key = row.get("id_abo", "")
        if key not in seen:
            seen.add(key)
            unique_rows.append(row)

    output_path = os.path.join(os.path.dirname(__file__), "src", "data.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(unique_rows, f, ensure_ascii=False, indent=2)

    print(f"Total: {len(unique_rows)} unique rows → src/data.json")

if __name__ == "__main__":
    scrape()
