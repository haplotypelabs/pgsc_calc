#!/usr/bin/env python3
"""Combine chromosome-relabeled scorefiles in their original row order."""

import argparse
import csv
import gzip
from pathlib import Path

INDEX_COLUMN = "__PGSC_ROW_INDEX"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("relabel_dir", type=Path)
    args = parser.parse_args()

    with args.manifest.open(newline="") as manifest_file:
        manifest = list(csv.DictReader(manifest_file, delimiter="\t"))

    rows: list[tuple[int, dict[str, str]]] = []
    output_header: list[str] | None = None
    expected_rows = 0

    for entry in manifest:
        chrom = entry["chrom"]
        expected_rows += int(entry["rows"])
        source_path = args.relabel_dir / chrom / "reference_ALL_relabelled.gz"
        with gzip.open(source_path, "rt", newline="") as source:
            reader = csv.DictReader(source, delimiter="\t")
            if reader.fieldnames is None or INDEX_COLUMN not in reader.fieldnames:
                raise ValueError(f"Missing {INDEX_COLUMN} in {source_path}")
            header = [column for column in reader.fieldnames if column != INDEX_COLUMN]
            if output_header is None:
                output_header = header
            elif output_header != header:
                raise ValueError(f"Inconsistent columns in {source_path}")

            for row in reader:
                row_index = int(row.pop(INDEX_COLUMN))
                rows.append((row_index, row))

    rows.sort(key=lambda item: item[0])
    if len(rows) != expected_rows:
        raise ValueError(f"Expected {expected_rows} rows, found {len(rows)}")
    if [index for index, _ in rows] != list(range(expected_rows)):
        raise ValueError("Relabeled scorefile row indexes are incomplete or duplicated")
    if output_header is None:
        raise ValueError("No relabeled scorefiles found")

    with gzip.open(args.output, "wt", compresslevel=1, newline="") as destination:
        writer = csv.DictWriter(destination, delimiter="\t", fieldnames=output_header)
        writer.writeheader()
        writer.writerows(row for _, row in rows)


if __name__ == "__main__":
    main()
