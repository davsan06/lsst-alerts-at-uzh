=================
DECam Data Processing Using the LSST Science Pipelines
=================

This note summarizes the ingestion and data reduction process for DECam data, using the Rubin Observatory LSST Science Pipelines.

There are three primary DECam dataset types:

* object:

    * primary science frames
    * observation type: object
    * filters:

        * ``N395 DECam c0015 3950.0 100.0``
        * ``M411 DECam c0017 4112.0 264.0``
        * ``M438 DECam c0019 4380.0 260.0``
        * ``M464 DECam c0018 4640.0 264.0``
        * ``M490 DECam c0020 4900.0 260.0``
        * ``M517 DECam c0021 5170.0 260.0``
        * ``N540 DECam c0014 5403.0 210.0``
        * **TODO: Add others**

    * data storage locations on s3it: ``/shares/soares-santos.physik.uzh/fitsFiles/desgw/single-epoch/*.fits.fz``

* zero:

    * bias frames
    * observation type:
    * data storage locations on s3it: ``/shares/soares-santos.physik.uzh/fitsFiles/desgw/bias/*.fits.fz``

* domeflat:

    * flat frames
    * observation type:
    * data storage locations on s3it: ``/shares/soares-santos.physik.uzh/fitsFiles/desgw/flat/*.fits.fz``

The DECam focal plane - **Add image here at some point**.

The DECam Focal Plane; figure from Diehl et al. 2018. DECam focal plane showing the 62 2k x 4k CCDs, 8 2k x 2k CCDs (labeled "F") for the adaptive optics system, and 4 2k x 2k CCDs (labeled "G") for guiding. The orientation of the sky is indicated. The black label (e.g., S30) indicates a position on the focal plane. The green label (e.g., 2) indicates the number of the CCD as is in the multi-extension FITS header. When the focal plane is viewed with the real-time display at the telescope or with default SAOImage DS9 settings, the direction labeled "north" is displayed to the left and "east" at the top. The background colors of the CCDs indicate the electronics backplane that reads them out.

Preparing the Science Pipelines
=================

Set up the Science Pipelines
--------------------------------

First, the LSST Science Pipelines ("the stack") needs to be set up on the science cluster machine. Typically, this is best executed on an interactive node, and not a login node. To support this, you can define two aliases in your `~/.bashrc` file. ::

    alias start_interactive_node="srun --export=ALL --time=1:00:00 --mem=16G --nodes=1 --ntasks=1 --pty /bin/bash"
    alias lsst_setup_uzh="module load miniforge3; source /shares/soares-santos.physik.uzh/envs/lsst_stack/loadLSST_uzh.sh; conda activate /shares/soares-santos.physik.uzh/envs/lsst_stack/lsst-scipipe-10.1.0;setup lsst_distrib -c"``


This will set up the most recent Rubin environment installed on the machine. A list of other installed Rubin environments is shown using mamba: ``mamba env list``.

Register new filters
--------------------------------

This step is only required if the data to be ingested uses a filter which is not already defined. Before being able to ingest raw science frames, all necessary filters being ingested need to be defined in the relevant ``obs_`` package (Update, and also in the skymap repo - see the end of this section for further details). Here, the relevant package is ``obs_decam``, and the filters file is located at ``obs_decam/python/lsst/obs/decam/decamFilters.py``.

For this example, the required observation filter (``M438 DECam c0019 4380.0 260.0``) was not previously defined and had to be added manually. This modification has now been merged into the main branch, but the instructions on how to do this are maintained here, for reference. As a recap, to do so, first, git clone the ``obs_decam`` package into a local directory: ::

    OBSDECAM=/shares/soares-santos.physik.uzh/repos/obs_decam
    git clone git@github.com:lsst/obs_decam.git $OBSDECAM``
    cd $OBSDECAM``

If this is the first time the package has been cloned, it will also need to be built using scons (as with all Science Pipelines packages), e.g.: ::

    scons -j8

Next, we checkout a user branch from the main branch to work on: ::

    git checkout -b u/seanmacb/gwprimo

Now add the relevant filter definition. In this case: ::

    FilterDefinition(physical_filter="M438 DECam c0019 4380.0 260.0",band="M438")

Finally, make sure both ``lsst_distrib`` and the relevant ``obs_`` package (obs_decam here) are set up in the working shell: ::

    setup -j -r $OBSDECAM

Double check that the local package has been loaded using: ::

    eups list | grep LOCAL
    #   obs_decam             LOCAL:/shares/soares-santos.physik.uzh/repos/obs_decam

Once complete, subsequent processing should be able to proceed.

| If a warning similar to ingest WARN: Exposure DECam:ct4m20210318t032843 could not be registered: (sqlite3.IntegrityError) FOREIGN KEY constraint failed is returned, check that all filters are correctly assigned in the filters file.

Note: after a new filter has been defined, you will need to update the camera defintion by re-registering the instrument: ::

    butler register-instrument $REPO lsst.obs.decam.DarkEnergyCamera --update

Finally, refObjLoader lookups to the new filter need to be added to a number of obs_decam config files to facilitate astrometric matching. This allows data processing to proceed beyond characterizeImage, i.e., the final step required to produce a calexp. Here, we map the new M438 filter into the existing g-band filter (the nearest broad-band filter in wavelength) by adding lines similar to: ::

    refObjLoader.filterMap['M438'] = 'g'

into: ::

    config/characterizeImage.py
    config/calibrate.py
    config/measureCoaddSources.py

New filters also need to be registered in the skymap repository. Central wavelengths for all required filters should be added to ``python/lsst/skymap/packers.py``.

Create a new butler
--------------------------------

A new butler will be created. Here we set aliases for the output repository directory: ::

    REPO=/shares/soares-santos.physik.uzh/ButlerProjects/DESGW
    mkdir -p $REPO
    chmod ug+rw $REPO

Whilst optional, it may be desirable to also construct a log directory, for log files to be stored within: ::

    LOGDIR=/shares/soares-santos.physik.uzh/ButlerProjects/logs
    mkdir -p $LOGDIR
    chmod ug+rw $LOGDIR

If this repository will be used by more than one user, modify the permissions of the output repository directory to ensure that all files constructed below are writeable by all members of that user group: ::

    cd $REPO
    umask 2

| Note: if changing permissions after the butler has been used, and if using an SQLite database (see below), you will also need to run chmod ug+rw gen3.sqlite3 to make the SQLite database read/writable to all members of your group. You will also need to run chmod ug+rw u to make the user output directory (here named u) read/writable to all members of your group.

Next, an empty Gen3 Butler repository is created, and then the instrument is registered in the data repository. In this example, the instrument is the Dark Energy Camera (DECam).

There are two types of database that be be constructed for use with the butler, either a SQLite database, or a PostgreSQL database. The former is default, and simpler to set up. The latter provides significantly improved data processing times, but requires a PostgreSQL database to have already been set up on the data processing machine in advance.

Create a SQLite database (quickest and easiest)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

On the command line, create a butler repo: ::

  butler create $REPO

This constructs a butler.yaml file in the $REPO directory.

| Note: after the gen3.sqlite3 file has been constructed, you may have to manually add write permissions for group members by running the command: ``chmod g+w gen3.sqlite3``.


Use Butler with a PostgreSQL Database
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

We have a PostgreSQL database running on the Science Cloud at UZH, with two databases

- ``butler_main``: For final data products / production registry
- ``butler_testing``: Secondary database which can be used as a testing target without disturbing the main registry.

To setup copy the contents from https://wiki.physik.uzh.ch/cosmo/doku.php?id=science:alerts:cloud:postgres into ``~/.pgpass`` on the machine you want to connect to PostgreSQL from (either your own machine or your Science-Cluster account home director).

- This file contains the PostgreSQL passwords! Keep them secret!
- Set the file ownership as: ``chmod 0600 ~/.pgpass``

  + **If you do not do this things will fail without error!**

The setup of a PostgreSQL database for use with Butler for DEcam and LSST processing at UZH on the Science Cloud is documented in :doc:`postgres`.


Register the instrument
--------------------------------

Once the butler repo has been created, register the instrument: ::

    butler register-instrument $REPO lsst.obs.decam.DarkEnergyCamera

The register-instrument command will need to be re-run (once only) every time a new filter is added to the filter definitions file.

| Note: the instrument name here needs to be the fully qualified name of an instrument subclass. Full names can be inferred from their respective ``obs_`` package at github.com/lsst. For this example, the relevant ``obs_`` package is ``obs_decam`` and the fully qualified name is ``lsst.obs.decam.DarkEnergyCamera``.

Finally, double check that all required filters are correctly registered with the butler: ::

    butler query-dimension-records $REPO physical_filter

In this case, double check that ``M438 DECam c0019 4380.0 260.0`` appears in the filter list.

Generate reference catalogues
--------------------------------

The Science Pipelines require reference catalogues ("refcats") to accurately calibrate photometric and astrometric results. Two reference catalogues are required here: Gaia DR2 for astrometry, and Pan-STARRS PS1 for photometry.Further information is also available on the Community forum and on pipelines.lsst.io.

A number of different methods are available to ingest these catalogues. For our purposes, you can yse `butler ingest-files`.

Ingesting survey reference catalogues
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The first step in constructing these reference catalogues is to gather the catalogue data together and ingest the files. This process is decidedly non-trivial, and may require several hours to complete even on a high-powered machine.

If ingesting for the first time, all raw files can be downloaded at the link described in [this comment](https://community.lsst.org/t/gaia-dr2-reference-catalog-in-lsst-format/3901/6) on the Community forum.

Fortunately for our purposes, these downloaded FITS files already exist on the machine used here, and can be used directly: ::

    GAIADR2=/shares/soares-santos.physik.uzh/refcats/GAIA_DR3/gaia_dr3
    PANSTARRSPS1=/shares/soares-santos.physik.uzh/refcats/ps1_pv3_3pi


Once the files are in place, we need to create astropy-readable .ecsv table files containing one row per input file in each reference catalogue. To construct these, in Python: ::

    import os
    import glob
    import astropy.table

    # output directory to save .ecsv files
    outdir = "/home/smacbr"

    # full paths to LSST sharded reference catalogues
    gaiadr3 = "/shares/soares-santos.physik.uzh/refcats/GAIA_DR3/gaia_dr3"
    panstarrsps1 = "/shares/soares-santos.physik.uzh/refcats/ps1_pv3_3pi"

    refcat_dirs = [
    gaiadr3,
    panstarrsps1,
    ]

    # loop over each FITS file in all refcats
    # note: this constructs a series of .ecsv files, each containing two columns:
    # 1) the FITS filename, and 2) the htm7 pixel index
    for refcat_dir in refcat_dirs:

        outfile = f"{outdir}/{os.path.basename(refcat_dir)}.ecsv"
        print(f"Saving to: {outfile}")

        table = astropy.table.Table(names=("filename", "htm7"), dtype=("str", "int"))
        files = glob.glob(f"{refcat_dir}/[0-9]*.fits")

        for ii, file in enumerate(files):
            print(f"{ii}/{len(files)} ({100*ii/len(files):0.1f}%)", end="\r")
            # try/except to catch extra .fits files which may be in this dir
            try:
                file_index = int(os.path.basename(os.path.splitext(file)[0]))
            except ValueError:
                continue
            else:
                table.add_row((file, file_index))

        table.write(outfile)


| Note: the above script running on an interactive node took ~20 minutes, 10 minutes per reference catalogue.

A .ecsv file should now exist for each reference catalogue. Next, register the dataset types for each reference catalogue with the butler: ::

    butler register-dataset-type $REPO gaia_dr3 SimpleCatalog htm7
    butler register-dataset-type $REPO ps1_pv3_3pi SimpleCatalog htm7

Check that both the Gaia DR2 and Pan-STARRS PS1 dataset types are now available using: ::

    butler query-dataset-types $REPO

Finally, ingest the LSST-formatted files into the refcats/gen3 RUN collection in the repository: ::

    butler ingest-files -t link $REPO gaia_dr2 refcats/gen3 gaia_dr2.ecsv
    butler ingest-files -t link $REPO ps1_pv3_3pi refcats/gen3 ps1_pv3_3pi.ecsv

Using ``butler transfer-datasets``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If a butler already exists on the machine, the refcat datasets can be transferred over from the existing butler directly: ::

    LOGFILE=$LOGDIR/transfer_refcats.log; \
    date | tee $LOGFILE; \
    butler transfer-datasets --register-dataset-types \
    -t copy --collections refcats/gen3 \
    $OLD_REPO $NEW_REPO \
    2>&1 | tee -a $LOGFILE; \
    date | tee -a $LOGFILE

| Note: This command can take a while.

Once the refcats are in place, their collection can be confirmed: ::

    butler query-collections $REPO "refcats*"

Following a dataset transfer, it may be necessary to set up the parent refcats parent CHAINED collection which contains a comma-separated list of all of the transferred child refcats/... RUN collections: ::

    PARENT=refcats; \
    CHILDREN=refcats/gen3; \
    butler collection-chain $REPO $PARENT $CHILDREN

Register the skyMap
--------------------------------

Make a sky map and add it to the repository. Sky maps exist as dimensions, datasets and collections.

This command registers the DECam skyMap dataset using the default obs_decam configuration, and setting the output name to the commonly used and de-facto standard decam_rings_v1: ::

    LOGFILE=$LOGDIR/register_decam_rings_v1.log; \
    date | tee $LOGFILE; \
    butler register-skymap $REPO \
    -C $OBS_DECAM_DIR/config/makeSkyMap.py \
    -c name='decam_rings_v1' \
    2>&1 | tee -a $LOGFILE; \
    date | tee -a $LOGFILE

| Note: the runtime for this command was ~5 minutes.

If other skymaps, such as the HSC skymap, are also required, they may be generated as well: ::

    LOGFILE=$LOGDIR/register_hsc_rings_v1.log; \
    date | tee $LOGFILE; \
    butler register-skymap $REPO \
    -C $OBS_SUBARU_DIR/config/makeSkyMap.py \
    -c name='hsc_rings_v1' \
    2>&1 | tee -a $LOGFILE; \
    date | tee -a $LOGFILE

Check that all required skyMap dataset types now exist in the skymaps run collection in the Butler repo: ::

    butler query-datasets $REPO skyMap

| Note: this sky map step doesn't really need to be performed until much later, however, if any errors occur during registration of the sky map, it may be necessary to delete the repo and start afresh. For this reason, it's usually better to perform this step as soon as possible.

Write curated calibrations
--------------------------------

Curated calibrations are collections of calibration data which describe various aspects of the camera and survey. If setting up a new butler on a new machine, an instrument's curated calibrations will need to be added to the data repository: ::

    butler write-curated-calibrations $REPO lsst.obs.decam.DarkEnergyCamera

| Note: if the modified version of `rootRepoConverter.py` was used above, the dataset types added by this command may already have been ingested into the repo. If so, running the above command will fail with an error similar to A database constraint failure was triggered by inserting one or more datasets of type DatasetType('camera', {instrument}, Camera, isCalibration=True) into collection 'DECam/calib/unbounded'. This probably means a dataset with the same data ID and dataset type already exists, but it may also mean a dimension row is missing.

The instrument may be specified via either the fully qualified name, as above, or the short name (DECam here). The -h help file indicates the former is required, but this advice may change in the future.

This currently adds camera, crosstalk, defects and linearizer dataset types into the repository within a number of collections (DECam/calib, DECam/calib/unbounded, and DECam/calib/curated/{timestamp}). Check the current collections within the repo using: ::

    butler query-collections $REPO "DECam/calib*"


Ingesting data
=================

Ingesting raw data
--------------------------------

We're now prepared to ingest raw science frames. If raw frames are being stored in multiple directories, this command needs to be repeated for each directory. Alternatively, a sufficient glob which is able to locate all files of interest may be supplied. Here's an example data ingest command: ::

   LOGFILE=$LOGDIR/ingest_science.log; \
   SCIFILES=/path/to/science/raw/images/raw_*.fz; \
   date | tee $LOGFILE; \
   butler ingest-raws $REPO $SCIFILES --transfer link \
   2>&1 | tee -a $LOGFILE; \
   date | tee -a $LOGFILE

Raw science exposures have now been added to the ``DECam/raw/all`` collection in the repo. Collections define groups of data, and can be listed (and searched) using: ::

   butler query-collections $REPO "DECam/raw/all"

Ingested exposures can be listed on the command line using: ::

   butler query-dimension-records $REPO exposure \
   --where "instrument='DECam' AND exposure.observation_type='science'"

This view shows all available dimensions associated with each ingested science image, including the observation ID, the physical filter, and the observation type. Alternatively, datasets can be queried directly using query-datasets, with optional SQL-like ``--where`` arguments to search specific dimensions, e.g.: ::

   WHERE="instrument='DECam' AND exposure=123456"

   WHERE="instrument='DECam' AND detector=1"

   WHERE="instrument='DECam'
   AND exposure.observation_type='science'
   AND exposure.day_obs > 20250830
   AND exposure.day_obs < 20250902
   AND detector=1"

   butler query-datasets $REPO --where $WHERE raw

| Note: To successfully use the ``--where`` argument, other dimensions may be required, such as instrument. The butler will complain with a UserExpressionError if a required dimension is not found.

A list of science exposure IDs can similarly be extracted within python: ::

   queryData = butler.registry.queryDatasets
   where = "exposure.observation_type='science' AND detector=1"
   exps = list(queryData("raw", collections="DECam/raw/all",
                         instrument="DECam", where=where))
   expids = tuple(x.dataId["exposure"] for x in exps)
   print(f'SCIEXPS="{expids}"')

The test dataset used here returns a list of science exposures: ::

   SCIEXPS="(971666, 971667, 971668, ..., 1068723)"

Ingesting calib data
--------------------------------

Ingesting bias data
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

As with the raw science frames above, raw bias frames ('zero') are also ingested: ::

   LOGFILE=$LOGDIR/ingest_bias.log; \
   BIASFILES=/path/to/raw/bias/images/raw_*.fz; \
   date | tee $LOGFILE; \
   butler ingest-raws $REPO $BIASFILES --transfer link \
   2>&1 | tee -a $LOGFILE; \
   date | tee -a $LOGFILE

| Note: The runtime for this command was ~1 minute, ingesting 3100 distinct Butler datasets from 50 exposures.

Bias exposures have now been ingested into the repo. Check that the bias calibration frames have been successfully ingested using: ::

   butler query-dimension-records $REPO exposure \
   --where "instrument='DECam' AND exposure.observation_type='zero'"

A list of bias exposure IDs can be extracted within python: ::

   queryData = butler.registry.queryDatasets
   where = "exposure.observation_type='zero' AND detector=1"
   exps = list(queryData("raw", collections='DECam/raw/all',
                         instrument="DECam", where=where))
   expids = tuple(x.dataId["exposure"] for x in exps)
   print(f'BIASEXPS="{expids}"')

The test dataset used here returns this list of bias exposures: ::

   BIASEXPS="(970488, 970489, 970490, ... 971166)"

Ingesting flat data
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The final set of data to be ingested are the raw flat frames ('dome flat'): ::

   LOGFILE=$LOGDIR/ingest_flat.log; \
   FLATFILES=/path/to/flat/raw/images/raw_*.fz; \
   date | tee $LOGFILE; \
   butler ingest-raws $REPO $FLATFILES --transfer link \
   2>&1 | tee -a $LOGFILE; \
   date | tee -a $LOGFILE

| Note: The runtime for this command was ~5 minutes, ingesting 6200 distinct Butler datasets from 100 exposures.

Flat exposures have now been ingested into your repo. Check that the flat calibration frames have been successfully ingested using: ::

   butler query-dimension-records $REPO exposure \
   --where "instrument='DECam' AND exposure.observation_type='dome flat'"

| Note: if an attempt is made to ingest a file which was already been ingested, the science pipelines will fail for that particular file. This behaviour is as expected, and not a cause for concern.

A list of flat exposure IDs can be extracted within python: ::

   queryData = butler.registry.queryDatasets
   where = "exposure.observation_type='dome flat' AND detector=1"
   exps = list(queryData("raw", collections="DECam/raw/all",
                         instrument="DECam", where=where))
   expids = tuple(x.dataId["exposure"] for x in exps)
   print(f'FLATEXPS="{expids}"')

The test dataset used here returns this list of flat exposures: ::

   FLATEXPS="(970228, 970229, ... 1054292)"


Defining visits
--------------------------------

Once all raw data has been ingested, we can define visits from exposures in the butler registry. This sets up the exposure IDs within the butler, allowing future runs to use this information when using the -d or --where data queries. Without this step, processing steps after ISR (i.e., characterizeImage onwards) will fail with ``RuntimeError: QuantumGraph is empty.``. ::

   LOGFILE=$LOGDIR/define_visits.log; \
   date | tee $LOGFILE; \
   butler define-visits $REPO lsst.obs.decam.DarkEnergyCamera \
   2>&1 | tee -a $LOGFILE; \
   date | tee -a $LOGFILE

Calibration
=================

Determine calibration frame validity ranges
--------------------------------
Now that raw bias (zero) and dome flat calibration frames have been ingested, validation date ranges need to be determined. For DESGW, we opt to construct calibraton frames which are certified across the entire timespan of our data; from 2023-05-01 to 2025-12-01.

Build bias frames
--------------------------------

Next, the master bias frames are built. These frames need to be built for each valid date range (see section above).

First, check the build pipeline: ::

   pipetask build \
   -p $CP_PIPE_DIR/pipelines/DECam/cpBias.yaml \
   --show pipeline

It's best to pipe this into some output .yaml, which I will call ``cp_bias.yaml``, and review it before running.

The ``cpBias`` pipeline may also be viewed graphically: ::

   pipetask build \
   -p $CP_PIPE_DIR/pipelines/DECam/cpBias.yaml \
   --pipeline-dot /tmp/pipeline.dot; \
   dot /tmp/pipeline.dot -Tpdf > $LOGDIR/pipeline_cpBias.pdf

Build master bias (zero) frames, ensuring that all required input collections are given as arguments to -i: ::

   BIASEXPS="(1249372, 1249373, 1258298, 1258299, 1278668, 1288161, 1288162, 1288163, 1298843, 1298844, 1300533, 1302332, 1302333, 1302685, 1302686, 1302687, 1302688, 1324835, 1324836, 1324837, 1343446, 1343447, 1343451, 1343452, 1343480, 1343481, 1343482, 1343986, 1343987, 1343988, 1344182, 1344183, 1344184, 1390552, 1390553, 1390700, 1390701, 1413071, 1413072, 1413073, 1439507, 1443176, 1443177)"
   LOGFILE=$LOGDIR/pilot_cpBias.log; \
   date | tee $LOGFILE; \
   pipetask --long-log run --register-dataset-types -j 12 \
   -b $REPO --instrument lsst.obs.decam.DarkEnergyCamera \
   -i DECam/raw/all,DECam/calib/curated/19700101T000000Z,DECam/calib/unbounded \
   -o DECam/calib/desgw_pilot/bias \
   -p $CP_PIPE_DIR/pipelines/DECam/cpBias.yaml \
   -d "instrument='DECam' AND exposure IN $BIASEXPS" \
   2>&1 | tee -a $LOGFILE; \
   date | tee -a $LOGFILE

The above command requires the definition of ``BIASEXPS``, which can be done in python: ::

   import lsst.daf.butler as daf_butler
   but = daf_butler.Butler("/shares/soares-santos.physik.uzh/ButlerProjects/DESGW")
   queryData = but.registry.queryDatasets
   where = "exposure.observation_type='zero' AND detector=1"
   exps = list(queryData("raw", collections='DECam/raw/all',instrument="DECam", where=where))
   expids = tuple(x.dataId["exposure"] for x in exps)
   print(f'BIASEXPS="{expids}"')
   expids = tuple(x.dataId["exposure"] for x in exps)
   print(f'BIASEXPS="{expids}"')
   >> BIASEXPS="(1249372, 1249373, 1258298, 1258299, 1278668, 1288161, 1288162, 1288163, 1298843, 1298844, 1300533, 1302332, 1302333, 1302685, 1302686, 1302687, 1302688, 1324835, 1324836, 1324837, 1343446, 1343447, 1343451, 1343452, 1343480, 1343481, 1343482, 1343986, 1343987, 1343988, 1344182, 1344183, 1344184, 1390552, 1390553, 1390700, 1390701, 1413071, 1413072, 1413073, 1439507, 1443176, 1443177)"

To avoid an error regarding missing defects dataset types, an input collection containing defects must also be supplied in the ``cpBias`` run. Here, these data will be ingested into the repo when running ``write-curated-calibrations``, for example. The instructions here make use of the ``DECam/calib/curated/19700101T000000Z`` collection. Other collections containing ``defects`` are also available, however, some of the commonly unused detectors are missing (i.e., there are <62). If defects data are not available at all, adding ``-c isr:doDefect=False`` to the ``pipetask run`` command will disable defect masking when running the ``cpBias`` pipeline.

On occasion, some of the tasks (quanta) may fail, likely due to memory issues. In such cases, an afterburner can be run on a single core to try the failed tasks again. To do so, add ``--extend-run`` and ``--skip-existing`` to the ``pipetask run`` command, and remove ``-j N`` to prevent it from running on multiple cores. This will help ensure that the most memory-intensive quanta will not request too much simultaneous memory usage.

Check the collections, dataset types and datasets now present in the repo: ::

   butler query-collections $REPO "*bias*"
   butler query-dataset-types $REPO
   butler query-datasets $REPO --collections DECam/calib/desgw_pilot/bias
   butler query-datasets $REPO --collections DECam/calib/desgw_pilot/bias bias

Certify bias frames
--------------------------------

Certify the biases for a given date range. Arguments: ``REPO``, ``INPUT_COLLECTION``, ``OUTPUT_COLLECTION``, ``DATASET_TYPE_NAME``: ::

   butler certify-calibrations \
   $REPO DECam/calib/desgw_pilot/bias DECam/calib/desgw_pilot bias \
   --begin-date 2023-04-01T00:00:00 --end-date 2025-11-30T23:59:59

You may check what certified date ranges have been applied to the bias data in Python by querying dataset associations in the output collection. For example, to check only detector #1: ::

   qda = butler.registry.queryDatasetAssociations
   coll = "DECam/calib/desgw_pilot"
   biases = [x for x in qda("bias", collections=coll) if x.ref.dataId["detector"] == 1]
   print(biases)

which produces a list of all biases relating to detector #1 (in the case of this example document, there should be only 1 result at present). Inspecting the properties of this object gives the timespan, e.g.: ::

   print(f"{biases[0].timespan.begin.value = }")
   print(f"{biases[0].timespan.end.value = }")

Generate crosstalk sources
--------------------------------

The next step is to generate ``crosstalk`` sources using step 0 of the Data Release Production (DRP) pipeline (DRP.yaml). Crosstalk sources need to be generated for any raw we want to run actual ISR on (i.e., raw flats and raw science frames). Step 0 of DRP.yaml runs only the doOverscan aspect of the ISR (instrument signature removal) task. Here, I used the Merian step zero pipeline. It can be visualized using: ::

   pipetask build \
   -p $DRP_PIPE_DIR/pipelines/DECam/DRP-Merian.yaml#step0 \
   --show pipeline

Run step0 for raw flats: ::

   LOGFILE=$LOGDIR/step0_flat_0.log; \
   date | tee $LOGFILE; \
   pipetask --long-log run --register-dataset-types -j 12 \
   -b $REPO --instrument lsst.obs.decam.DarkEnergyCamera \
   -i DECam/raw/all,DECam/calib/desgw_pilot,DECam/calib/unbounded \
   -o DECam/calib/desgw_pilot/crosstalk \
   -p /home/smacbr/Butler-imports/s3it_setup/desgw/cp_crosstalk_i.yaml \
   -d "instrument='DECam' AND exposure IN $FLATEXPS" \
   2>&1 | tee -a $LOGFILE; \
   date | tee -a $LOGFILE

> Note that if the above, or any other job fails, you can add `` --extend-run --skip-existing --clobber-outputs `` to the ``pipetask run`` command to continue the run without starting over.

Extend the crosstalk RUN collection to also include science exposures: ::

   LOGFILE=$LOGDIR/step0_science.log; \
   date | tee -a $LOGFILE; \
   pipetask --long-log run --register-dataset-types -j 12 \
   --extend-run --skip-existing \
   -b $REPO --instrument lsst.obs.decam.DarkEnergyCamera \
   -i DECam/raw/all,DECam/calib/desgw_pilot,DECam/calib/unbounded \
   -o DECam/calib/desgw_pilot/crosstalk \
   -p /home/smacbr/Butler-imports/s3it_setup/desgw/cp_crosstalk_i.yaml \
   -d "instrument='DECam' AND exposure IN $SCIEXPS" \
   2>&1 | tee -a $LOGFILE; \
   date | tee -a $LOGFILE

The overscanRaw dataset types should now be available in the output repository. Check the collections and datasets: ::

   butler query-collections $REPO
   butler query-datasets $REPO overscanRaw

Build flat frames
--------------------------------

This step constructs the master flat frames (which requires using the biases). The cpFlat pipeline can be visualized using: ::

   pipetask build \
   -p $CP_PIPE_DIR/pipelines/DECam/cpFlat.yaml \
   --show pipeline

Build master flats: ::

   LOGFILE=$LOGDIR/cpFlat.log; \
   date | tee $LOGFILE; \
   pipetask --long-log run --register-dataset-types -j 12 \
   -b $REPO --instrument lsst.obs.decam.DarkEnergyCamera \
   -i DECam/raw/all,DECam/calib/desgw_pilot,DECam/calib/desgw_pilot/crosstalk,DECam/calib/curated/19700101T000000Z,DECam/calib/unbounded \
   -o DECam/calib/desgw_pilot/flat \
   -p $CP_PIPE_DIR/pipelines/DECam/cpFlat.yaml \
   -d "instrument='DECam' AND exposure IN $FLATEXPS" \
   2>&1 | tee -a $LOGFILE; \
   date | tee -a $LOGFILE

Check what types of data now exist in the output collection: ::

   butler query-collections $REPO
   butler query-dataset-types $REPO
   butler query-datasets $REPO --collections DECam/calib/desgw_pilot/flat
   butler query-datasets $REPO --collections DECam/calib/desgw_pilot/flat flat

Certify flat frames
--------------------------------

Certify the flats for a given date range. Arguments: ``REPO``, ``INPUT_COLLECTION``, ``OUTPUT_COLLECTION``, ``DATASET_TYPE_NAME``: ::

   butler certify-calibrations \
   $REPO DECam/calib/desgw_pilot/flat DECam/calib/desgw_pilot flat \
   --begin-date 2025-08-25T00:00:00 --end-date 2025-09-30T00:00:00

You may check what certified date ranges have been applied to the flat data in Python by querying dataset associations in the output collection. For example, to check only detector #1: ::

   qda = butler.registry.queryDatasetAssociations
   coll = "DECam/calib/desgw_pilot
   flats = [x for x in qda("flat", collections=coll) if x.ref.dataId["detector"] == 1]
   print(flats)

which produces a list of all flats relating to detector #1 (in the case of this example document, there should be only 1 result at present). Inspecting the properties of this object gives the timespan, e.g.: ::

   print(f"{flats[0].timespan.begin.value = }")
   print(f"{flats[0].timespan.end.value = }")

Build fringes
--------------------------------
**TODO: Write this section**

Certify fringes
--------------------------------
**TODO: Write this section**

Set up a default collection
=================

Data in the Science Pipelines are arranged into collections; groupings of data. Here we establish a default collection which contains the commonly required raw `RUN` collections. Whilst this step is not strictly necessary, this will allow us to specify only a single `INPUT` collection for future raw data processing: ::

   INPUT=DECam/defaults/desgw_pilot

If this step is not performed, future data processing will need to specify all required input collections explicitly: ::

   -i long,comma,separated,list,of,child,collections

If this step is followed then future data processing from raw data should only need to specify the default collection: ::

   -i $INPUT

| Note: it is not currently possible to query a `CHAINED` collection containing a `CALIBRATION` child collection. By constructing a dedicated `CHAINED` collection containing only the `RUN` runs of `interest, this will allow users to query the `CHAINED` collection and avoid this error.

A `CHAINED` collection can be set up either on the command line or in Python. To set up a `CHAINED` collection on the command line for all required input collections, run: ::

   CHILDREN="DECam/raw/all,\
   DECam/calib/desgw_pilot,\
   DECam/calib/desgw_pilot/crosstalk,\
   DECam/calib/curated/19700101T000000Z,\
   DECam/calib/unbounded,\
   skymaps,\
   refcats"

   butler collection-chain $REPO $INPUT $CHILDREN

| Note: the `CHILDREN` list may be amended and the above command re-run to update this parent collection, if, for example, new data has been processed and a user would like to add the updated crosstalk `RUN` collection to this parent `CHAINED` collection.

Alternatively, this may also be achieved in Python: ::

   import lsst.daf.butler as dafButler

   REPO = "/shares/soares-santos.physik.uzh/ButlerProjects/DESGW"
   default_collection = "DECam/defaults/desgw_pilot"

   # Set up a writeable butler
   butler_writeable = dafButler.Butler(REPO, writeable=True)
   registry_writeable = butler_writeable.registry

   # Register a new default CHAINED collection
   registry_writeable.registerCollection(default_collection,
                                         type = dafButler.CollectionType.CHAINED)

   # Add required CHILD collections into the CHAINED collection
   registry_writeable.setCollectionChain(default_collection,
                                         ["DECam/raw/all",
                                          "DECam/calib/desgw_pilot",
                                          "DECam/calib/desgw_pilot/crosstalk"
                                          "DECam/calib/curated/19700101T000000Z",
                                          "DECam/calib/unbounded",
                                          "skymaps",
                                          "refcats"])

| Note: as above, if reprocessing data in future runs, you can amend the list above to add your own collections, and then re-run setCollectionChain to update default_collection. This allows for the default collection to stay relevant in linking to all necessary datasets as new data becomes available.

Data release production
=================

In this section we will proceed through all the relevant data processing steps to take raw DECam science data through to coadd outputs. These processed data will output into the `OUTPUT` `CHAINED` collection: ::

   OUTPUT=DECam/runs/desgw_pilot/v29_2_1

Here, the `v29_2_1` is a reference to the 29.2.1 major release of the LSST Science Pipelines used to reduce these data.

Processing consists of four main steps:

* Step 1: single frame processing.
   * instrumental signature removal, initial bg subtraction / calibration / PSF estimation.
* Step 2: post single frame processing.
   * step 2a - initial visit aggregation.
   * step 2b - tract-level characterization.
   * step 2c - global collection summaries.
   * step 2d - final source table generation.
* Step 3: coadd level processing
   * Warping visit-level images onto the coadd plane, constructing a coadd, running detection & deblending algorithms.
* Step 4: difference image processing
   * Subtract processed single frames and template frames to identify and analyze interesting difference image sources.

If outputting to an already existing collection in the commands below, the following arguments should be appended to the pipetask run commands below: ::

   --extend-run --skip-existing --clobber-outputs

Step 1: Single visit processing
--------------------------------

Processed visit images (PVIs) and preliminary source tables are produced in step 1.

The Stage 1 DESGW .yaml:
::
   description: |
     The DRP pipeline specialized for the DECam instrument, developed against the
     DESGW dataset.

     Prior to running subsets or tasks in this pipeline, the DECam prerequisite
     task isrForCrosstalkSources must be run. More information on that task can be
     found in the isrForCrosstalkSources.yaml pipeline file.
   instrument: lsst.obs.decam.DarkEnergyCamera
   parameters:
     add_point_source: false
     fix_centroid: false
     use_shapelet_psf: false
   tasks:
     isr:
       class: lsst.ip.isr.IsrTask
       config:
       - doAmpOffset: true
         ampOffset.doApplyAmpOffset: false
         connections.crosstalkSources: overscanRaw
         doCrosstalk: true
     calibrateImage:
       class: lsst.pipe.tasks.calibrateImage.CalibrateImageTask
       config:
       - file:
         - $DRP_PIPE_DIR/config/calibrateImage.py
         connections.initial_stars_schema: src_schema
         connections.stars_footprints: src
         connections.stars: source
         connections.exposure: calexp
         connections.background: calexpBackground
       - connections.stars: preSource
         connections.exposure: calexp
         connections.background: calexpBackground
         photometry.match.referenceSelection.magLimit.fluxField: i_flux
         photometry.match.referenceSelection.magLimit.maximum: 21.0
     transformPreSourceTable:
       class: lsst.pipe.tasks.postprocess.TransformSourceTableTask
       config:
       - functorFile: $PIPE_TASKS_DIR/schemas/PreSource.yaml
         connections.inputCatalog: preSource
         connections.outputCatalog: preSourceTable
   contracts:
   - contract: isr.doFlat == True if calibrateImage.do_illumination_correction == True
       else True
   subsets:
     processCcd:
       subset:
       - calibrateImage
       - isr
       description: 'Set of tasks to run when doing single frame processing, without
         any conversions to Parquet/DataFrames or visit-level summaries.

         '
     step1:
       subset:
       - calibrateImage
       - isr
       - transformPreSourceTable
       description: |
         Per-detector tasks that can be run together to start the DRP pipeline.

         These should never be run with 'tract' or 'patch' as part of the data ID
         expression if any later steps will also be run, because downstream steps
         require full visits and 'tract' and 'patch' constraints will always
         select partial visits that overlap that region.

Then run the bash script to submit the job to the grid. ::

   INPUT="DECam/defaults/desgw_pilot"
   OUTPUT="DECam/runs/desgw_pilot/v29_2_1"
   PIPEYAML="/shares/soares-santos.physik.uzh/repos/Butler-imports/s3it_setup/desgw/stage1DESGW.yaml"

   DATAQUERY="exposure.day_obs > 20250825
   AND exposure.day_obs < 20250930
   AND exposure.observation_type='science'
   AND detector NOT IN (31,61)"

   LOGFILE=$LOGDIR/desgw_pilot_step1.log; \
   date | tee $LOGFILE; \
   pipetask --long-log run --register-dataset-types -j 30 \
   -b $REPO --instrument lsst.obs.decam.DarkEnergyCamera \
   -i $INPUT \
   -o $OUTPUT \
   -p $PIPEYAML  \
   -d "instrument='DECam' AND $DATAQUERY" \
   2>&1 | tee -a $LOGFILE; \
   date | tee -a $LOGFILE

Step 2: Photometric and astrometric calibration
--------------------------------

Step 3: Difference image processing
--------------------------------

Step 4: Image Coaddition
--------------------------------

=================
Appendix
=================

Useful commands
=================

This section provides some useful command-line commands which may be used to interact with the data.

query-collections
--------------------------------

Query collections in the repo: ::

   butler query-collections $REPO "*u/seanmacb*"

The final search pattern may use standard glob syntax (e.g., note the asterisks above).

query-datasets
--------------------------------

Query the datasets which live in a given collection: ::

   butler query-datasets $REPO \
   --collections u/seanmacb/testrun/01 \
   --where "instrument='DECam' AND skymap='hsc_rings_v1' AND tract=9813" \
   calexp

If the final dataset type (calexp in the example above) is not given, all dataset types found will be printed to the command line.

collection-chain
--------------------------------

Redefine a `CHAINED` collection to only contain certain child `RUN` collections: ::

   butler collection-chain $REPO PARENT "CHILD1,CHILD2"

This command is useful to use prior to attempting to delete a CHAINED collection, ensuring that no attempt is made to delete input raw collections.

remove-runs
--------------------------------

Remove one or more `RUN` collections: ::

   butler remove-runs $REPO COLLECTION

remove-collections
--------------------------------

Remove one or more non-RUN collections: ::

   butler remove-collections $REPO COLLECTION

What tracts cover my data?
==========================

The visitSummary tables produced in step 2a contain important information on single frame processed visits. This information may be used to find out which tracts overlap with your data.

To generate a list of tract overlaps for a single visit, in Python: ::

   from collections import defaultdict
   import lsst.daf.butler as dafButler

   butler = dafButler.Butler('/project/lskelvin/repo')

   grouped_by_tract = defaultdict(set)
   for data_id in butler.registry.queryDataIds(
       ["tract", "visit", "detector"],
       datasets="visitSummary",
       collections="DECam/runs/merian9813/w_2022_26",
       instrument="DECam",
       visit=971666,
   ):
       grouped_by_tract[data_id["tract"]].add(data_id)

   print({k: len(v) for k, v in grouped_by_tract.items()})

To get total tract coverage for all visits in a given collection, remove the visit= argument above.

Transferring datasets from one machine to another
==========================

To transfer datasets from one machine to another (e.g., from science cluster to somewhere else), first, on the source machine in Python: ::

   outdir = "/path/to/output/on/destination"

   datasetType = ["objectTable_tract", "deepCoadd", "deepCoadd_calexp"] # List all your dataset objects you want to transfer
   collection = "HSC/runs/RC2/w_2022_04/DM-33402" # List the collection where you can find these objects
   dataId = dict(skymap="hsc_rings_v1", tract=9813) # Define your data ID

   with butler.export(directory=outdir, format="yaml", transfer="copy") as export:
       items = []
       found = set(butler.registry.queryDatasets(datasetType,
                                                 collections=collection,
                                                 dataId=dataId))
       items.extend(found)
       export.saveDatasets(items)

Next, in the output directory on the source machine: ::

   tar -czvf data_transfer.tar.gz *

Transfer the file (here named data_transfer.tar.gz) from the source machine to the destination machine. Extract the tarball on the source machine: ::

   tar -xzvf data_transfer.tar.gz

Next, on the source machine: ::

   LOGFILE=$LOGDIR/data_import.log; \
   butler import $REPO \
   /path/to/data_transfer_directory \
   --transfer copy \
   --skip-dimensions skymap,tract,patch \
   2>&1 | tee -a $LOGFILE; \
   date | tee -a $LOGFILE

Finally, set up a similarly named parent collection, e.g.: ::

   PARENT=HSC/runs/RC2/w_2022_04/DM-33402
   CHILD=HSC/runs/RC2/w_2022_04/DM-33402/20220128T212035Z

   butler collection-chain $REPO $PARENT $CHILD

Decertifying a calibration dataset
=====================

To decertify a calibration collection (because, e.g., a new calibration collection has been generated and intended to replace the existing certified data on-disk): ::

   writeable_butler = dafButler.Butler(
       '/projects/MERIAN/repo', writeable=True
   )

   writeable_butler.registry.decertify(
       collection='DECam/calib/merian',
       datasetType='bias',
       timespan=lsst.daf.butler.Timespan(None, None),
   )

   writeable_butler.registry.decertify(
       collection='DECam/calib/merian',
       datasetType='flat',
       timespan=lsst.daf.butler.Timespan(None, None),
   )
