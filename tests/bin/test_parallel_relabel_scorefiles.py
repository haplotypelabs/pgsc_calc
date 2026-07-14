import csv
import gzip
import subprocess
from pathlib import Path


def test_split_and_combine_preserve_original_order(tmp_path: Path) -> None:
    source = tmp_path / "sample_ALL_additive_0.scorefile.gz"
    split_dir = tmp_path / "split"
    relabel_dir = tmp_path / "relabel"
    output = tmp_path / "reference_ALL_additive_0.scorefile.gz"
    rows = [
        ["2:20:A:G", "A", "0.2"],
        ["1:10:C:T", "T", "0.1"],
        ["2:30:G:C", "C", "0.3"],
    ]

    with gzip.open(source, "wt", newline="") as destination:
        writer = csv.writer(destination, delimiter="\t")
        writer.writerow(["ID", "effect_allele", "PGS_TEST"])
        writer.writerows(rows)

    subprocess.run(["bin/split_scorefile_by_chrom.py", source, split_dir], check=True)

    replacements = {
        "1": {"1:10:C:T": "1:10:T:C"},
        "2": {"2:20:A:G": "2:20:G:A", "2:30:G:C": "2:30:C:G"},
    }
    for chrom, mapping in replacements.items():
        destination_dir = relabel_dir / chrom
        destination_dir.mkdir(parents=True)
        with gzip.open(
            split_dir / f"reference_{chrom}.scorefile.gz", "rt", newline=""
        ) as split_source:
            reader = csv.DictReader(split_source, delimiter="\t")
            split_rows = list(reader)
            fieldnames = reader.fieldnames
        assert fieldnames is not None
        for row in split_rows:
            row["ID"] = mapping[row["ID"]]
        with gzip.open(
            destination_dir / "reference_ALL_relabelled.gz", "wt", newline=""
        ) as destination:
            writer = csv.DictWriter(destination, delimiter="\t", fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(split_rows)

    subprocess.run(
        [
            "bin/combine_relabelled_scorefiles.py",
            output,
            split_dir / "manifest.tsv",
            relabel_dir,
        ],
        check=True,
    )

    with gzip.open(output, "rt", newline="") as combined:
        reader = csv.DictReader(combined, delimiter="\t")
        assert reader.fieldnames == ["ID", "effect_allele", "PGS_TEST"]
        assert list(reader) == [
            {"ID": "2:20:G:A", "effect_allele": "A", "PGS_TEST": "0.2"},
            {"ID": "1:10:T:C", "effect_allele": "T", "PGS_TEST": "0.1"},
            {"ID": "2:30:C:G", "effect_allele": "C", "PGS_TEST": "0.3"},
        ]
