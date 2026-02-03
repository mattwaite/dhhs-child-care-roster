#!/usr/bin/env python3
"""
Consistency tests for Nebraska DHHS Child Care Roster parsing.

These tests validate that:
1. Parsing the same PDF twice produces identical results
2. Extracted data matches expected patterns and formats
3. Provider counts are reasonable
4. Required fields are populated
"""

import re
from collections import Counter


# Expected patterns for validation
LICENSE_PATTERN = re.compile(r'^(FII?\d+|CCC\d+|PRE\d+|SAOC\d+)$')
PHONE_PATTERN = re.compile(r'^\(\d{3}\) \d{3}-\d{4}$')
DATE_PATTERN = re.compile(r'^\d{2}/\d{2}/\d{4}$')
ZIP_PATTERN = re.compile(r'^\d{5}$')
HOURS_PATTERN = re.compile(r'^\d{4} To \d{4}$')
DAYS_PATTERN = re.compile(r'^[MTWTHFS]+$')

# Valid license types
VALID_LICENSE_TYPES = {
    'Family Child Care Home I',
    'Family Child Care Home II',
    'Child Care Center',
    'School-Age-Only Child Care Center',
    'Preschool',
}

# Minimum expected providers (safeguard against empty/broken parsing)
MIN_EXPECTED_PROVIDERS = 100


class ConsistencyTestResult:
    """Result of a consistency test run."""

    def __init__(self):
        self.passed = True
        self.errors = []
        self.warnings = []
        self.stats = {}

    def add_error(self, message):
        self.passed = False
        self.errors.append(message)

    def add_warning(self, message):
        self.warnings.append(message)

    def __str__(self):
        lines = []
        if self.passed:
            lines.append("✓ All consistency tests passed")
        else:
            lines.append("✗ Consistency tests FAILED")

        if self.errors:
            lines.append("\nErrors:")
            for err in self.errors:
                lines.append(f"  - {err}")

        if self.warnings:
            lines.append("\nWarnings:")
            for warn in self.warnings:
                lines.append(f"  - {warn}")

        if self.stats:
            lines.append("\nStats:")
            for key, val in self.stats.items():
                lines.append(f"  {key}: {val}")

        return '\n'.join(lines)


def test_parsing_determinism(pdf_path, parse_func, download_date=''):
    """
    Test that parsing the same PDF twice produces identical results.

    Args:
        pdf_path: Path to PDF file
        parse_func: Function to parse PDF (extract_providers_from_pdf)
        download_date: Date string to pass to parser

    Returns:
        ConsistencyTestResult
    """
    result = ConsistencyTestResult()

    # Parse twice
    providers1 = parse_func(pdf_path, download_date=download_date)
    providers2 = parse_func(pdf_path, download_date=download_date)

    # Check count matches
    if len(providers1) != len(providers2):
        result.add_error(
            f"Provider count differs between runs: {len(providers1)} vs {len(providers2)}"
        )
        return result

    result.stats['provider_count'] = len(providers1)

    # Check each provider matches
    mismatches = 0
    for i, (p1, p2) in enumerate(zip(providers1, providers2)):
        if p1 != p2:
            mismatches += 1
            if mismatches <= 3:  # Only report first few
                result.add_error(f"Provider {i} differs between runs")

    if mismatches > 3:
        result.add_error(f"... and {mismatches - 3} more mismatches")

    return result


