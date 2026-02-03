#!/usr/bin/env python3
"""
Parse Nebraska DHHS Child Care Licensing Roster PDF into CSV.

This script uses pdfplumber to extract child care provider data from the
Child Care Roster PDF and outputs a structured CSV file with one row per provider.

Usage:
    python parse_childcare_roster.py [input_pdf] [output_csv]

    If no arguments provided, defaults to:
        input:  ChildCareRoster.pdf (in same directory)
        output: child_care_providers.csv
"""

import pdfplumber
import csv
import re
import sys
from pathlib import Path


# License type patterns
LICENSE_PATTERNS = {
    'FII': 'Family Child Care Home II',
    'FI': 'Family Child Care Home I',
    'CCC': 'Child Care Center',
    'PRE': 'Preschool',
    'SAOC': 'School-Age-Only Child Care Center',
}

# Facility type strings as they appear in the PDF
FACILITY_TYPES = [
    'Family Child Care Home II',
    'Family Child Care Home I',
    'Child Care Center',
    'School-Age-Only Child Care Center',
    'Preschool',
]


def extract_license_number(text):
    """
    Extract license number from text (e.g., FI12640, CCC9578, PRE9025).
    """
    match = re.search(r'\b(FII?\d+|CCC\d+|PRE\d+|SAOC\d+)\b', text)
    return match.group(1) if match else ''


def extract_capacity(text):
    """
    Extract capacity from text like 'Capacity: 10'.
    """
    match = re.search(r'Capacity:\s*(\d+)', text)
    return match.group(1) if match else ''


def extract_days(text):
    """
    Extract days of week from text like 'Days of Week Open: MTWTHF'.
    """
    match = re.search(r'Days of Week Open:\s*([A-Z]+)', text)
    return match.group(1) if match else ''


def extract_ages(text):
    """
    Extract ages from text like 'Ages: 6 WKS To 13 YRS'.
    """
    match = re.search(r'Ages:\s*(.+?)(?:\s*$)', text)
    return match.group(1).strip() if match else ''


def extract_hours(text):
    """
    Extract hours from text like 'Hours: 0600 To 1800'.
    """
    match = re.search(r'Hours:\s*(\d{4})\s*To\s*(\d{4})', text)
    if match:
        return f"{match.group(1)} To {match.group(2)}"
    return ''


def extract_phone(text):
    """
    Extract phone number from text.
    """
    match = re.match(r'^\((\d{3})\)\s*(\d{3})-?(\d{4})', text)
    if match:
        return f"({match.group(1)}) {match.group(2)}-{match.group(3)}"
    return ''


def extract_effective_date(text):
    """
    Extract effective date from text like '04/30/2024'.
    """
    match = re.search(r'\b(\d{2}/\d{2}/\d{4})\b', text)
    return match.group(1) if match else ''


def extract_city_state_zip(text):
    """
    Extract city, state, zip from text like 'Arlington NE 68002'.
    """
    # Pattern: City Name NE ZIPCODE
    # City names typically are 1-3 words, don't include NEBRASKA
    match = re.search(r'\b([A-Za-z][A-Za-z\s\.]{0,30}?)\s+NE\s+(\d{5})\b', text)
    if match:
        city = match.group(1).strip()
        # Don't include "NEBRASKA" as part of city name
        city = re.sub(r'\bNEBRASKA\b', '', city, flags=re.IGNORECASE).strip()
        if city:
            return city, 'NE', match.group(2)
    return '', '', ''


def extract_facility_type(text):
    """
    Extract facility type from text.
    """
    for ftype in FACILITY_TYPES:
        if ftype in text:
            return ftype
    return ''


def extract_yn_value(line, prefix):
    """
    Extract Y/N value from a line like 'Currently Accepts Subsidy? Y'.
    """
    if prefix in line:
        # Look for Y or N after the prefix
        match = re.search(rf'{re.escape(prefix)}\s*([YN])?', line)
        if match and match.group(1):
            return match.group(1)
    return ''


def extract_step_up_quality(line):
    """
    Extract Step Up To Quality rating from line.
    """
    match = re.search(r'Step Up To Quality:\s*(\d+)?', line)
    if match and match.group(1):
        return match.group(1)
    return ''


def extract_accredited(line):
    """
    Extract accreditation status from line.
    """
    match = re.search(r'Accredited\?\s*([YN])?', line)
    if match and match.group(1):
        return match.group(1)
    return ''


