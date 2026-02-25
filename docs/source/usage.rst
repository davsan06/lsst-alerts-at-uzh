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

The series of `tutorials <https://pipelines.lsst.io/>`_ covers the various stages of the LSST Science Pipeline in depth. Necessary data for the tutorials is available in the shared folder, under:

.. code-block:: bash

   cd /shares/soares-santos.physik.uzh/demo_data

Set up the necessary environment variables and pre-requisites by running:

.. code-block:: bash

   setup -j -r rc2_subset

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

[DSC: to be updated]

Always connect using the ``-Y`` flag to enable X11 forwarding:

.. code-block:: bash

   ssh -Y davisa@cluster.s3it.uzh.ch

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

Always connect to a specific node explicitly:

.. code-block:: bash

   ssh -Y davisa@u24-login-1.cluster.s3it.uzh.ch

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

   If the hostnames differ, reconnect both terminals to the same node:

   .. code-block:: bash

      ssh -Y davisa@u24-login-1.cluster.s3it.uzh.ch

**DS9 freezes the terminal**
   You launched DS9 without ``&``. Kill it with ``Ctrl+C`` and relaunch
   with ``ds9 &``.

**WCS does not have an attached FITS approximation**
   Use ``display.mtv(calexp.image)`` instead of ``display.image(calexp)``
   to skip WCS serialization:

   .. code-block:: python

      display.mtv(calexp.image)
