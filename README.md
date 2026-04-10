# Title Intelligence Agent
### Anne Arundel County, Maryland

An AI-powered title research agent that automatically analyzes tax delinquent properties, identifies title defects, and generates Title Intelligence Profile (TIP) reports displayed on a live dashboard.

---

## What This Does

1. **Reads** your Google Sheet of tax delinquent properties
2. **Logs into** landrec.msa.maryland.gov (handles 2FA automatically)
3. **Searches** 3+ deeds deep for every property
4. **Analyzes** with Claude AI for title defects
5. **Generates** a full TIP report for each property
6. **Saves** results to your GitHub dashboard
7. **Updates** the Google Sheet with completion status

---

## Setup Instructions

### Step 1: Clone this Repository
```
git clone https://github.com/YOUR-USERNAME/title-agent.git
cd title-agent
```

### Step 2: Install Dependencies
```
pip install -r requirements.txt
playwright install
```

### Step 3: Set Up Google Sheets Access
1. Go to https://console.cloud.google.com
2. Create a new project
3. Enable "Google Sheets API" and "Google Drive API"
4. Create a Service Account
5. Download the JSON key file
6. Rename it to `service_account.json` and place it in the project root
7. Share your Google Sheet with the service account email address

### Step 4: Create Your .env File
```
cp .env.example .env
```
Edit `.env` and fill in:
- `ANTHROPIC_API_KEY` - from console.anthropic.com
- `LANDREC_EMAIL` - your land records login email
- `LANDREC_PASSWORD` - your land records password
- `GOOGLE_SHEET_ID` - from your Google Sheet URL

### Step 5: Set Up GitHub Pages
1. Push this repo to GitHub
2. Go to Settings → Pages
3. Set Source to "main branch" and folder to "/dashboard"
4. Your dashboard will be live at: https://YOUR-USERNAME.github.io/title-agent

### Step 6: Run the Agent
```
cd agent
python main.py
```

The browser will open. When prompted for the 2FA code, check your email and paste it in.

### Step 7: Push Results to Dashboard
After the agent runs:
```
git add .
git commit -m "New TIP reports"
git push
```

Your dashboard updates automatically!

---

## Google Sheet Format

Your sheet should have columns for:
- Property address (any column with "address" in the name)
- Owner name (any column with "owner" or "name")
- Tax delinquency amount (any column with "delinq", "tax", or "amount")
- Assessed value (any column with "assessed" or "value")

The agent will automatically detect these columns.

---

## File Structure
```
title-agent/
├── agent/
│   ├── main.py          # Run this to start the agent
│   ├── scraper.py       # Browser automation
│   ├── analyzer.py      # Claude AI analysis
│   ├── sheets.py        # Google Sheets integration
│   └── geocoder.py      # Address → coordinates
├── dashboard/
│   ├── index.html       # Your live dashboard
│   └── data/
│       └── reports.json # Generated TIP reports
├── requirements.txt
├── .env.example
└── README.md
```

---

## Dashboard Features

- **Interactive map** with color-coded severity markers
- **Filter by severity** (Critical / High / Medium / Low)
- **"Pursue Only"** filter to focus on best opportunities
- **Full TIP report** modal with chain of title, defects, strategy
- **Skip trace targets** with priority rankings
- **Confirmation checklist** for in-person verification

---

## Notes

- The agent handles 2FA by pausing and asking you to paste the code
- Progress is saved after each property so you can resume if interrupted
- The agent searches minimum 3 deeds deep on every property
- All results are pushed to your Google Sheet automatically
