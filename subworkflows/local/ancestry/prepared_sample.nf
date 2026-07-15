// Load score-independent sample artifacts produced by a previous pgsc_calc
// compatibility and ancestry projection run.

include { EXTRACT_DATABASE } from '../../../modules/local/ancestry/extract_database'

workflow PREPARED_SAMPLE {
    take:
    input_vcf
    reference
    target_build

    main:
    ch_versions = Channel.empty()

    if (!params.prepared_sample_id) {
        error "--prepared_sample_id is required with --prepared_sample_dir"
    }

    // Reuse samplesheet metadata so partial chromosome inputs and dosage
    // provenance remain identical to the cold path. The BCF paths themselves
    // are never staged into a process in prepared mode.
    input_vcf
        .map { tuple(it.first().chrom.toString(), it.first()) }
        .set { ch_target_meta }

    Channel.fromPath("${params.prepared_sample_dir}/genomes/*/*.pgen", checkIfExists: true)
        .map { tuple(preparedChromosome(it), it) }
        .join(ch_target_meta, failOnMismatch: true)
        .map { chrom, path, meta -> tuple(preparedMeta(meta), path) }
        .set { target_geno }

    Channel.fromPath("${params.prepared_sample_dir}/genomes/*/*.psam", checkIfExists: true)
        .map { tuple(preparedChromosome(it), it) }
        .join(ch_target_meta, failOnMismatch: true)
        .map { chrom, path, meta -> tuple(preparedMeta(meta), path) }
        .set { target_pheno }

    Channel.fromPath("${params.prepared_sample_dir}/genomes/*/*.pvar.zst", checkIfExists: true)
        .map { tuple(preparedChromosome(it), it) }
        .join(ch_target_meta, failOnMismatch: true)
        .map { chrom, path, meta -> tuple(preparedMeta(meta), path) }
        .set { target_variants }

    Channel.fromPath(
        "${params.prepared_sample_dir}/intersections/${params.prepared_sample_id}_*_matched.txt.gz",
        checkIfExists: true
    )
        .map { tuple(preparedChromosome(it), it) }
        .join(ch_target_meta, failOnMismatch: true)
        .map { chrom, path, meta -> tuple(preparedMeta(meta).subMap('id', 'build', 'n_chrom', 'chrom'), path) }
        .set { intersection }

    Channel.fromPath(
        "${params.prepared_sample_dir}/${params.prepared_sample_id}.afreq_ALL_relabelled.gz",
        checkIfExists: true
    )
        .map { tuple([:], it) }
        .set { ref_afreq }

    Channel.fromPath(
        "${params.prepared_sample_dir}/intersections/intersect_counts_*.txt",
        checkIfExists: true
    )
        .collect()
        .set { intersect_count }

    // The full reference genotype remains global. Extracting it here costs
    // roughly one minute and avoids storing a multi-gigabyte duplicate in every
    // prepared sample artifact.
    EXTRACT_DATABASE(reference)
    ch_versions = ch_versions.mix(EXTRACT_DATABASE.out.versions.first())

    EXTRACT_DATABASE.out.grch38
        .concat(EXTRACT_DATABASE.out.grch37)
        .filter { it.first().build == target_build }
        .map {
            def meta = [:].plus(it.first())
            meta.is_pfile = true
            meta.id = 'reference'
            meta.chrom = 'ALL'
            tuple(meta, it.tail())
        }
        .transpose()
        .branch {
            geno: it.last().getExtension() == 'pgen'
            pheno: it.last().getExtension() == 'psam'
            variants: it.last().getExtension() == 'zst'
        }
        .set { ch_ref }

    Channel.fromPath(
        "${params.prepared_sample_dir}/GRCh38_*.king.cutoff.out.id",
        checkIfExists: true
    )
        .set { relatedness }

    // REPORT expects [meta, [target pcs], [reference pcs]]. Preserve that
    // shape so ANCESTRY_ANALYSIS and SCORE_REPORT remain unchanged.
    Channel.of(['target_id': params.prepared_sample_id])
        .concat(Channel.fromPath("${params.prepared_sample_dir}/target_pcs/*.pcs", checkIfExists: true).collect())
        .concat(Channel.fromPath("${params.prepared_sample_dir}/reference_pcs/*.pcs", checkIfExists: true).collect())
        .buffer(size: 3)
        .set { projections }

    emit:
    geno = target_geno
    pheno = target_pheno
    variants = target_variants
    intersection = intersection
    intersect_count = intersect_count
    projections = projections
    ref_geno = ch_ref.geno
    ref_pheno = ch_ref.pheno
    ref_var = ch_ref.variants
    relatedness = relatedness
    ref_afreq = ref_afreq
    versions = ch_versions
}

def preparedMeta(meta) {
    def prepared = [:].plus(meta)
    prepared.is_pfile = true
    prepared.id = params.prepared_sample_id.toString()
    prepared
}

def preparedChromosome(path) {
    def matcher = path.getName() =~ /_([0-9]+)(?:_matched\.txt\.gz|\.pgen|\.psam|\.pvar\.zst)$/
    if (!matcher.find()) {
        error "Can't determine chromosome from prepared sample artifact: ${path.getName()}"
    }
    matcher.group(1)
}
