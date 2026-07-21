PostgreSQL Setup on the UZH Science Cloud
=========================================

The baseline PostgreSQL setup on the Science Cloud consists of the following:

- One Debian 13 instance (*lsst-butler-postgres*) running the PostgreSQL database
    + This instance does not have a persistent volume.
    + If deleted, needs to be setup again (see below).
- One 200GB persistent volume (*butler-pgdata*) for storing the PostgreSQL data.


High Level Steps to Reproduce the Current Setup
-----------------------------------------------

#. Make sure you have at least one valid SSH key pair under https://cloud.science-it.uzh.ch/project/key_pairs
#. Create a volume under https://cloud.science-it.uzh.ch/project/volumes/

   + Or re-use the existing volume with the existing data

#. Launch a new instance under https://cloud.science-it.uzh.ch/project/instances/

   #. Give it a name
   #. Select the source template (*Debian 13*)

      - Do not create a new boot volume

   #. Select the VM flavour (no. of CPUs and amount of RAM)

      - Size depends on the usage, to be determined in the future.

   #. Assign the *uzh-only* network

      - We do not need to have the outside world try to access our PostgreSQL database

   #. *No other network ports necessary.*
   #. Assign the *lsst-imgproc* security group

      - This should already have the PostgreSQL port 5432 open to everybody.

   #. Assign an SSH key-pair, otherwise you can not login to the new machine.
   #. *No configuration script necessary*
   #. *No server group necessary*
   #. *No scheduler hints necessary*
   #. *No metadata necessary*
   #. **Launch the Instance**

#. Once the instance is launched, under *Actions* select *Attach Volume* and attach the previously created volume.

At this point you can login to the running instance via SSH.

The setup and configuration of the PostgreSQL database on the new instance is done via a setup script.

- The setup scripts can be found on Github: https://github.com/seanmacb/image-processing-configs/tree/jw_lsst_pipeline_physik_cluster/utilities/postgres-setup

- The setup config files can be found on the internal WIKI: https://wiki.physik.uzh.ch/cosmo/doku.php?id=science:alerts:cloud:postgres



Setup Script Description
^^^^^^^^^^^^^^^^^^^^^^^^

This script executes the following high level actions:

#. Read the list of databases, database users and passwords from a config file.
#. Install PostgreSQL and other dependencies.

#. Make sure the data volume is correctly formatted and mounted as ``/mnt/pgdata``

   .. note:: Skipped if the volume is already existing and already ext4 formatted.

#. Configure ``/etc/fstab`` to automount the volume.
#. Move the PGDATA to the volume

   .. note:: Not done if the volume already exists.

#. Configure PostgreSQL to use ``/mnt/pgdata/postgresql/data`` as the data directory

   .. note:: Some basic error checks are done (e.g. incompatible PostgreSQL versions etc.) and alerted to the user.

#. Create the database and db users

   .. note:: If db users already exist, the passwords are **NOT** changed!

#. Configure PostgreSQL to listen to external interfaces.

The script is in general *idempotent*, thus checking for existing settings, before changing anything!


Backup Configuration
^^^^^^^^^^^^^^^^^^^^

The setup scripts also install a backup configuration, which dumps all PostgreSQL databases to disk once per day (via a cronjob).

- Copy of the database dump files off-site is handled from a secondary machine.

More details on the backup setup is given in https://wiki.physik.uzh.ch/cosmo/doku.php?id=science:alerts:cloud:postgres and https://github.com/seanmacb/image-processing-configs/tree/jw_lsst_pipeline_physik_cluster/utilities/postgres-setup



Increase / Change the VM Instance
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The current (June 2026) baseline for this VM instance is:

- 4CPU cores
- 16GB of RAM

If a larger (or smaller) instance is needed / is desired, this can be changed, by going to the *Actions* column of the instance and selecting *Resize Instance*.

- A reboot will be necessary in this case!
- It is unclear of the IP will change after a resize!

Alternatively, instance can also be completely deleted and re-created by following the steps above, but by not creating a new data volumn, but re-using the existing volume.



Relevant Science Cloud Documentation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

- Instance resizing: https://docs.s3it.uzh.ch/cloud2/user_guide/instances/#resize-instance
- Storage volumes: https://docs.s3it.uzh.ch/cloud2/user_guide/volumes/
- Science cloud pricing: https://www.zi.uzh.ch/dam/jcr:75153c5b-2d76-43e4-ae27-bc34086f07df/ScienceIT-ScienceCloud-Costs-202503.pdf



Transfer of Data from SQLite to PostgreSQL
------------------------------------------

**TODO**
