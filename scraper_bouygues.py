import requests
from bs4 import BeautifulSoup
import json
import os
import sys
import datetime
from dateutil.relativedelta import relativedelta

BASE_URL = "https://myofficebyc2e.com"
USERNAME = os.environ.get("BOUYGUES_USER", "")
PASSWORD = os.environ.get("BOUYGUES_PASS", "")


def scrape():
    if not USERNAME or not PASSWORD:
        print("ERROR: BOUYGUES_USER / BOUYGUES_PASS not set")
        sys.exit(1)

    session = requests.Session()

    # GET homepage to grab PHPSESSID cookie
    session.get(BASE_URL + "/", timeout=30)

    # POST login
    login_resp = session.post(
        BASE_URL + "/index.php",
        data={"username": USERNAME, "password": PASSWORD},
        timeout=30,
    )
    login_resp.raise_for_status()

    if "logout" not in login_resp.text.lower() and "déconnexion" not in login_resp.text.lower():
        print("ERROR: Login failed – check credentials")
        print(f"Response status: {login_resp.status_code}")
        print(f"Response body (first 500 chars): {login_resp.text[:500]}")
        sys.exit(1)

    # Date range: 3 months back → today
    today = datetime.date.today()
    debut = today - relativedelta(months=3)

    url = (
        BASE_URL
        + "/details_bouygues.php"
        + f"?debut={debut.isoformat()}&fin={today.isoformat()}"
        + "&periode=month&mode=equipe&equipe=428"
    )

    resp = session.get(url, timeout=60)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    table = soup.find("table")

    if not table:
        print("ERROR: No table found on page")
        print(f"Response body (first 500 chars): {resp.text[:500]}")
        sys.exit(1)

    headers = [th.get_text(strip=True) for th in table.find_all("th")]
    rows = []
    for tr in table.find_all("tr")[1:]:
        cells = [td.get_text(strip=True) for td in tr.find_all("td")]
        if cells and len(cells) == len(headers):
            rows.append(dict(zip(headers, cells)))

    # Deduplicate by num_contrat
    seen = set()
    unique_rows = []
    for row in rows:
        key = row.get("num_contrat", "")
        if key and key not in seen:
            seen.add(key)
            unique_rows.append(row)

    if len(unique_rows) == 0:
        print("ERROR: 0 rows scraped")
        print(f"Headers found: {headers}")
        sys.exit(1)

    existing = load_existing()
    merged = merge_rows(existing, unique_rows)

    output = {
        "scraped_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "rows": merged,
    }

    save(output)
    print(f"Bouygues: {len(unique_rows)} new, {len(merged)} total -> src/data_bouygues.json")


def load_existing():
    output_path = os.path.join(os.path.dirname(__file__), "src", "data_bouygues.json")
    if not os.path.exists(output_path):
        return []
    with open(output_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("rows", [])


def merge_rows(existing, fresh):
    by_key = {}
    for row in existing:
        key = row.get("num_contrat", "")
        if key:
            by_key[key] = row
    for row in fresh:
        key = row.get("num_contrat", "")
        if key:
            by_key[key] = row
    return list(by_key.values())


def save(output):
    output_path = os.path.join(os.path.dirname(__file__), "src", "data_bouygues.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    scrape()
