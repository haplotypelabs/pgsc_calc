#!/usr/bin/env python3
"""Split a scorefile by chromosome while retaining its original row order."""

import argparse
import contextlib
import csv
import gzip
from pathlib import Path
from typing import TextIO

INDEX_COLUMN = "__PGSC_ROW_INDEX"


def open_text(path: Path, mode: str) -> TextIO:
    if path.suffix == ".gz":
        return gzip.open(path, mode, newline="")
    return path.open(mode, newline="")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("outdir", type=Path)
    args = parser.parse_args()
    args.outdir.mkdir(parents=True, exist_ok=True)

    outputs: dict[str, tuple[TextIO, csv.DictWriter]] = {}
    row_counts: dict[str, int] = {}
    chrom_order: list[str] = []

    with contextlib.ExitStack() as stack, open_text(args.source, "rt") as source:
        for line in source:
            if line.startswith("##"):
                continue
            header = next(csv.reader([line], delimiter="\t"))
            break
        else:
            raise ValueError(f"No header found in {args.source}")

        if "ID" not in header:
            raise ValueError(f"No ID column found in {args.source}")
        if INDEX_COLUMN in header:
            raise ValueError(f"Reserved column {INDEX_COLUMN} already exists")

        reader = csv.DictReader(source, delimiter="\t", fieldnames=header)
        output_header = [*header, INDEX_COLUMN]
        for row_index, row in enumerate(reader):
            chrom = row["ID"].split(":", 1)[0]
            if not chrom or chrom in {".", ".."} or "/" in chrom:
                raise ValueError(f"Invalid chromosome in variant ID: {row['ID']}")

            if chrom not in outputs:
                destination = stack.enter_context(
                    gzip.open(
                        args.outdir / f"reference_{chrom}.scorefile.gz",
                        "wt",
                        compresslevel=1,
                        newline="",
                    )
                )
                writer = csv.DictWriter(
                    destination, delimiter="\t", fieldnames=output_header
                )
                writer.writeheader()
                outputs[chrom] = (destination, writer)
                row_counts[chrom] = 0
                chrom_order.append(chrom)

            row[INDEX_COLUMN] = str(row_index)
            outputs[chrom][1].writerow(row)
            row_counts[chrom] += 1

    if not chrom_order:
        raise ValueError(f"No score rows found in {args.source}")

    with (args.outdir / "manifest.tsv").open("w", newline="") as manifest:
        writer = csv.DictWriter(manifest, delimiter="\t", fieldnames=["chrom", "rows"])
        writer.writeheader()
        for chrom in chrom_order:
            writer.writerow({"chrom": chrom, "rows": row_counts[chrom]})


if __name__ == "__main__":
    main()
