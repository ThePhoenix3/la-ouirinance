import requests
from bs4 import BeautifulSoup
import json
import os
import datetime
from dateutil.relativedelta import relativedelta

BASE_URL = "https://myofficebyc2e.com"
USERNAME = os.environ.get("BOUYGUES_USER", "")
PASSWORD = os.environ.get("BOUYGUES_PASS", "")


def scrape():
    if not USERNAME or not PASSWORD:
        print("BOUYGUES_USER / BOUYGUES_PASS not set, skipping")
        return

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
        print("Login failed – check credentials")
        return

    # Date range: 3 months back → today
    today = datetime.date.today()
    debut = today - relativedelta(months=3)

    url = (
        BASE_URL
        + "/details_bouygues.php"
        + f"?debut={debut.isoformat()}&fin={today.isoformat()}"
        + "&periode=month&mode=equipe&equipe=403"
    )

    resp = session.get(url, timeout=60)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    table = soup.find("table")

    if not table:
        print("No table found on page – keeping existing data")
        return

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
        print("0 rows scraped – keeping existing data")
        return

    output = {
        "scraped_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "rows": unique_rows,
    }

    save(output)
    print(f"Bouygues: {len(unique_rows)} unique rows → src/data_bouygues.json")


def save(output):
    output_path = os.path.join(os.path.dirname(__file__), "src", "data_bouygues.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    scrape()
