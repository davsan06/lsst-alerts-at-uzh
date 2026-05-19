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

    OBSDECAM=/home/lkelvin/repos/obs_decam
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
    #   obs_decam             LOCAL:/home/lkelvin/repos/obs_decam

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

A new butler will be created in the directory /projects/MERIAN/repo. Here we set aliases for the output repository directory: ::

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

Create a PostgreSQL database.
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

This is another option, but requires the service running on the machine in advance.

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

Ingesting calib data
--------------------------------

Ingesting bias data
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Ingesting dark data
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Defining visits
--------------------------------

Set up a default collection
=================

Data release production
=================

Step 1: Single visit processing
--------------------------------

Step 2: Photometric and astrometric calibration
--------------------------------

Step 3: Difference image processing
--------------------------------

Step 4: Image Coaddition
--------------------------------

