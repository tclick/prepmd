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
* ``water_box`` (table/object)

Protein
-------

* ``variants`` (list of strings, default ``["apo", "holo"]``)
* ``pdb_files`` (mapping from variant name to optional PDB path)
* ``pdb_file`` (single local input PDB path)
* ``pdb_id`` (RCSB PDB identifier)
* ``pdb_cache_dir`` (optional cache directory for downloaded PDB files)

Model-level validation enforces exactly one PDB source: local file(s) or remote ``pdb_id``.

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

Water box
---------

* ``shape`` (string, one of ``cubic``, ``truncated_octahedron``, ``orthorhombic``; default ``cubic``)
* ``side_length`` (float > 0, cubic only)
* ``edge_length`` (float > 0, truncated octahedron only)
* ``dimensions`` (3 floats > 0, orthorhombic only)
* ``auto_box_padding`` (float > 0, default ``10.0``; fallback when shape dimensions are omitted)

See ``examples/config.yaml`` and ``examples/config.toml`` for complete examples.
