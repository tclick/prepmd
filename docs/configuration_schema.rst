Configuration schema
====================

`prepmd` accepts YAML (``.yaml``/``.yml``) and TOML (``.toml``) files with the same schema.

Top-level fields
----------------

* ``project_name`` (string, required)
* ``output_dir`` (string, default ``.``)
* ``protein`` (table/object)
* ``simulation`` (table/object)
* ``engine`` (table/object)

Protein
-------

* ``variants`` (list of strings, default ``["apo", "holo"]``)
* ``pdb_files`` (mapping from variant name to optional PDB path)

Simulation
----------

* ``replicas`` (integer >= 1, default ``1``)
* ``temperature`` (float > 0, default ``300.0``)
* ``ensemble`` (string, default ``NVT``)
* ``production_runs`` (integer >= 1, default ``3``)
* ``production_run_length_ns`` (integer >= 1, default ``100``)

Engine
------

* ``name`` (string, default ``amber``)
* ``force_field`` (string, default ``ff19sb``)
* ``water_model`` (string, default ``OPC3``)
* ``options`` (mapping, default empty)

See ``examples/config.yaml`` and ``examples/config.toml`` for complete examples.
