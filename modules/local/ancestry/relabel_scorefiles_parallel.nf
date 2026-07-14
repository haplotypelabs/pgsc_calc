process RELABEL_SCOREFILES_PARALLEL {
    label 'process_high'
    label 'process_high_memory'
    label 'pgscatalog_utils'

    tag "reference $meta.effect_type scorefile chromosome-parallel"

    conda "${task.ext.conda}"

    container "${ workflow.containerEngine == 'singularity' &&
        !task.ext.singularity_pull_docker_container ?
        "${task.ext.singularity}${task.ext.singularity_version}" :
        "${task.ext.docker}${task.ext.docker_version}" }"

    input:
    tuple val(meta), path(target), path(matched)

    output:
    tuple val(relabel_meta), path("${output}"), emit: relabelled
    path "parallel_scorefile_relabel_timings.tsv", emit: timings
    path "versions.yml", emit: versions

    script:
    target_format = target.getName().tokenize('.')[1]
    relabel_meta = meta.plus(['target_format': target_format])
    output = target.getName().replaceFirst('^[^_]*_', 'reference_')
    def map_args = matched.collect { "'${it}'" }.join(' ')
    """
    split_start=\$(date +%s%N)
    split_scorefile_by_chrom.py $target split
    split_end=\$(date +%s%N)

    mkdir -p relabel
    : > relabel_jobs.tsv
    for map in $map_args; do
        chrom=\$(basename "\$map" | sed -E 's/.*_([0-9]+)_matched\\.txt\\.gz/\\1/')
        split_target="split/reference_\${chrom}.scorefile.gz"
        if [ -f "\$split_target" ]; then
            printf '%s\t%s\t%s\n' "\$chrom" "\$map" "\$split_target" >> relabel_jobs.tsv
        fi
    done

    expected_jobs=\$(awk 'END { print NR - 1 }' split/manifest.tsv)
    actual_jobs=\$(wc -l < relabel_jobs.tsv)
    if [ "\$actual_jobs" -ne "\$expected_jobs" ]; then
        echo "Expected \$expected_jobs chromosome relabel jobs, found \$actual_jobs" >&2
        exit 1
    fi

    export relabel_cpus=$task.cpus
    cat relabel_jobs.tsv | xargs -P "\$relabel_cpus" -n 3 bash -c '
        set -euo pipefail
        chrom="\$1"
        map="\$2"
        split_target="\$3"
        mkdir -p "relabel/\$chrom"
        pgscatalog-relabel \\
            --maps "\$map" \\
            --col_from ID_TARGET \\
            --col_to ID_REF \\
            --target_file "\$split_target" \\
            --target_col ID \\
            --dataset reference \\
            --combined \\
            --outdir "relabel/\$chrom"
    ' _
    relabel_end=\$(date +%s%N)

    combine_relabelled_scorefiles.py $output split/manifest.tsv relabel
    combine_end=\$(date +%s%N)

    python -c '
import sys
a, b, c, d = map(int, sys.argv[1:])
print("phase\\tseconds")
print(f"split\\t{(b - a) / 1e9:.3f}")
print(f"parallel_relabel\\t{(c - b) / 1e9:.3f}")
print(f"combine\\t{(d - c) / 1e9:.3f}")
print(f"total\\t{(d - a) / 1e9:.3f}")
' "\$split_start" "\$split_end" "\$relabel_end" "\$combine_end" > parallel_scorefile_relabel_timings.tsv

    cat <<-END_VERSIONS > versions.yml
    ${task.process.tokenize(':').last()}:
        pgscatalog.core: \$(echo \$(python -c 'import pgscatalog.core; print(pgscatalog.core.__version__)'))
    END_VERSIONS
    """
}
