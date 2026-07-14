#!/usr/bin/env python3
"""Combine chromosome AFREQ outputs, retaining one header and original row bytes."""

import argparse
import gzip
import shutil
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    parser.add_argument("inputs", nargs="+", type=Path)
    args = parser.parse_args()

    with gzip.open(args.output, "wb", compresslevel=1) as destination:
        for index, path in enumerate(args.inputs):
            with gzip.open(path, "rb") as source:
                if index:
                    next(source)
                shutil.copyfileobj(source, destination, length=1024 * 1024)


if __name__ == "__main__":
    main()
