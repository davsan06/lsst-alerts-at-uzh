Usage
=====

.. _installation:

Installation
------------

LSST Science Pipeline shared installation available in the UZH Science Cluster (S3IT).

We follow the installation method lsstinstall (`LSST Install Guide <https://pipelines.lsst.io/install/lsstinstall.html>`_) with version tag ``v29_2_1``. A shared installation lives in ``/shares/soares-santos.physik.uzh/envs/lsst_stack``.

.. code-block:: bash

   # Every time we start a new terminal we have to setup the environment by running the following commands:
   cd /shares/soares-santos.physik.uzh/envs/lsst_stack
   source loadLSST.sh
   setup lsst_distrib

The installation has been successfully tested by running the demo pipeline (`LSST Demo Pipeline <https://pipelines.lsst.io/install/demo.html>`_).

