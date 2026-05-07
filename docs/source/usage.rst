LSST Science Pipeline
======================

.. _installation:

Installation & Setup
--------------------

The LSST Science Pipeline shared installation is available in the UZH Science Cluster (S3IT).

We follow the installation method `lsstinstall` (`LSST Install Guide <https://pipelines.lsst.io/install/lsstinstall.html>`_) with version tag ``v29_2_1``. A shared installation is located in ``/shares/soares-santos.physik.uzh/envs/lsst_stack``.

.. code-block:: bash

   # Every time we start a new terminal, we need to set up the environment by running the following commands:
   cd /shares/soares-santos.physik.uzh/envs/lsst_stack
   source loadLSST.sh
   conda activate /shares/soares-santos.physik.uzh/envs/lsst_stack/lsst-scipipe-10.1.0
   setup lsst_distrib

.. _demo:

Quick Demo Pipeline
-------------------

A quick way to check that the setup is working is to run a short demo, as described in detail in the `LSST Demo Pipeline <https://pipelines.lsst.io/install/demo.html>`_. The data required for this test is already available in the shared folder, under:

Navigate to the directory containing the demo data:

.. code-block:: bash

   cd /shares/soares-santos.physik.uzh/demo_data/pipelines_check-29.2.1

Set up the required environment variables and other pre-requisites:

.. code-block:: bash

   setup -r .

Finally, run the demo pipeline:

.. code-block:: bash

   ./bin/run_demo.sh

A successful run will begin by displaying the creation of the Butler object, followed by the execution of the various pipeline stages. As of February 20, 2026, some warning messages may appear at the end of the run; these can be safely ignored. Additionally, if this test is executed on the login node without allocating sufficient memory, it may fail due to inadequate memory resources.

.. _tutorials:

Tutorials
---------

The series of `Getting Started tutorials <https://pipelines.lsst.io/getting-started/index.html>`_ on ``pipelines.lsst.io`` covers the various stages of the LSST Science Pipeline in depth, from setting up a Butler repository through to multi-band catalog analysis. The tutorials are written against the latest weekly release, and the v29.2.1 channel of the docs is occasionally behind the ``weekly`` channel. When in doubt, cross-check with `the weekly version <https://pipelines.lsst.io/v/weekly/getting-started/index.html>`_ of the same page — it is sometimes more accurate for v29.2.1 than the v29.2.1-labeled page itself. The :ref:`v29-tutorial-gotchas` section below documents the cases we have hit so far.

The tutorial dataset (``rc2_subset``) is available in the shared folder. Set up the necessary environment variables and pre-requisites by running:

.. code-block:: bash

   cd /shares/soares-santos.physik.uzh/demo_data
   setup -j -r rc2_subset

Throughout the tutorials, output collections follow the convention ``u/$USER/<step_name>`` (for example ``u/$USER/single_frame``, ``u/$USER/warps``, ``u/$USER/coadds``). The ``u/`` prefix is a per-user namespace inside the Butler registry, so multiple people can run the same tutorial against the same shared repository without overwriting each other's outputs.

Shared tutorial resources
~~~~~~~~~~~~~~~~~~~~~~~~~

The ``rc2_subset`` data and a set of jobscripts that run each tutorial step on the cluster are available under:

.. code-block:: none

   /shares/soares-santos.physik.uzh/demo_data/rc2_subset    # tutorial dataset
   /shares/soares-santos.physik.uzh/demo_data/tutorials     # SLURM jobscripts for each step

