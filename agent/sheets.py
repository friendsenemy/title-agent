import gspread
from google.oauth2.service_account import Credentials
import os

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

def get_client():
    creds = Credentials.from_service_account_file("service_account.json", scopes=SCOPES)
    return gspread.authorize(creds)

def get_properties(sheet_id):
    """Read all properties from Google Sheet, sorted by highest delinquency first."""
    client = get_client()
    sheet = client.open_by_key(sheet_id).sheet1
    rows = sheet.get_all_records()

    # Find the delinquency column (flexible column name matching)
    delinquency_key = None
    if rows:
        for key in rows[0].keys():
            if any(word in key.lower() for word in ["delinq", "tax", "amount", "owed", "balance"]):
                delinquency_key = key
                break

    # Sort by delinquency amount descending
    if delinquency_key:
        def parse_amount(row):
            val = str(row.get(delinquency_key, "0")).replace("$", "").replace(",", "").strip()
            try:
                return float(val)
            except:
                return 0
        rows = sorted(rows, key=parse_amount, reverse=True)

    # Add row index for tracking (row 2 = first data row, row 1 = header)
    for i, row in enumerate(rows):
        row["_row_index"] = i + 2

    return rows

def mark_complete(sheet_id, row_index, status="Complete", notes=""):
    """Mark a row as complete in the Google Sheet."""
    client = get_client()
    sheet = client.open_by_key(sheet_id).sheet1
    headers = sheet.row_values(1)

    # Find or create Status and Notes columns
    status_col = None
    notes_col = None
    for i, h in enumerate(headers):
        if h.lower() == "status":
            status_col = i + 1
        if h.lower() in ["notes", "tip notes", "agent notes"]:
            notes_col = i + 1

    if not status_col:
        status_col = len(headers) + 1
        sheet.update_cell(1, status_col, "Status")

    if not notes_col:
        notes_col = len(headers) + 2
        sheet.update_cell(1, notes_col, "Agent Notes")

    sheet.update_cell(row_index, status_col, status)
    if notes:
        sheet.update_cell(row_index, notes_col, notes[:500])  # Truncate for cell limit

def get_pending_properties(sheet_id):
    """Return only properties that haven't been processed yet."""
    all_props = get_properties(sheet_id)
    pending = []
    for prop in all_props:
        status = str(prop.get("Status", "")).lower()
        if status not in ["complete", "skip", "error"]:
            pending.append(prop)
    return pending