def clean_provider_name(name):
    """
    Clean up provider name by removing trailing 'owned by' or 'OWNED BY' fragments.
    """
    # Remove trailing "owned by" or partial fragments
    name = re.sub(r'\s+owned by\s*$', '', name, flags=re.IGNORECASE)
    name = re.sub(r'\s+OWNED BY\s*$', '', name)
    name = re.sub(r'\s+owned\s*$', '', name, flags=re.IGNORECASE)
    name = re.sub(r'\s+ob\s*$', '', name, flags=re.IGNORECASE)  # partial "owned by" -> "ob"
    return name.strip()


def parse_provider_block(lines, current_zip, current_county, download_date=''):
    """
    Parse a block of lines representing a single provider.
    Returns a dictionary with provider data.
    """
    provider = {
        'Download_Date': download_date,
        'Zip_Code': current_zip,
        'County': current_county,
        'Provider_Name': '',
        'License_Number': '',
        'License_Type': '',
        'Owner_Name': '',
        'Effective_Date': '',
        'Address': '',
        'City': '',
        'State': 'NE',
        'Phone': '',
        'Capacity': '',
        'Ages': '',
        'Hours': '',
        'Days_Open': '',
        'Currently_Accepts_Subsidy': '',
        'Willing_To_Accept_Subsidy': '',
        'Does_Not_Accept_Subsidy': '',
        'Step_Up_Quality': '',
        'Accredited': '',
    }

    if not lines:
        return provider

    # Combine all lines for searching
    all_text = ' '.join(lines)

    # Line 1: Provider Name, License Number, Address, Capacity, Days
    line1 = lines[0] if len(lines) > 0 else ''

    # Extract license number first
    provider['License_Number'] = extract_license_number(line1)
    provider['Capacity'] = extract_capacity(line1)
    provider['Days_Open'] = extract_days(line1)

    # Extract address (between license number and Capacity)
    if provider['License_Number']:
        parts = line1.split(provider['License_Number'])
        if len(parts) >= 2:
            # Provider name is before license number
            name_part = parts[0].strip()
            # Remove "owned by..." suffix from provider name
            owned_match = re.search(r'^(.+?)\s+owned by\s+', name_part, re.IGNORECASE)
            if owned_match:
                provider['Provider_Name'] = clean_provider_name(owned_match.group(1))
            else:
                provider['Provider_Name'] = clean_provider_name(name_part)

            # Address is between license number and Capacity
            after_license = parts[1]
            cap_match = re.search(r'\s*Capacity:', after_license)
            if cap_match:
                provider['Address'] = after_license[:cap_match.start()].strip()

    # Line 2: (continuation of owner), License Type, Ages
    line2 = lines[1] if len(lines) > 1 else ''
    provider['License_Type'] = extract_facility_type(line2)
    provider['Ages'] = extract_ages(line2)

    # Look for city/state/zip in any line (since text can get mangled)
    for line in lines:
        if not provider['City']:
            city, state, zip_code = extract_city_state_zip(line)
            if city:
                provider['City'] = city

    # Look for hours in any line
    for line in lines:
        if not provider['Hours']:
            hours = extract_hours(line)
            if hours:
                provider['Hours'] = hours
                break

    # Look for effective date and owner name
    for line in lines:
        if not provider['Effective_Date']:
            eff_date = extract_effective_date(line)
            if eff_date:
                provider['Effective_Date'] = eff_date
                # Try to extract owner name (before effective date)
                owner_match = re.match(r'^(.+?)\s+' + eff_date, line)
                if owner_match:
                    provider['Owner_Name'] = owner_match.group(1).strip()
                break

    # Look for phone in any line (typically line 4, but search all to be safe)
    for line in lines:
        if not provider['Phone']:
            phone = extract_phone(line)
            if phone:
                provider['Phone'] = phone
                break

    # Extract subsidy info from lines that contain those questions
    for line in lines:
        if 'Currently Accepts Subsidy?' in line and not provider['Currently_Accepts_Subsidy']:
            provider['Currently_Accepts_Subsidy'] = extract_yn_value(line, 'Currently Accepts Subsidy?')
        if 'Willing To Accept Subsidy?' in line and not provider['Willing_To_Accept_Subsidy']:
            provider['Willing_To_Accept_Subsidy'] = extract_yn_value(line, 'Willing To Accept Subsidy?')
        if 'Does Not Accept Subsidy?' in line and not provider['Does_Not_Accept_Subsidy']:
            provider['Does_Not_Accept_Subsidy'] = extract_yn_value(line, 'Does Not Accept Subsidy?')
        if 'Step Up To Quality:' in line and not provider['Step_Up_Quality']:
            provider['Step_Up_Quality'] = extract_step_up_quality(line)
        if 'Accredited?' in line and not provider['Accredited']:
            provider['Accredited'] = extract_accredited(line)

    return provider


