Usage
=====

.. _installation:

Installation & setup
--------------------

LSST Science Pipeline shared installation available in the UZH Science Cluster (S3IT).

We follow the installation method lsstinstall (`LSST Install Guide <https://pipelines.lsst.io/install/lsstinstall.html>`_) with version tag ``v29_2_1``. A shared installation lives in ``/shares/soares-santos.physik.uzh/envs/lsst_stack``.

.. code-block:: bash

   # Every time we start a new terminal we have to setup the environment by running the following commands:
   cd /shares/soares-santos.physik.uzh/envs/lsst_stack
   source loadLSST.sh
   conda activate /shares/soares-santos.physik.uzh/envs/lsst_stack/lsst-scipipe-10.1.0
   setup lsst_distrib

Quick demo pipeline
--------------------

A quick way to check that the setup is working fine is to run a short demo, as described in detail in `LSST Demo Pipeline <https://pipelines.lsst.io/install/demo.html>`_ . The data required for this
test is already available in the shared folder, under 

.. code-block:: bash
   cd /shares/soares-santos.physik.uzh/demo_data/pipelines_check-29.2.1

Export the required environment variables and other pre-requisites:

.. code-block:: bash
   setup -r .

And finally run the demo pipeline:

.. code-block:: bash
   ./bin/run_demo.sh

A successful run will begin by displaying the creation of the Butler object, followed by the execution of the various pipeline stages. As of February 20, 2026, some warning messages may appear at the end of the run; these can be safely ignored. Additionally, if this test is executed on the login node without allocating sufficient memory, it may fail due to inadequate memory resources.

Tutorials
---------

The series of `tutorials <https://pipelines.lsst.io/#l>`_ available cover in-depth the various stages of the LSST Science Pipeline. Necessary data for the tutorials is available in the shared folder, under

.. code-block:: bash
   cd /shares/soares-santos.physik.uzh/demo_data

and necessary environment variables and pre-requisites can be set up by running

.. code-block:: bash
   setup -r -j rc2_subset