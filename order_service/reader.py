import csv
from typing import Dict, Iterator


def read_csv_rows(path: str) -> Iterator[Dict[str, str]]:
    """Stream CSV rows one at a time"""
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            yield row