The jobscripts are named after the tutorial part they correspond to. Copy them to your own working directory and edit the paths and ``--output`` log file before submitting.

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Jobscript
     - Tutorial step
   * - ``tut1_butler.py``
     - Part 1 — Butler repository sanity check
   * - ``tut2_singframe.sh``
     - Part 2 — single frame processing (``#singleFrame``)
   * - ``tut2_bis_graphq.sh``
     - Part 2 — quantum graph generation for inspection
   * - ``tut4_fgcm.sh``
     - Part 4 — FGCM photometric calibration
   * - ``tut4_gbdes.sh``
     - Part 4 — gbdes astrometric fit
   * - ``tut4_applycalibr.sh``
     - Part 4 — apply the source calibration
   * - ``tut5a_warping.sh``
     - Part 5 — warping (legacy ``#makeWarp`` version, kept for reference)
   * - ``tut5a_bis_warping.sh``
     - Part 5 — warping with the v29.2.1-correct ``#makeDirectWarp,makePsfMatchedWarp`` (use this one)
   * - ``tut5b_coadding.sh``
     - Part 5 — coadd assembly (``#selectDeepCoaddVisits,assembleCoadd``)
   * - ``tut6a_detection.sh``
     - Part 6 — coadd detection and measurement (``#coadd_measurement``)
   * - ``tut6b_forcephoto.sh``
     - Part 6 — forced photometry (``#forcedPhotCoadd`` only; see :ref:`v29-tutorial-gotchas`)

The directory also contains rendered artifacts from past runs (``single_frame.dot``, ``single_frame.qgraph``, ``single_frame.pdf``) that you can use as references for what the quantum graph looks like before committing to a long compute run.

.. note::

   Before kicking off a long ``pipetask run``, dry-build the quantum graph to confirm all inputs resolve. This was the single most useful debugging step we found while validating the v29.2.1 tutorials:

   .. code-block:: bash

      pipetask build \
        -b $RC2_SUBSET_DIR/SMALL_HSC/butler.yaml \
        -i u/$USER/<input_collection> \
        -p $DRP_PIPE_DIR/pipelines/HSC/DRP-RC2_subset.yaml#<subset_or_task> \
        -d "<your data query>" \
        --show pipeline-graph

   This builds the graph but does not execute any quanta. If a required dataset type is missing or unregistered, the error appears in seconds rather than after a multi-hour SLURM job. ``--show pipeline-graph`` also prints the full input/output dataset list per task, which is invaluable for spotting missing prerequisites.

.. _v29-tutorial-gotchas:

Known issues with the v29.2.1 tutorials
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The Getting Started tutorial pages on ``pipelines.lsst.io`` were written against an earlier pipeline release and have not been fully refreshed for v29.2.1. The two issues below will block you from finishing the tutorial end-to-end if followed verbatim.

Part 5 — ``makeWarp`` was split into ``makeDirectWarp`` and ``makePsfMatchedWarp``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The v29.2.1 tutorial page for `Part 5: coadding images <https://pipelines.lsst.io/getting-started/coaddition.html>`_ instructs you to run:

.. code-block:: bash

   -p $DRP_PIPE_DIR/pipelines/HSC/DRP-RC2_subset.yaml#makeWarp

In v29.2.1, the ``makeWarp`` task no longer exists. It has been split into two separate tasks:

- ``makeDirectWarp`` — produces the direct (non-PSF-matched) warps. This is the replacement for what ``makeWarp`` did by default.
- ``makePsfMatchedWarp`` — produces PSF-matched warps used by ``assembleCoadd`` for artifact rejection (``compareWarp``-style assembly).

In ``$DRP_PIPE_DIR/pipelines/HSC/DRP-RC2_subset.yaml``, the production ``nightlyStep3`` subset includes **both** warp tasks before ``assembleCoadd``, which means ``assembleCoadd`` is configured to consume both warp types. Running only ``makeDirectWarp`` leaves the quantum graph for ``assembleCoadd`` unable to resolve its PSF-matched warp inputs.

The corrected command for the warping step is:

.. code-block:: bash

   pipetask run --register-dataset-types \
   -b $RC2_SUBSET_DIR/SMALL_HSC/butler.yaml \
   -i u/$USER/source_calibration,u/$USER/gbdes,u/$USER/fgcm \
   -o u/$USER/warps \
   -p $DRP_PIPE_DIR/pipelines/HSC/DRP-RC2_subset.yaml#makeDirectWarp,makePsfMatchedWarp \
   -d "skymap = 'hsc_rings_v1' AND tract = 9813 AND patch in (38, 39, 40, 41)"

The subsequent coadd assembly step (``#selectDeepCoaddVisits,assembleCoadd``) is unchanged from the tutorial.

.. note::

   You can verify the rename in your installation directly:

   .. code-block:: bash

      grep -E "^\s+(makeWarp|makeDirectWarp|makePsfMatchedWarp):" \
        $DRP_PIPE_DIR/pipelines/HSC/DRP-RC2_subset.yaml

   In v29.2.1 only ``makeDirectWarp`` and ``makePsfMatchedWarp`` will appear; ``makeWarp`` is absent.

Part 6 — the ``forced_objects`` subset has missing prerequisites
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The v29.2.1 tutorial page for `Part 6: measuring sources <https://pipelines.lsst.io/getting-started/photometry.html>`_ instructs you to run:

.. code-block:: bash

   -p $DRP_PIPE_DIR/pipelines/HSC/DRP-RC2_subset.yaml#forced_objects

Running this command after completing the tutorial up to and including ``coadd_measurement`` fails at the quantum graph build stage with two errors:

.. code-block:: none

   Search for dataset type 'pvi' ... is doomed to fail.
   ...
   QuantumGraphBuilderError: No datasets for overall-input 'deepCoadd_Sersic_multiprofit' found
   (the dataset type is not even registered).

Both errors are caused by the ``forced_objects`` subset bundling tasks whose prerequisites are not produced by the preceding tutorial subsets:

- ``forcedPhotCcd`` requires the ``pvi`` (post-visit image) dataset, which is produced by ``reprocessVisitImage`` in the production ``nightlyStep4`` subset. The tutorial never runs ``nightlyStep4``.
- ``transformObjectTable`` requires ``deepCoadd_Sersic_multiprofit``, produced by ``fitDeblendedObjectsSersic``. This task is in ``nightlyStep3`` but **not** in the tutorial-friendly ``coadd_measurement`` subset.

The simplest fix that lets you finish the tutorial is to run only the task whose output Part 7 actually consumes — ``forcedPhotCoadd``, which produces ``deepCoadd_forced_src``:

.. code-block:: bash

   pipetask run --register-dataset-types \
   -b $RC2_SUBSET_DIR/SMALL_HSC/butler.yaml \
   -i u/$USER/coadd_meas \
   -o u/$USER/objects \
   -p $DRP_PIPE_DIR/pipelines/HSC/DRP-RC2_subset.yaml#forcedPhotCoadd \
   -d "skymap = 'hsc_rings_v1' AND tract = 9813 AND patch in (38, 39, 40, 41)"

This is enough to complete Part 7 of the tutorial (loading ``deepCoadd_forced_src`` per band and producing the color-color diagram).

.. note::

   If you want the full tract-level ``objectTable_tract`` output, you need to run the missing prerequisites first:

   .. code-block:: bash

      # 1. Produce the Sersic and PSF Gaussian fits that transformObjectTable needs
      pipetask run --register-dataset-types \
        -b $RC2_SUBSET_DIR/SMALL_HSC/butler.yaml \
        -i u/$USER/coadd_meas \
        -o u/$USER/coadd_meas_extra \
        -p $DRP_PIPE_DIR/pipelines/HSC/DRP-RC2_subset.yaml#fitDeepCoaddPsfGaussians,fitDeblendedObjectsSersic \
        -d "skymap = 'hsc_rings_v1' AND tract = 9813 AND patch in (38, 39, 40, 41)"

      # 2. Then run forced photometry and the object-table tasks (skipping forcedPhotCcd)
      pipetask run --register-dataset-types \
        -b $RC2_SUBSET_DIR/SMALL_HSC/butler.yaml \
        -i u/$USER/coadd_meas_extra \
        -o u/$USER/objects \
        -p $DRP_PIPE_DIR/pipelines/HSC/DRP-RC2_subset.yaml#forcedPhotCoadd,transformObjectTable,writeObjectTable,consolidateObjectTable \
        -d "skymap = 'hsc_rings_v1' AND tract = 9813 AND patch in (38, 39, 40, 41)"

   ``forcedPhotCcd`` is intentionally omitted because it requires ``pvi`` from ``reprocessVisitImage`` (a ``nightlyStep4`` task). The production pipeline notes that many ``forcedPhotCcd`` quanta are expected to fail when run without the full upstream chain.

.. warning::

   The ``echo "Job completed successfully!"`` line at the end of the SLURM jobscripts runs unconditionally after ``pipetask`` exits, so it does **not** indicate that ``pipetask`` itself succeeded. Always check the job log for Python tracebacks, or add ``set -e`` near the top of the jobscript so the shell aborts on the first failed command.

Using DS9 on the UZH Science Cluster
=====================================

This guide explains how to launch SAOImageDS9 on the UZH Science IT cluster
from a Mac, including the required one-time setup of XQuartz for X11 display
forwarding.

.. contents:: Table of Contents
   :local:
   :depth: 2

Prerequisites: Install XQuartz (Mac only)
-----------------------------------------

DS9 is a graphical application. To display it on your local Mac screen while
running on the cluster, you need **XQuartz**, a free X11 server for macOS.
This is a one-time setup.

1. Download and install XQuartz from https://www.xquartz.org
2. **Log out and log back into your Mac** after installation (required).
3. Open XQuartz from ``Applications > Utilities``.

.. note::
   After the initial setup you can use any terminal app (e.g. the default
   Mac Terminal) — XQuartz just needs to be installed and you need to have
   logged out/in at least once.

Connecting to the Cluster with X11 Forwarding
----------------------------------------------

Always connect using the ``-Y`` flag to enable X11 forwarding:

.. code-block:: bash

   ssh -Y <user>@cluster.s3it.uzh.ch

After logging in, verify that the display is set correctly:

.. code-block:: bash

   echo $DISPLAY

You should see output like ``localhost:12.0``. If this is empty, X11
forwarding is not working — check that XQuartz is installed and that you
reconnected after installing it.

Launching DS9
-------------

A dedicated conda environment with DS9 and all its dependencies has been
set up at:

.. code-block:: none

   /shares/soares-santos.physik.uzh/envs/ds9env/

Activate it and launch DS9 in the background:

.. code-block:: bash

   conda activate /shares/soares-santos.physik.uzh/envs/ds9env
   ds9 &

The ``&`` runs DS9 as a background process, keeping your terminal free.
A DS9 window will appear on your local Mac screen after a few seconds.

.. note::
   The ds9env environment is separate from the LSST stack environment.
   DS9 and the LSST stack communicate via XPA sockets, so they do not
   need to share the same conda environment.

Using DS9 with the LSST Stack
------------------------------

.. important::
   Both terminals must be on the **same login node**. XPA communication
   between DS9 and the LSST stack only works within the same node. The
   cluster has multiple login nodes (e.g. ``u24-login-1``, ``u24-login-2``,
   ``u24-login-3``) and connections may land on different ones by default.

Open two terminals, both connected to the **same node** with ``ssh -Y``.
Verify this before starting:

.. code-block:: bash

   hostname  # run in both terminals — output must match

**Terminal 1** — launch DS9:

.. code-block:: bash

   conda activate /shares/soares-santos.physik.uzh/envs/ds9env
   ds9 &

**Terminal 2** — run your LSST Python session:

.. code-block:: bash

   conda activate /shares/soares-santos.physik.uzh/envs/lsst_stack/lsst-scipipe-10.1.0
   python

Before running Python, verify that DS9 is visible via XPA:

.. code-block:: bash

   xpaaccess ds9

It should return ``yes``. If it returns ``no``, DS9 is either not running
or the two terminals are on different nodes. Check the Troubleshooting
section below.

Then inside Python:

.. code-block:: python

   import lsst.afw.display as afwDisplay

   afwDisplay.setDefaultBackend('ds9')
   display = afwDisplay.getDisplay()

   # Load and display a calexp
   calexp = butler.get('calexp', visit=1204, detector=41)
   display.mtv(calexp)

.. warning::
   Make sure DS9 is already running **before** calling ``display.mtv()``,
   otherwise you will get an ``XPA$ERROR no access points match`` error.

Troubleshooting
---------------

**$DISPLAY is empty after ssh -Y**
   XQuartz is not installed or you have not logged out and back into your
   Mac since installing it. See the Prerequisites section above.

**ds9: error while loading shared libraries: libXss.so.1**
   You are not using the ``ds9env`` conda environment. Activate it with
   ``conda activate /shares/soares-santos.physik.uzh/envs/ds9env``.

**XPA$ERROR no 'xpaset' access points match template: ds9**
   Either DS9 is not running, or the two terminals are on different login
   nodes. First check that DS9 is accessible:

   .. code-block:: bash

      xpaaccess ds9  # should return "yes"

   Then verify both terminals are on the same node:

   .. code-block:: bash

      hostname  # run in both terminals — output must match

**DS9 freezes the terminal**
   You launched DS9 without ``&``. Kill it with ``Ctrl+C`` and relaunch
   with ``ds9 &``.

**WCS does not have an attached FITS approximation**
   Use ``display.mtv(calexp.image)`` instead of ``display.image(calexp)``
   to skip WCS serialization:

   .. code-block:: python

      display.mtv(calexp.image)

Submitting Single Frame Image Processing Jobs to the Cluster
============================================================

.. contents:: Table of Contents
   :local:
   :depth: 2

Some steps of image processing can be time and resource-intensive. To speed up the process, tasks can be parallelized. 
However, it is important to carefully select the number of cores and memory to ensure the job completes successfully. 
Below is an example of how to submit a `singleFrame` task, as described in the tutorial:

.. code-block:: bash

   #!/bin/bash
   #SBATCH --job-name=singleFrame
   #SBATCH --time=29:00:00
   #SBATCH --nodes=1
   #SBATCH --ntasks=8
   #SBATCH --mem-per-cpu=8G
   #SBATCH --output=log/singleFrame_02032026.log 

   # Initialize the LSST Science Pipeline
   cd /shares/soares-santos.physik.uzh/envs/lsst_stack
   source loadLSST.sh
   conda activate /shares/soares-santos.physik.uzh/envs/lsst_stack/lsst-scipipe-10.1.0
   setup lsst_distrib

   # Load environment variables specific to the tutorial data
   cd /shares/soares-santos.physik.uzh/demo_data
   setup -j -r rc2_subset

   # Run the singleFrame task
   pipetask run --register-dataset-types \
   -b $RC2_SUBSET_DIR/SMALL_HSC/butler.yaml \
   -i HSC/RC2/defaults \
   -o u/$USER/single_frame \
   -p $DRP_PIPE_DIR/pipelines/HSC/DRP-RC2_subset.yaml#singleFrame \
   -j 8

   echo "Job completed successfully!"

The process is expected to complete in approximately 1 hour and 24 minutes, with a peak memory usage of 48 GB.