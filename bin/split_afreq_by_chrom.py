#!/usr/bin/env python3
"""Split a PLINK2 AFREQ stream by chromosome without changing row bytes."""

import argparse
import contextlib
import gzip
from pathlib import Path

from xopen import xopen


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source")
    parser.add_argument("outdir", type=Path)
    args = parser.parse_args()
    args.outdir.mkdir(parents=True, exist_ok=True)

    outputs = {}
    with contextlib.ExitStack() as stack, xopen(args.source, "rb") as source:
        metadata = []
        for line in source:
            if line.startswith(b"##"):
                metadata.append(line)
                continue
            header = line
            break
        else:
            raise ValueError(f"No header found in {args.source}")

        columns = header.rstrip(b"\r\n").split(b"\t")
        chrom_index = columns.index(b"#CHROM") if b"#CHROM" in columns else None
        id_index = columns.index(b"ID")

        for line in source:
            fields = line.rstrip(b"\r\n").split(b"\t")
            chrom = (
                fields[chrom_index]
                if chrom_index is not None
                else fields[id_index].split(b":", 1)[0]
            ).decode()
            output = outputs.get(chrom)
            if output is None:
                output = stack.enter_context(
                    gzip.open(
                        args.outdir / f"reference_{chrom}.afreq.gz",
                        "wb",
                        compresslevel=1,
                    )
                )
                output.writelines(metadata)
                output.write(header)
                outputs[chrom] = output
            output.write(line)


if __name__ == "__main__":
    main()