def is_provider_start_line(line):
    """
    Check if a line is the start of a new provider entry.
    Provider lines contain a license number pattern.
    """
    # Must have a license number and Capacity
    has_license = bool(re.search(r'\b(FII?\d+|CCC\d+|PRE\d+|SAOC\d+)\b', line))
    has_capacity = 'Capacity:' in line
    return has_license and has_capacity


def is_zip_header(line):
    """
    Check if line is a ZIP code header like '68002 Washington'.
    """
    match = re.match(r'^(\d{5})\s+([A-Za-z]+)\s*$', line)
    return match


def extract_providers_from_pdf(pdf_path, download_date=''):
    """
    Extract all provider records from the PDF.

    Args:
        pdf_path: Path to the PDF file to parse.
        download_date: Optional date string (YYYY-MM-DD) to include in each record.

    Returns a list of dictionaries, one per provider.
    """
    providers = []
    current_zip = ''
    current_county = ''

    with pdfplumber.open(pdf_path) as pdf:
        # Skip first page (title/intro)
        for page_num, page in enumerate(pdf.pages[1:], start=2):
            text = page.extract_text()
            if not text:
                continue

            lines = [l.strip() for l in text.split('\n') if l.strip()]

            i = 0
            while i < len(lines):
                line = lines[i]

                # Skip header lines
                if any(skip in line for skip in [
                    'CHILD CARE LICENSING ROSTER',
                    'Date of Printing:',
                    'ZIP CODE',
                    'PROVIDER NAME',
                    'OWNER NAME',
                    'PHONE NUMBER',
                ]):
                    i += 1
                    continue

                # Check for ZIP code header
                zip_match = is_zip_header(line)
                if zip_match:
                    current_zip = zip_match.group(1)
                    current_county = zip_match.group(2)
                    i += 1
                    continue

                # Check for Total line
                if line.startswith('Total Number in Zip Code:'):
                    i += 1
                    continue

                # Check if this is a provider start line
                if is_provider_start_line(line):
                    # Collect lines for this provider (typically 8 lines)
                    provider_lines = [line]
                    i += 1

                    # Collect subsequent lines until we hit another provider or special line
                    lines_collected = 1
                    while i < len(lines) and lines_collected < 10:
                        next_line = lines[i]

                        # Stop if we hit a new provider, zip header, or total
                        if is_provider_start_line(next_line):
                            break
                        if is_zip_header(next_line):
                            break
                        if next_line.startswith('Total Number in Zip Code:'):
                            break
                        if any(skip in next_line for skip in [
                            'CHILD CARE LICENSING ROSTER',
                            'Date of Printing:',
                            'ZIP CODE',
                            'PROVIDER NAME',
                            'OWNER NAME',
                            'PHONE NUMBER',
                        ]):
                            break

                        provider_lines.append(next_line)
                        i += 1
                        lines_collected += 1

                    # Parse the provider block
                    provider = parse_provider_block(provider_lines, current_zip, current_county, download_date)
                    if provider['Provider_Name'] or provider['License_Number']:
                        providers.append(provider)
                else:
                    i += 1

    return providers


def write_csv(providers, output_path):
    """
    Write providers to CSV file.
    """
    fieldnames = [
        'Download_Date', 'Zip_Code', 'County', 'Provider_Name', 'License_Number',
        'License_Type', 'Owner_Name', 'Effective_Date', 'Address', 'City', 'State',
        'Phone', 'Capacity', 'Ages', 'Hours', 'Days_Open',
        'Currently_Accepts_Subsidy', 'Willing_To_Accept_Subsidy',
        'Does_Not_Accept_Subsidy', 'Step_Up_Quality', 'Accredited'
    ]

    with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(providers)

    print(f"Wrote {len(providers)} providers to {output_path}")


def main():
    # Default paths
    script_dir = Path(__file__).parent
    default_input = script_dir / "ChildCareRoster.pdf"
    default_output = script_dir / "child_care_providers.csv"

    # Parse command line arguments
    if len(sys.argv) >= 2:
        input_pdf = Path(sys.argv[1])
    else:
        input_pdf = default_input

    if len(sys.argv) >= 3:
        output_csv = Path(sys.argv[2])
    else:
        output_csv = default_output

    # Validate input file exists
    if not input_pdf.exists():
        print(f"Error: Input file not found: {input_pdf}")
        sys.exit(1)

    print(f"Parsing: {input_pdf}")

    # Extract providers
    providers = extract_providers_from_pdf(input_pdf)

    # Write to CSV
    write_csv(providers, output_csv)

    print(f"Successfully extracted {len(providers)} providers")


if __name__ == "__main__":
    main()
