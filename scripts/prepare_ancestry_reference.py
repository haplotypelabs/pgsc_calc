#!/usr/bin/env python3
"""Create immutable chromosome-split PVAR files from an ancestry reference PVAR."""

import argparse
import hashlib
import json
from pathlib import Path

from xopen import xopen


def digest(path: Path) -> str:
    sha256 = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def normalise_chrom(raw: bytes) -> str:
    chrom = raw.decode()
    if chrom.lower().startswith("chr"):
        chrom = chrom[3:]
    return chrom


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", help="Whole-genome .pvar.zst reference file")
    parser.add_argument("outdir", type=Path)
    parser.add_argument("--build", default="GRCh38")
    parser.add_argument("--reference-id", default="HGDP+1kGP")
    parser.add_argument("--source-uri")
    args = parser.parse_args()
    args.outdir.mkdir(parents=True, exist_ok=True)

    metadata = []
    seen = set()
    expected = {str(chrom) for chrom in range(1, 23)}
    current_chrom = None
    output = None
    output_path = None
    artifacts = []

    try:
        with xopen(args.source, "rb") as source:
            for line in source:
                if line.startswith(b"##"):
                    metadata.append(line)
                    continue
                header = line
                break
            else:
                raise ValueError(f"No #CHROM header found in {args.source}")

            columns = header.rstrip(b"\r\n").split(b"\t")
            chrom_index = columns.index(b"#CHROM")

            for line in source:
                fields = line.rstrip(b"\r\n").split(b"\t", chrom_index + 1)
                chrom = normalise_chrom(fields[chrom_index])
                if chrom not in expected:
                    continue
                if chrom != current_chrom:
                    if chrom in seen:
                        raise ValueError(f"Input is not grouped by chromosome: {chrom} repeats")
                    if output is not None:
                        output.close()
                        artifacts.append(output_path)
                    seen.add(chrom)
                    current_chrom = chrom
                    output_path = (
                        args.outdir
                        / f"{args.build}_{args.reference_id}_{chrom}.pvar.zst"
                    )
                    output = xopen(output_path, "wb", compresslevel=3, threads=1)
                    output.writelines(metadata)
                    output.write(header)
                output.write(line)
    finally:
        if output is not None:
            output.close()
            artifacts.append(output_path)

    missing = sorted(expected - seen, key=int)
    if missing:
        raise ValueError(f"Missing autosomes: {', '.join(missing)}")

    manifest = {
        "schema_version": 1,
        "build": args.build,
        "reference_id": args.reference_id,
        "source_uri": args.source_uri,
        "source_file": Path(args.source).name,
        "source_size": Path(args.source).stat().st_size,
        "source_sha256": digest(Path(args.source)),
        "artifacts": [
            {
                "chrom": path.name.removesuffix(".pvar.zst").rsplit("_", 1)[-1],
                "name": path.name,
                "size": path.stat().st_size,
                "sha256": digest(path),
            }
            for path in artifacts
        ],
    }
    with (args.outdir / "manifest.json").open("w") as destination:
        json.dump(manifest, destination, indent=2)
        destination.write("\n")


if __name__ == "__main__":
    main()
