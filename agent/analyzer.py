import anthropic
import json
import os

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

SYSTEM_PROMPT = """You are a Title Intelligence Agent specializing in distressed real estate investing in Maryland. 
You analyze raw land records data and produce structured Title Intelligence Profile (TIP) reports.

You must search at least 3 deeds deep and identify ALL of the following defects if present:
- Broken chain of title (gap between grantor and grantee)
- Deeds of Trust with no recorded release
- Affidavits of Heirship with no follow-up executor deed or conveyance
- Divorce decrees with no deed transfer recorded
- Missing spouse signatures on deeds
- Quitclaim deeds within family transfers
- Old unpaid judgment liens
- IRS or state tax liens
- Lis pendens that went quiet with no resolution
- Living trust mismatches between tax records and recorded chain
- Ownership mismatches between SDAT and recorded chain
- Probate cases with no executor deed recorded
- Missing marital status on deeds
- Incorrect or missing notarization
- Multiple heirs with no probate or conveyance
- UCC filings attached to property
- Unprobated estates where heirs are presumed but not legally confirmed
- Deeds signed by someone without confirmed legal authority

You MUST respond with ONLY valid JSON, no other text. Use this exact structure:
{
  "chain_of_title": [
    {
      "date": "YYYY-MM-DD",
      "grantor": "name",
      "grantee": "name", 
      "instrument_type": "type",
      "book_page": "book/page",
      "notes": "any important observations"
    }
  ],
  "defects": [
    {
      "type": "defect name",
      "severity": "Critical|High|Medium|Low",
      "description": "plain english explanation",
      "cure_cost_min": 0,
      "cure_cost_max": 0,
      "investor_opportunity": "how this creates an opportunity"
    }
  ],
  "overall_severity": "Critical|High|Medium|Low|Clean",
  "pursue_deal": true,
  "financial": {
    "total_liens_estimated": 0,
    "delinquent_taxes": 0,
    "total_debt_estimated": 0,
    "estimated_equity": 0
  },
  "human_intelligence": {
    "all_names": ["name1", "name2"],
    "skip_trace_targets": [
      {
        "name": "full name",
        "relationship": "heir/owner/etc",
        "last_known_address": "address if found",
        "priority": "High|Medium|Low",
        "reason": "why contact them"
      }
    ],
    "motivation_indicators": ["indicator1", "indicator2"]
  },
  "strategy": {
    "acquisition_approach": "Tax Sale|Direct Outreach|Probate|Subject-To|Quiet Title|Walk Away",
    "leverage_points": ["point1", "point2"],
    "offer_structure": "description of how to structure the offer",
    "negotiation_notes": "key notes for negotiation"
  },
  "confirmation_checklist": [
    {
      "item": "what needs to be verified",
      "priority": "Critical|High|Medium",
      "where": "where to verify this",
      "impact": "what changes if this resolves differently"
    }
  ],
  "summary": "2-3 sentence executive summary of the deal"
}"""


def analyze_property(scraped_data, property_row):
    """
    Send scraped land records data to Claude for analysis.
    Returns a structured TIP report.
    """
    # Build the prompt
    owner_name = scraped_data.get("owner_name", "Unknown")
    address = scraped_data.get("address", "Unknown")
    documents = scraped_data.get("documents", [])
    sdat_data = scraped_data.get("sdat_data", "")

    # Get financial info from the spreadsheet row
    tax_delinquency = 0
    assessed_value = 0
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

    # Format documents for the prompt
    docs_text = ""
    for i, doc in enumerate(documents[:30]):  # Limit to 30 docs to stay within token limits
        docs_text += f"\n--- Document {i+1} ---\n"
        docs_text += f"Type: {doc.get('instrument_type', 'Unknown')}\n"
        docs_text += f"Grantor: {doc.get('grantor', '')}\n"
        docs_text += f"Grantee: {doc.get('grantee', '')}\n"
        docs_text += f"Date: {doc.get('date', '')}\n"
        docs_text += f"Book/Page: {doc.get('book_page', '')}\n"
        docs_text += f"Description: {doc.get('description', '')}\n"
        if doc.get("full_text"):
            docs_text += f"Document Text (excerpt): {doc['full_text'][:500]}\n"

    prompt = f"""Analyze this property for title defects and investment opportunities.

PROPERTY DETAILS:
Address: {address}
Owner of Record: {owner_name}
Tax Delinquency: ${tax_delinquency:,.2f}
Assessed Value: ${assessed_value:,.2f}
County: Anne Arundel County, Maryland

SDAT ASSESSMENT DATA:
{sdat_data[:1000] if sdat_data else "Not available"}

LAND RECORDS FOUND ({len(documents)} documents):
{docs_text}

IMPORTANT INSTRUCTIONS:
1. Build the complete chain of title in chronological order going back at least 3 deeds
2. Flag EVERY defect you find, no matter how minor
3. Identify ALL names that appear in the documents for skip tracing
4. Assess the investment opportunity and recommended strategy
5. Create a detailed confirmation checklist for in-person verification
6. Consider Maryland-specific laws (ground rent, homestead tax credit, Maryland estate law)

Respond with ONLY the JSON structure specified. No preamble or explanation."""

    print("  Sending to Claude for analysis...")
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}]
    )

    raw_text = response.content[0].text.strip()

    # Parse JSON response
    try:
        # Remove any markdown code blocks if present
        if raw_text.startswith("```"):
            raw_text = raw_text.split("```")[1]
            if raw_text.startswith("json"):
                raw_text = raw_text[4:]
        analysis = json.loads(raw_text)
    except json.JSONDecodeError as e:
        print(f"  JSON parse error: {e}")
        analysis = {
            "chain_of_title": [],
            "defects": [],
            "overall_severity": "Unknown",
            "pursue_deal": False,
            "financial": {},
            "human_intelligence": {"all_names": [], "skip_trace_targets": [], "motivation_indicators": []},
            "strategy": {"acquisition_approach": "Manual Review Required"},
            "confirmation_checklist": [],
            "summary": f"Analysis failed - manual review required. Raw response: {raw_text[:200]}"
        }

    return analysis
