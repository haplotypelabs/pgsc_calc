Benchmark instrumentation
=========================

Use the ``benchmark`` profile alongside the normal execution profile::

    nextflow run haplotypelabs/pgsc_calc \
      -r <revision> \
      -profile docker,benchmark \
      -work-dir /mnt/ssd/work \
      --outdir /mnt/ssd/results \
      <normal pipeline parameters>

The pipeline already writes its execution trace, timeline, report, and DAG to
``<outdir>/pipeline_info``. The benchmark profile expands the trace fields and adds
``PGSC_BENCHMARK_TASK_START`` and ``PGSC_BENCHMARK_TASK_END`` records to each task log.

Nextflow keeps the exact generated commands and their output in the work directory.
On an ephemeral runner, preserve these files before shutdown::

    cd /mnt/ssd/work
    find . -type f \
      \( -name '.command.sh' -o -name '.command.run' -o -name '.command.out' \
         -o -name '.command.err' -o -name '.command.log' -o -name '.command.trace' \
         -o -name '.exitcode' \) \
      -print0 | tar --null -czf /mnt/ssd/results/pipeline_info/task-command-logs.tar.gz --files-from -

Also preserve ``.nextflow.log`` from the launch directory. The task archive can contain
input paths and command-line parameters, so treat it as diagnostic data rather than a
public pipeline result.
