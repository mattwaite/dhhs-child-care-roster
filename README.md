# Nebraska DHHS Child Care Provider Roster

A collection of CSVs parsed from the Nebraska Department of Health and Human Services child care provider roster PDF.

## About

The Nebraska DHHS publishes a [Child Care Licensing Roster](https://dhhs.ne.gov/licensure/Documents/ChildCareRoster.pdf) as a PDF document containing all licensed child care providers in the state. This repository:

1. Automatically downloads the roster PDF monthly
2. Parses provider data into structured CSV format
3. Archives historical snapshots for tracking changes over time

## Data

### CSV Files

Parsed data files are stored in the `data/` directory with filenames like `child_care_providers_YYYY-MM-DD.csv`.

Each CSV contains 21 columns:

| Column | Description |
|--------|-------------|
| `Download_Date` | Date the PDF was downloaded |
| `Zip_Code` | Provider's ZIP code |
| `County` | Nebraska county |
| `Provider_Name` | Name of the child care facility |
| `License_Number` | State license number (e.g., FI12640, CCC9578) |
| `License_Type` | Type of facility (see below) |
| `Owner_Name` | Owner/operator name |
| `Effective_Date` | License effective date |
| `Address` | Street address |
| `City` | City |
| `State` | State (NE) |
| `Phone` | Contact phone number |
| `Capacity` | Maximum number of children |
| `Ages` | Age range served (e.g., "6 WKS To 13 YRS") |
| `Hours` | Operating hours (e.g., "0600 To 1800") |
| `Days_Open` | Days of operation (e.g., "MTWTHF") |
| `Currently_Accepts_Subsidy` | Y/N |
| `Willing_To_Accept_Subsidy` | Y/N |
| `Does_Not_Accept_Subsidy` | Y/N |
| `Step_Up_Quality` | Quality rating (1-5) |
| `Accredited` | Y/N |

### License Types

- **Family Child Care Home I** (FI) - Up to 10 children
- **Family Child Care Home II** (FII) - Up to 12 children
- **Child Care Center** (CCC) - Larger facilities
- **Preschool** (PRE) - Preschool programs
- **School-Age-Only Child Care Center** (SAOC) - Before/after school care

### PDF Archives

Original PDF files are stored in `pdfs/` for reference and verification.

## Automated Collection

A GitHub Actions workflow runs on the 15th of each month to download and parse the latest roster. You can also trigger it manually from the Actions tab.

## Running Locally

### Requirements

- Python 3.9+
- Dependencies: `pdfplumber`, `requests`

### Installation

```bash
git clone https://github.com/mattwaite/dhhs-child-care-roster.git
cd dhhs-child-care-roster
pip install -r requirements.txt
```

### Usage

**Download latest roster and parse:**
```bash
python download_and_parse.py
```

This will:
1. Download the current PDF from DHHS
2. Run consistency tests to validate the parsed data
3. Save dated files to `pdfs/` and `data/`

**Parse an existing PDF:**
```bash
python parse_childcare_roster.py [input.pdf] [output.csv]
```

**Run consistency tests standalone:**
```bash
python test_parse_consistency.py pdfs/ChildCareRoster_YYYY-MM-DD.pdf
```

## Data Quality

The parsing process includes automated consistency tests that validate:

- **Parsing determinism** - Same PDF produces identical results across runs
- **Data quality** - License numbers, phone formats, dates, and ZIP codes match expected patterns
- **Field completeness** - Key fields are populated in 90%+ of records

If tests fail, the CSV is not written, ensuring only validated data is saved.

## Source

Data is sourced from the Nebraska Department of Health and Human Services:
https://dhhs.ne.gov/licensure/Documents/ChildCareRoster.pdf

## License

MIT License - See [LICENSE](LICENSE) for details.
