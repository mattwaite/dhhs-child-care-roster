#!/usr/bin/env python3
"""
Download and parse Nebraska DHHS Child Care Roster.

This script downloads the latest Child Care Roster PDF from the Nebraska DHHS
website, saves it with a dated filename, parses it, and outputs a dated CSV file.

Usage:
    python download_and_parse.py

Output:
    - pdfs/ChildCareRoster_YYYY-MM-DD.pdf
    - data/child_care_providers_YYYY-MM-DD.csv
"""

import requests
import sys
from datetime import date
from pathlib import Path

from parse_childcare_roster import extract_providers_from_pdf, write_csv
from test_parse_consistency import run_all_tests


# URL for the Child Care Roster PDF
PDF_URL = "https://dhhs.ne.gov/licensure/Documents/ChildCareRoster.pdf"


def download_pdf(url, output_path):
    """
    Download PDF from URL and save to output_path.

    Returns True if successful, False otherwise.
    """
    print(f"Downloading PDF from {url}...")

    try:
        response = requests.get(url, timeout=60)
        response.raise_for_status()

        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'wb') as f:
            f.write(response.content)

        print(f"Saved PDF to {output_path}")
        return True

    except requests.RequestException as e:
        print(f"Error downloading PDF: {e}")
        return False


def main():
    script_dir = Path(__file__).parent

    # Get today's date for filenames
    today = date.today()
    date_str = today.strftime("%Y-%m-%d")

    # Define output paths
    pdf_dir = script_dir / "pdfs"
    data_dir = script_dir / "data"

    pdf_path = pdf_dir / f"ChildCareRoster_{date_str}.pdf"
    csv_path = data_dir / f"child_care_providers_{date_str}.csv"

    # Create directories if they don't exist
    pdf_dir.mkdir(parents=True, exist_ok=True)
    data_dir.mkdir(parents=True, exist_ok=True)

    # Download the PDF
    if not download_pdf(PDF_URL, pdf_path):
        sys.exit(1)

    # Parse the PDF
    print(f"Parsing {pdf_path}...")
    providers = extract_providers_from_pdf(pdf_path, download_date=date_str)

    # Run consistency tests
    print()
    passed, test_result = run_all_tests(
        pdf_path,
        providers,
        parse_func=extract_providers_from_pdf,
        download_date=date_str
    )
    print()
    print(test_result)
    print()

    if not passed:
        print("ERROR: Consistency tests failed. CSV not written.")
        sys.exit(1)

    # Write the CSV
    write_csv(providers, csv_path)

    print(f"Successfully processed {len(providers)} providers")
    print(f"  PDF: {pdf_path}")
    print(f"  CSV: {csv_path}")


if __name__ == "__main__":
    main()
