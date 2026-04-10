import os
import json
import uuid
from datetime import datetime
from dotenv import load_dotenv

from sheets import get_pending_properties, mark_complete
from scraper import run_scraper
from analyzer import analyze_property
from geocoder import geocode_address

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
LANDREC_EMAIL = os.getenv("LANDREC_EMAIL")
LANDREC_PASSWORD = os.getenv("LANDREC_PASSWORD")
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID")

REPORTS_PATH = os.path.join(os.path.dirname(__file__), "..", "dashboard", "data", "reports.json")


def load_existing_reports():
    """Load existing reports from JSON file."""
    if os.path.exists(REPORTS_PATH):
        with open(REPORTS_PATH, "r") as f:
            return json.load(f)
    return []


def save_reports(reports):
    """Save all reports to JSON file for dashboard."""
    os.makedirs(os.path.dirname(REPORTS_PATH), exist_ok=True)
    with open(REPORTS_PATH, "w") as f:
        json.dump(reports, f, indent=2)
    print(f"Saved {len(reports)} reports to dashboard/data/reports.json")


def build_report(property_row, scraped_data, analysis):
    """Build a complete TIP report object for the dashboard."""

    address = scraped_data.get("address", "Unknown Address")
    owner_name = scraped_data.get("owner_name", "Unknown Owner")

    # Get financial data from row
    tax_delinquency = 0
    assessed_value = 0
    parcel_number = ""
    for key, val in property_row.items():
        key_lower = key.lower()
        val_str = str(val).replace("$", "").replace(",", "").strip()
        if any(w in key_lower for w in ["delinq", "tax", "amount", "owed", "balance"]):
            try:
                tax_delinquency = float(val_str)
            except:
                pass
        if any(w in key_lower for w in ["assessed", "value", "apprais"]):
            try:
                assessed_value = float(val_str)
            except:
                pass
        if any(w in key_lower for w in ["parcel", "account", "id"]):
            parcel_number = str(val)

    # Geocode the address
    print(f"  Geocoding: {address}")
    lat, lng = geocode_address(address)

    # Count defects by severity
    defects = analysis.get("defects", [])
    severity_counts = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0}
    for d in defects:
        sev = d.get("severity", "Low")
        severity_counts[sev] = severity_counts.get(sev, 0) + 1

    return {
        "id": str(uuid.uuid4()),
        "address": address,
        "parcel_number": parcel_number,
        "lat": lat,
        "lng": lng,
        "county": "Anne Arundel County, MD",
        "owner_of_record": owner_name,
        "tax_delinquency": tax_delinquency,
        "assessed_value": assessed_value,
        "status": "complete",
        "processed_date": datetime.now().strftime("%Y-%m-%d"),
        "deeds_searched": len(scraped_data.get("documents", [])),
        "overall_severity": analysis.get("overall_severity", "Unknown"),
        "pursue_deal": analysis.get("pursue_deal", False),
        "severity_counts": severity_counts,
        "summary": analysis.get("summary", ""),
        "defects": defects,
        "chain_of_title": analysis.get("chain_of_title", []),
        "financial": analysis.get("financial", {}),
        "human_intelligence": analysis.get("human_intelligence", {}),
        "strategy": analysis.get("strategy", {}),
        "confirmation_checklist": analysis.get("confirmation_checklist", [])
    }


def process_property(property_row):
    """Process a single property end-to-end."""
    address = ""
    for key, val in property_row.items():
        if any(w in key.lower() for w in ["address", "situs"]):
            address = str(val)
            break

    print(f"\n{'='*60}")
    print(f"PROCESSING: {address}")
    print(f"{'='*60}")

    try:
        # Step 1: Scrape land records
        print("STEP 1: Scraping land records...")
        scraped_data = run_scraper(property_row, LANDREC_EMAIL, LANDREC_PASSWORD)

        if not scraped_data:
            print("Scraping failed, skipping property")
            mark_complete(GOOGLE_SHEET_ID, property_row["_row_index"], "Error", "Scraping failed")
            return None

        # Step 2: Analyze with Claude
        print("STEP 2: Analyzing with Claude AI...")
        analysis = analyze_property(scraped_data, property_row)

        # Step 3: Build report
        print("STEP 3: Building TIP report...")
        report = build_report(property_row, scraped_data, analysis)

        # Step 4: Mark complete in Google Sheet
        defect_summary = f"{len(analysis.get('defects', []))} defects | {analysis.get('overall_severity', 'Unknown')} severity"
        mark_complete(GOOGLE_SHEET_ID, property_row["_row_index"], "Complete", defect_summary)

        print(f"SUCCESS: {address} - {defect_summary}")
        return report

    except Exception as e:
        print(f"ERROR processing {address}: {e}")
        mark_complete(GOOGLE_SHEET_ID, property_row["_row_index"], "Error", str(e)[:200])
        return None


def main():
    print("\n" + "="*60)
    print("TITLE INTELLIGENCE AGENT")
    print("Anne Arundel County, Maryland")
    print("="*60)

    # Load existing reports
    reports = load_existing_reports()
    print(f"Found {len(reports)} existing reports")

    # Get pending properties from Google Sheet
    print("Reading Google Sheet...")
    properties = get_pending_properties(GOOGLE_SHEET_ID)
    print(f"Found {len(properties)} properties to process")

    if not properties:
        print("No pending properties found. All done!")
        return

    print(f"\nStarting processing. Properties will be sorted by highest delinquency first.")
    print("Note: The browser will open for the first property login. You will need to enter your 2FA code.")
    print("\nPress ENTER to begin or CTRL+C to cancel...")
    input()

    processed = 0
    errors = 0

    for i, property_row in enumerate(properties):
        print(f"\nProperty {i+1} of {len(properties)}")
        report = process_property(property_row)

        if report:
            reports.append(report)
            processed += 1
            # Save after each property in case of interruption
            save_reports(reports)
        else:
            errors += 1

        # Small delay between properties
        if i < len(properties) - 1:
            print("Waiting 3 seconds before next property...")
            import time
            time.sleep(3)

    print(f"\n{'='*60}")
    print(f"COMPLETE: {processed} processed, {errors} errors")
    print(f"Reports saved to dashboard/data/reports.json")
    print(f"Push to GitHub to update your dashboard!")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
