import time
from playwright.sync_api import sync_playwright

LANDREC_URL = "https://landrec.msa.maryland.gov/Pages/Login.aspx"
SDAT_URL = "https://sdat.dat.maryland.gov/RealProperty/Pages/default.aspx"


def login(page, email, password):
    """Log into landrec.msa.maryland.gov with 2FA support."""
    print("Opening land records site...")
    page.goto(LANDREC_URL)
    page.wait_for_load_state("networkidle")

    print("Entering credentials...")
    page.locator('input[type="email"], input[name*="email"], input[id*="email"]').first.fill(email)
    page.locator('input[type="password"], input[name*="password"], input[id*="password"]').first.fill(password)
    page.locator('input[type="submit"], button[type="submit"]').first.click()
    page.wait_for_timeout(3000)

    # Check if 2FA code is required
    page_text = page.content().lower()
    if any(word in page_text for word in ["verification", "code", "otp", "token", "authenticate"]):
        print("\n" + "="*50)
        print("TWO-FACTOR AUTHENTICATION REQUIRED")
        print("Check your email for a verification code.")
        code = input("Enter the verification code here: ").strip()
        print("="*50 + "\n")

        code_field = page.locator('input[type="text"], input[name*="code"], input[id*="code"]').first
        code_field.fill(code)
        page.locator('input[type="submit"], button[type="submit"]').first.click()
        page.wait_for_timeout(3000)

    print("Login successful!")


def search_by_name(page, last_name, first_name="", county="Anne Arundel"):
    """Search land records by name and return all results."""
    print(f"Searching for: {last_name}, {first_name}")

    # Navigate to search page
    search_links = page.locator('a:has-text("Search"), a:has-text("Land Records"), a:has-text("Name Search")')
    if search_links.count() > 0:
        search_links.first.click()
        page.wait_for_load_state("networkidle")

    # Try to fill in search fields
    try:
        # County selection
        county_select = page.locator('select[name*="county"], select[id*="county"]').first
        if county_select.count() > 0:
            county_select.select_option(label=county)

        # Name fields
        last_name_field = page.locator('input[name*="last"], input[id*="last"], input[placeholder*="Last"]').first
        last_name_field.fill(last_name)

        if first_name:
            first_name_field = page.locator('input[name*="first"], input[id*="first"], input[placeholder*="First"]').first
            first_name_field.fill(first_name)

        # Submit search
        page.locator('input[type="submit"], button[type="submit"], button:has-text("Search")').first.click()
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2000)

    except Exception as e:
        print(f"Search field error: {e}")

    return extract_results(page)


def extract_results(page):
    """Extract all results from the search results table."""
    results = []
    try:
        rows = page.locator("table tr").all()
        for row in rows[1:]:  # Skip header row
            cells = row.locator("td").all()
            if len(cells) >= 4:
                result = {
                    "grantor": cells[0].inner_text().strip() if len(cells) > 0 else "",
                    "grantee": cells[1].inner_text().strip() if len(cells) > 1 else "",
                    "instrument_type": cells[2].inner_text().strip() if len(cells) > 2 else "",
                    "date": cells[3].inner_text().strip() if len(cells) > 3 else "",
                    "book_page": cells[4].inner_text().strip() if len(cells) > 4 else "",
                    "instrument_number": cells[5].inner_text().strip() if len(cells) > 5 else "",
                    "description": cells[6].inner_text().strip() if len(cells) > 6 else "",
                    "link": ""
                }
                # Try to get document link
                link = row.locator("a").first
                if link.count() > 0:
                    result["link"] = link.get_attribute("href") or ""
                results.append(result)
    except Exception as e:
        print(f"Result extraction error: {e}")

    return results


def open_document(page, link):
    """Open an individual document and extract its text content."""
    if not link:
        return ""
    try:
        page.goto(link)
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2000)
        content = page.inner_text("body")
        page.go_back()
        page.wait_for_timeout(1000)
        return content[:5000]  # Limit to 5000 chars per document
    except Exception as e:
        print(f"Document open error: {e}")
        return ""


