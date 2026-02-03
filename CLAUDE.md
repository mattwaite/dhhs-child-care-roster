# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python data extraction utility that parses the Nebraska DHHS child care provider roster PDF into structured CSV format. It uses `pdfplumber` to extract text and regex patterns to parse provider information.

The project includes automated monthly data collection via GitHub Actions.

## Running the Scripts

### Manual parsing (existing PDF)
```bash
# Default: reads ChildCareRoster.pdf, outputs child_care_providers.csv
python parse_childcare_roster.py

# With custom files
python parse_childcare_roster.py [input_pdf] [output_csv]
```

### Automated download and parse
```bash
# Downloads latest PDF from DHHS, saves dated files to pdfs/ and data/
python download_and_parse.py
```

## Dependencies

- Python 3.9+
- `pdfplumber` - PDF text extraction
- `requests` - HTTP download (for download_and_parse.py)

Install with: `pip install -r requirements.txt`

## Directory Structure

```
├── parse_childcare_roster.py   # Core parsing logic
├── download_and_parse.py       # Download and orchestration script
├── requirements.txt            # Python dependencies
├── data/                       # CSV output files (dated)
├── pdfs/                       # Archived PDF files (dated)
└── .github/workflows/          # GitHub Actions automation
```

## Automated Monthly Collection

A GitHub Actions workflow (`.github/workflows/monthly-download.yml`) runs automatically:
- **Schedule**: Noon UTC on the 15th of each month
- **Manual trigger**: Available via GitHub Actions "Run workflow" button

The workflow:
1. Downloads the PDF from `https://dhhs.ne.gov/licensure/Documents/ChildCareRoster.pdf`
2. Saves to `pdfs/ChildCareRoster_YYYY-MM-DD.pdf`
3. Parses and outputs `data/child_care_providers_YYYY-MM-DD.csv`
4. Commits and pushes the new files to the repository

## Architecture

**Core parser** (`parse_childcare_roster.py`):

1. **Constants** (lines 23-39): License type mappings (`LICENSE_TYPES`) and facility type validation (`FACILITY_TYPES`)

2. **Extraction Functions** (lines 42-169): 12+ specialized regex-based extractors:
   - `extract_license_number()` - Pattern: `FII?\d+|CCC\d+|PRE\d+|SAOC\d+`
   - `extract_phone()` - Pattern: `(XXX) XXX-XXXX`
   - `extract_zip_city()` - Pattern: `City NE XXXXX`
   - `extract_dates()` - Pattern: `MM/DD/YYYY`
   - Plus extractors for capacity, ages, hours, days, subsidy status, etc.

3. **Provider Block Parser** (`parse_provider_block()`): Orchestrates extraction for each provider entry, collecting up to 10 lines per provider

4. **PDF Processing**: Page-by-page iteration (skips page 1), maintains context (current ZIP, county) across entries

5. **CSV Output**: 21-column schema including Download_Date, license info, contact details, capacity, operating hours, and subsidy/accreditation status

**Orchestration script** (`download_and_parse.py`):
- Downloads PDF from DHHS website
- Saves dated copies of PDF and CSV files
- Passes download date to parser for inclusion in CSV records

## Key Patterns

- Each provider is parsed as a logical block of consecutive lines
- Context (ZIP code, county) persists across provider entries on the same page
- Provider names are cleaned of trailing "owned by" fragments
- Missing fields are handled gracefully (empty strings in output)
- Download_Date column tracks when each dataset was collected
