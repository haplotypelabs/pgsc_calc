.. _ancestry:

How do I normalise calculated scores across different genetic ancestry groups?
==============================================================================

Download reference data
-----------------------

The fastest method of getting started is to download a `reference panel`_:

.. code-block:: console

    $ wget https://ftp.ebi.ac.uk/pub/databases/spot/pgs/resources/pgsc_1000G_v1.tar.zst

This example reference panel is based on 1000 Genomes (`Nature 2015`_).

We also provide a reference panel that combines 1000 Genomes with data from the Human Genome
Diversity Project derived from the gnomAD release (v3.1, `Koenig, Yohannes et al. bioRxiv 2023`_),
which includes additional samples and ancestry groups:

.. code-block:: console

    $ wget https://ftp.ebi.ac.uk/pub/databases/spot/pgs/resources/pgsc_HGDP+1kGP_v1.tar.zst

.. _`resources section`: https://www.cog-genomics.org/plink/2.0/resources
.. _`reference panel`: https://ftp.ebi.ac.uk/pub/databases/spot/pgs/resources/
.. _`Nature 2015`: https://doi.org/10.1038/nature15393
.. _`Koenig, Yohannes et al. bioRxiv 2023`: https://doi.org/10.1101/2023.01.23.525248

.. note:: These reference databases are not compatible with the test profile. 
  The test profile is not biologically meaningful, and is only used to test the workflow installed.

Bootstrap reference data
~~~~~~~~~~~~~~~~~~~~~~~~

It's possible to bootstrap (create from scratch) the reference data from the
PLINK 2 data, which is how we create the reference panel tar. See
:ref:`database`

Genetic similarity analysis and score normalisation
----------------------------------------------------------

To enable genetic similarity analysis and score normalisation, just include the
``--run_ancestry`` parameter when running the workflow:

.. code-block:: console

    $ nextflow run pgscatalog/pgsc_calc -profile test,docker \
        --run_ancestry path/to/reference/pgsc_HGDP+1kGP_v1.tar.zst

The ``--run_ancestry`` parameter requires the path to the reference database.

Prepared reference PVARs
~~~~~~~~~~~~~~~~~~~~~~~~

Repeated runs can avoid decompressing the whole-genome reference PVAR once per
target chromosome. Create chromosome-split immutable PVARs with
``scripts/prepare_ancestry_reference.py``, publish them beside its generated
``manifest.json``, and pass their glob to the pipeline:

.. code-block:: console

    $ nextflow run haplotypelabs/pgsc_calc \
        --run_ancestry path/to/reference/pgsc_HGDP+1kGP_v1.tar.zst \
        --prepared_ancestry_pvar 'gs://bucket/reference/v1/*.pvar.zst' \
        --parallel_relabel_afreq true

Prepared PVAR filenames must end in ``_<chrom>.pvar.zst`` for autosomes 1–22.
The original reference archive is still required for reference genotypes,
sample metadata, and relatedness exclusions. ``--parallel_relabel_afreq`` also
parallelises the sample-dependent AFREQ relabel step; AFREQ output cannot be
prepared globally because its variant set depends on the target sample.
