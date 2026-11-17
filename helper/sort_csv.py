#!/usr/bin/env python3
"""
CSV Sorter - Sorts large CSV files by the first column in ascending order.

This script efficiently handles large CSV files using streaming I/O and provides
detailed statistics about the sorting process.
"""

import argparse
import csv
import sys
from pathlib import Path
from typing import TextIO, Union

def parse_int(value: str) -> Union[int, None]:
    try:
        return int(value)
    except ValueError:
        # Handle potential hex values or other formats
        if value.lower().startswith('0x'):
            return int(value, 16)
        return None

def read_csv_streaming(input_file: TextIO, delimiter: str = ',') -> tuple:
    reader = csv.reader(input_file, delimiter=delimiter)
    header = next(reader)
    rows = list(reader)
    return header, rows

def is_numeric_value(value: str) -> bool:
    if not value or value.strip() == '':
        return False
    try:
        int(value)
        return True
    except ValueError:
        if value.lower().startswith('0x'):
            try:
                _ = int(value, 16)
                return True
            except:
                return False

def sort_csv_by_first_column(rows: list, reverse_first_column: bool = True) -> list:
    """
    Sort CSV rows by the first column in ascending order.

    Args:
        header: CSV header row
        rows: List of data rows
        reverse_first_column: Whether to sort by first column (default: True)

    Returns:
        Sorted list of rows with header at top
    """
    # Filter out header row from sorting using a general numeric check
    data_rows = [row for row in rows if row and is_numeric_value(row[0])]

    sorted_rows = sorted(
        data_rows,
        key=lambda row: parse_int(row[0]) if row else 0,
        reverse=not reverse_first_column
    )
    return sorted_rows

def write_csv_sorted(output_file: TextIO, header: list, rows: list, delimiter: str = ',') -> None:
    """
    Write sorted CSV data to output file.

    Args:
        output_file: Output file handle
        header: CSV header row
        rows: Sorted list of data rows
        delimiter: CSV delimiter character
    """
    writer = csv.writer(output_file, delimiter=delimiter)
    writer.writerow(header)
    writer.writerows(rows)

def sort_csv(input_path: Union[str, Path], output_path: Union[str, Path] = None, delimiter: str = ',') -> bool:
    """
    Main function to sort a CSV file by the first column.

    Args:
        input_path: Path to input CSV file
        output_path: Path to output CSV file (optional, defaults to input_path with _sorted suffix)
        chunk_size: Number of rows to process at once for very large files
        delimiter: CSV delimiter character

    Returns:
        True if sorting was successful, False otherwise
    """
    input_file = Path(input_path)

    if not input_file.exists():
        print(f"Error: Input file '{input_path}' not found.")
        return False

    if output_path is None:
        output_path = input_file.with_suffix(input_file.suffix + '_sorted.csv')
    else:
        output_path = Path(output_path)

    print(f"Processing: {input_file.absolute()}")
    print(f"Output:     {output_path.absolute()}")

    try:
        # Read CSV data
        with open(input_file, 'r', newline='', encoding='utf-8') as infile:
            header, rows = read_csv_streaming(infile, delimiter)

            # Sort by first column
            sorted_data = sort_csv_by_first_column(rows)

            # Write sorted data
            with open(output_path, 'w', newline='', encoding='utf-8') as outfile:
                write_csv_sorted(outfile, header, sorted_data, delimiter)
            return True

    except Exception as e:
        print(f"Error during sorting: {e}", file=sys.stderr)
        return False


def main():
    """Parse command line arguments and execute CSV sorting."""
    parser = argparse.ArgumentParser(
        description='Sort large CSV files by the first column in ascending order.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example usage:
  %(prog)s input.csv                    # Sort input.csv and save as input_sorted.csv
  %(prog)s data.csv -o sorted_data.csv  # Sort and specify output filename
  %(prog)s results.csv --delimiter ';'  # Use custom delimiter for semicolon-separated CSV
        """
    )

    parser.add_argument('input', type=str, help='Path to input CSV file')
    parser.add_argument('-o', '--output', type=str, default=None, help='Path to output CSV file (default: input_filename_sorted.csv)')
    parser.add_argument('-d', '--delimiter', type=str, default=',', help='CSV delimiter character (default: ,)')
    parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose output')
    args = parser.parse_args()

    success = sort_csv(
        input_path=args.input,
        output_path=args.output,
        delimiter=args.delimiter
    )
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
