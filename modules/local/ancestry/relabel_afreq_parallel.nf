process RELABEL_AFREQ_PARALLEL {
    label 'process_high'
    label 'process_high_memory'
    label 'pgscatalog_utils'

    tag "$meta.id $meta.effect_type afreq chromosome-parallel"

    storeDir ((params.genotypes_cache ? file(params.genotypes_cache) : workDir) / "ancestry" / "relabel" / "afreq_parallel")

    conda "${task.ext.conda}"

    container "${ workflow.containerEngine == 'singularity' &&
        !task.ext.singularity_pull_docker_container ?
        "${task.ext.singularity}${task.ext.singularity_version}" :
        "${task.ext.docker}${task.ext.docker_version}" }"

    input:
    tuple val(meta), path(target), path(matched)

    output:
    tuple val(relabel_meta), path("${output}"), emit: relabelled
    path "parallel_relabel_timings.tsv", emit: timings
    path "versions.yml", emit: versions

    script:
    relabel_meta = meta.plus(['target_format': 'afreq'])
    output = "${meta.id}.afreq_ALL_relabelled.gz"
    def map_args = matched.collect { "'${it}'" }.join(' ')
    """
    split_start=\$(date +%s%N)
    split_afreq_by_chrom.py $target split
    split_end=\$(date +%s%N)

    mkdir -p relabel
    export dataset='${meta.id}.afreq'
    export relabel_cpus=$task.cpus
    printf '%s\n' $map_args | xargs -P "\$relabel_cpus" -n 1 bash -c '
        set -euo pipefail
        map="\$1"
        chrom=\$(basename "\$map" | sed -E "s/.*_([0-9]+)_matched\\.txt\\.gz/\\1/")
        mkdir -p "relabel/\$chrom"
        pgscatalog-relabel \\
            --maps "\$map" \\
            --col_from ID_REF \\
            --col_to ID_TARGET \\
            --target_file "split/reference_\$chrom.afreq.gz" \\
            --target_col ID \\
            --dataset "\$dataset" \\
            --combined \\
            --outdir "relabel/\$chrom"
    ' _
    relabel_end=\$(date +%s%N)

    combine_relabelled_afreq.py $output \\
        \$(for chrom in \$(seq 1 22); do printf 'relabel/%s/%s ' "\$chrom" "$output"; done)
    combine_end=\$(date +%s%N)

    python -c '
import sys
a, b, c, d = map(int, sys.argv[1:])
print("phase\\tseconds")
print(f"split\\t{(b - a) / 1e9:.3f}")
print(f"parallel_relabel\\t{(c - b) / 1e9:.3f}")
print(f"combine\\t{(d - c) / 1e9:.3f}")
print(f"total\\t{(d - a) / 1e9:.3f}")
' "\$split_start" "\$split_end" "\$relabel_end" "\$combine_end" > parallel_relabel_timings.tsv

    cat <<-END_VERSIONS > versions.yml
    ${task.process.tokenize(':').last()}:
        pgscatalog.core: \$(echo \$(python -c 'import pgscatalog.core; print(pgscatalog.core.__version__)'))
    END_VERSIONS
    """
}