def get_sdat_info(page, address, county="02"):
    """Look up property info on SDAT for cross-reference."""
    try:
        page.goto(SDAT_URL)
        page.wait_for_load_state("networkidle")

        # Select Anne Arundel County (code 02)
        county_select = page.locator('select[name*="county"], select[id*="county"]').first
        if county_select.count() > 0:
            county_select.select_option(value=county)

        # Enter address
        address_parts = address.split(" ")
        house_number = address_parts[0] if address_parts else ""
        street_name = " ".join(address_parts[1:3]) if len(address_parts) > 1 else ""

        house_field = page.locator('input[name*="house"], input[id*="house"]').first
        if house_field.count() > 0:
            house_field.fill(house_number)

        street_field = page.locator('input[name*="street"], input[id*="street"]').first
        if street_field.count() > 0:
            street_field.fill(street_name)

        page.locator('input[type="submit"], button[type="submit"]').first.click()
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2000)

        return page.inner_text("body")[:3000]
    except Exception as e:
        print(f"SDAT lookup error: {e}")
        return ""


def deep_chain_search(page, owner_name, min_deeds=3):
    """
    Search going at least 3 deeds deep.
    Returns a list of all documents found in the chain.
    """
    all_documents = []
    names_to_search = set()
    names_searched = set()

    # Parse owner name
    parts = owner_name.split(",")
    last_name = parts[0].strip() if parts else owner_name
    first_name = parts[1].strip() if len(parts) > 1 else ""

    names_to_search.add((last_name, first_name))

    # Search all series types
    series_types = ["Land", "Judgments", "Financing Statements", "Wills", "Marriages"]

    while names_to_search:
        last, first = names_to_search.pop()
        if (last, first) in names_searched:
            continue
        names_searched.add((last, first))

        print(f"  Searching: {last}, {first}")
        results = search_by_name(page, last, first)

        for result in results:
            # Open each document to read full content
            if result.get("link"):
                result["full_text"] = open_document(page, result["link"])

            all_documents.append(result)

            # Extract new names to search (cross-reference)
            for name_field in ["grantor", "grantee"]:
                name = result.get(name_field, "")
                if name and len(name) > 2:
                    name_parts = name.split(",")
                    new_last = name_parts[0].strip()
                    new_first = name_parts[1].strip() if len(name_parts) > 1 else ""
                    if (new_last, new_first) not in names_searched:
                        names_to_search.add((new_last, new_first))

        # Limit cross-reference depth to prevent infinite loops
        if len(names_searched) > 15:
            print("  Max name depth reached, stopping cross-reference")
            break

    print(f"  Found {len(all_documents)} total documents across {len(names_searched)} name searches")
    return all_documents


def run_scraper(property_row, email, password):
    """
    Main scraper function. Takes a property row from Google Sheet
    and returns all scraped data.
    """
    # Extract owner name from row (flexible column matching)
    owner_name = ""
    address = ""
    for key, val in property_row.items():
        key_lower = key.lower()
        if any(w in key_lower for w in ["owner", "name", "grantor"]):
            owner_name = str(val)
        if any(w in key_lower for w in ["address", "situs", "property address"]):
            address = str(val)

    if not owner_name:
        print("No owner name found in row, skipping")
        return None

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        try:
            # Login
            login(page, email, password)

            # Get SDAT info for cross-reference
            sdat_data = ""
            if address:
                print("Checking SDAT records...")
                sdat_data = get_sdat_info(page, address)

            # Deep chain search - minimum 3 deeds
            print(f"Starting deep chain search for: {owner_name}")
            documents = deep_chain_search(page, owner_name, min_deeds=3)

            browser.close()

            return {
                "owner_name": owner_name,
                "address": address,
                "documents": documents,
                "sdat_data": sdat_data,
                "property_row": property_row
            }

        except Exception as e:
            print(f"Scraper error: {e}")
            browser.close()
            return None