def test_data_quality(providers):
    """
    Test that extracted data meets quality standards.

    Args:
        providers: List of provider dictionaries

    Returns:
        ConsistencyTestResult
    """
    result = ConsistencyTestResult()

    if len(providers) < MIN_EXPECTED_PROVIDERS:
        result.add_error(
            f"Too few providers extracted: {len(providers)} (minimum: {MIN_EXPECTED_PROVIDERS})"
        )

    result.stats['total_providers'] = len(providers)

    # Track field statistics
    license_types = Counter()
    invalid_licenses = []
    invalid_phones = []
    invalid_dates = []
    invalid_zips = []
    missing_names = 0
    missing_license_numbers = 0

    for i, p in enumerate(providers):
        # Check required fields
        if not p.get('Provider_Name'):
            missing_names += 1

        if not p.get('License_Number'):
            missing_license_numbers += 1
        elif not LICENSE_PATTERN.match(p['License_Number']):
            invalid_licenses.append((i, p['License_Number']))

        # Track license types
        if p.get('License_Type'):
            license_types[p['License_Type']] += 1
            if p['License_Type'] not in VALID_LICENSE_TYPES:
                result.add_warning(f"Unknown license type: {p['License_Type']}")

        # Validate phone format (if present)
        if p.get('Phone') and not PHONE_PATTERN.match(p['Phone']):
            invalid_phones.append((i, p['Phone']))

        # Validate date format (if present)
        if p.get('Effective_Date') and not DATE_PATTERN.match(p['Effective_Date']):
            invalid_dates.append((i, p['Effective_Date']))

        # Validate ZIP format (if present)
        if p.get('Zip_Code') and not ZIP_PATTERN.match(p['Zip_Code']):
            invalid_zips.append((i, p['Zip_Code']))

    # Report issues
    if missing_names > 0:
        pct = (missing_names / len(providers)) * 100
        if pct > 5:
            result.add_error(f"{missing_names} providers ({pct:.1f}%) missing Provider_Name")
        else:
            result.add_warning(f"{missing_names} providers ({pct:.1f}%) missing Provider_Name")

    if missing_license_numbers > 0:
        pct = (missing_license_numbers / len(providers)) * 100
        if pct > 5:
            result.add_error(f"{missing_license_numbers} providers ({pct:.1f}%) missing License_Number")
        else:
            result.add_warning(f"{missing_license_numbers} providers ({pct:.1f}%) missing License_Number")

    if invalid_licenses:
        result.add_error(f"{len(invalid_licenses)} invalid license numbers (e.g., {invalid_licenses[0][1]})")

    if invalid_phones:
        pct = (len(invalid_phones) / len(providers)) * 100
        if pct > 10:
            result.add_error(f"{len(invalid_phones)} invalid phone formats ({pct:.1f}%)")
        elif invalid_phones:
            result.add_warning(f"{len(invalid_phones)} invalid phone formats")

    if invalid_dates:
        result.add_error(f"{len(invalid_dates)} invalid date formats")

    if invalid_zips:
        result.add_error(f"{len(invalid_zips)} invalid ZIP codes")

    # Add stats
    result.stats['license_type_distribution'] = dict(license_types)
    result.stats['providers_with_phone'] = sum(1 for p in providers if p.get('Phone'))
    result.stats['providers_with_address'] = sum(1 for p in providers if p.get('Address'))

    return result


def test_field_completeness(providers, required_rate=0.90):
    """
    Test that key fields are populated at expected rates.

    Args:
        providers: List of provider dictionaries
        required_rate: Minimum proportion that must have the field (0.0-1.0)

    Returns:
        ConsistencyTestResult
    """
    result = ConsistencyTestResult()

    # Fields that should be present in most records
    key_fields = [
        'License_Number',
        'Provider_Name',
        'Zip_Code',
        'County',
        'License_Type',
        'Capacity',
    ]

    for field in key_fields:
        populated = sum(1 for p in providers if p.get(field))
        rate = populated / len(providers) if providers else 0
        result.stats[f'{field}_rate'] = f"{rate:.1%}"

        if rate < required_rate:
            result.add_error(
                f"Field '{field}' only populated in {rate:.1%} of records "
                f"(required: {required_rate:.0%})"
            )

    return result


def run_all_tests(pdf_path, providers, parse_func=None, download_date=''):
    """
    Run all consistency tests.

    Args:
        pdf_path: Path to the PDF file
        providers: Already-parsed list of providers
        parse_func: Parse function for determinism test (optional)
        download_date: Date string for parsing

    Returns:
        tuple: (overall_passed: bool, combined_result: ConsistencyTestResult)
    """
    combined = ConsistencyTestResult()

    print("Running consistency tests...")

    # Test 1: Data quality
    print("  - Testing data quality...")
    quality_result = test_data_quality(providers)
    combined.errors.extend(quality_result.errors)
    combined.warnings.extend(quality_result.warnings)
    combined.stats.update(quality_result.stats)

    # Test 2: Field completeness
    print("  - Testing field completeness...")
    completeness_result = test_field_completeness(providers)
    combined.errors.extend(completeness_result.errors)
    combined.warnings.extend(completeness_result.warnings)
    combined.stats.update(completeness_result.stats)

    # Test 3: Parsing determinism (if parse function provided)
    if parse_func:
        print("  - Testing parsing determinism...")
        determinism_result = test_parsing_determinism(pdf_path, parse_func, download_date)
        combined.errors.extend(determinism_result.errors)
        combined.warnings.extend(determinism_result.warnings)
        # Don't duplicate provider_count if already present
        for k, v in determinism_result.stats.items():
            if k not in combined.stats:
                combined.stats[k] = v

    combined.passed = len(combined.errors) == 0

    return combined.passed, combined


if __name__ == "__main__":
    # Standalone test runner
    import sys
    from pathlib import Path
    from parse_childcare_roster import extract_providers_from_pdf

    if len(sys.argv) < 2:
        print("Usage: python test_parse_consistency.py <pdf_path>")
        sys.exit(1)

    pdf_path = Path(sys.argv[1])
    if not pdf_path.exists():
        print(f"Error: PDF not found: {pdf_path}")
        sys.exit(1)

    print(f"Testing: {pdf_path}")
    providers = extract_providers_from_pdf(pdf_path)

    passed, result = run_all_tests(
        pdf_path,
        providers,
        parse_func=extract_providers_from_pdf
    )

    print()
    print(result)

    sys.exit(0 if passed else 1)
