"""Engine-specific post-processing and analysis script templates."""

from __future__ import annotations

from textwrap import dedent


def render_replica_workflow_scripts(engine_name: str) -> dict[str, str]:
    """Render per-replica post-processing and analysis scripts for *engine_name*."""

    scripts_by_engine: dict[str, dict[str, str]] = {
        "amber": _amber_scripts(),
        "gromacs": _gromacs_scripts(),
        "charmm": _charmm_family_scripts(),
        "namd": _charmm_family_scripts(),
        "openmm": _openmm_scripts(),
    }
    scripts = scripts_by_engine.get(engine_name)
    if scripts is None:
        raise ValueError(f"Unsupported engine for workflow scripts: {engine_name}")
    return scripts


def _normalize_script(content: str) -> str:
    return dedent(content).strip() + "\n"


def _amber_scripts() -> dict[str, str]:
    return {
        "05_post_processing/01_strip_waters.cpptraj": _normalize_script(
            """
            parm ../system.prmtop
            trajin ../04_production/run_001/production.nc
            trajin ../04_production/run_002/production.nc
            trajin ../04_production/run_003/production.nc
            strip :WAT,Na+,Cl-
            trajout stripped_protein.nc netcdf
            run
            """
        ),
        "05_post_processing/02_center.cpptraj": _normalize_script(
            """
            parm ../system.prmtop
            trajin stripped_protein.nc
            autoimage
            center :* mass origin
            image origin center familiar
            trajout centered_protein.nc netcdf
            run
            """
        ),
        "05_post_processing/03_merge_production.cpptraj": _normalize_script(
            """
            parm ../system.prmtop
            trajin ../04_production/run_001/production.nc
            trajin ../04_production/run_002/production.nc
            trajin ../04_production/run_003/production.nc
            trajout merged_protein.nc netcdf
            run
            """
        ),
        "05_post_processing/04_visualize_merged.vmd.tcl": _normalize_script(
            """
            mol new ../system.prmtop type parm7 waitfor all
            mol addfile merged_protein.nc type netcdf waitfor all
            display projection Orthographic
            color Display Background white
            mol modstyle 0 0 NewCartoon
            """
        ),
        "06_analysis/01_rmsd.cpptraj": _normalize_script(
            """
            parm ../system.prmtop
            trajin ../05_post_processing/centered_protein.nc
            rms first @CA out rmsd_ca.dat
            run
            """
        ),
        "06_analysis/02_rmsf.cpptraj": _normalize_script(
            """
            parm ../system.prmtop
            trajin ../05_post_processing/centered_protein.nc
            atomicfluct @CA byres out rmsf_ca_byres.dat
            run
            """
        ),
        "06_analysis/03_radius_of_gyration.cpptraj": _normalize_script(
            """
            parm ../system.prmtop
            trajin ../05_post_processing/centered_protein.nc
            radgyr :* out rgyr.dat
            run
            """
        ),
        "06_analysis/04_hbond.cpptraj": _normalize_script(
            """
            parm ../system.prmtop
            trajin ../05_post_processing/centered_protein.nc
            hbond hb out hbond_counts.dat avgout hbond_avg.dat
            run
            """
        ),
        "06_analysis/05_sasa.cpptraj": _normalize_script(
            """
            parm ../system.prmtop
            trajin ../05_post_processing/centered_protein.nc
            surf :* out sasa_protein.dat
            run
            """
        ),
    }


def _gromacs_scripts() -> dict[str, str]:
    return {
        "05_post_processing/01_strip_waters.sh": _normalize_script(
            """
            #!/usr/bin/env bash
            set -euo pipefail
            echo Protein | gmx trjconv -f merged.xtc -s ../topol.tpr -n ../index.ndx -o protein_only.xtc
            """
        ),
        "05_post_processing/02_center.sh": _normalize_script(
            """
            #!/usr/bin/env bash
            set -euo pipefail
            printf '%s\\n%s\\n' Protein Protein | gmx trjconv \
              -f protein_only.xtc \
              -s ../topol.tpr \
              -n ../index.ndx \
              -center -pbc mol -ur compact \
              -o centered_protein.xtc
            """
        ),
        "05_post_processing/03_merge_production.sh": _normalize_script(
            """
            #!/usr/bin/env bash
            set -euo pipefail
            gmx trjcat -f \
              ../04_production/run_001/md.xtc \
              ../04_production/run_002/md.xtc \
              ../04_production/run_003/md.xtc \
              -o merged.xtc -settime
            """
        ),
        "05_post_processing/04_visualize_merged.vmd.tcl": _normalize_script(
            """
            mol new ../topol.tpr type tpr waitfor all
            mol addfile centered_protein.xtc type xtc waitfor all
            mol modstyle 0 0 NewCartoon
            """
        ),
        "06_analysis/01_rmsd.sh": _normalize_script(
            """
            #!/usr/bin/env bash
            set -euo pipefail
            printf '%s\\n%s\\n' Backbone Backbone | gmx rms \
              -s ../topol.tpr \
              -f ../05_post_processing/centered_protein.xtc \
              -o rmsd_backbone.xvg
            """
        ),
        "06_analysis/02_rmsf.sh": _normalize_script(
            """
            #!/usr/bin/env bash
            set -euo pipefail
            echo C-alpha | gmx rmsf -s ../topol.tpr -f ../05_post_processing/centered_protein.xtc -res -o rmsf_ca.xvg
            """
        ),
        "06_analysis/03_radius_of_gyration.sh": _normalize_script(
            """
            #!/usr/bin/env bash
            set -euo pipefail
            echo Protein | gmx gyrate -s ../topol.tpr -f ../05_post_processing/centered_protein.xtc -o rgyr.xvg
            """
        ),
        "06_analysis/04_hbond.sh": _normalize_script(
            """
            #!/usr/bin/env bash
            set -euo pipefail
            printf '%s\\n%s\\n' Protein Protein | gmx hbond \
              -s ../topol.tpr \
              -f ../05_post_processing/centered_protein.xtc \
              -num hbond_count.xvg
            """
        ),
        "06_analysis/05_sasa.sh": _normalize_script(
            """
            #!/usr/bin/env bash
            set -euo pipefail
            echo Protein | gmx sasa -s ../topol.tpr -f ../05_post_processing/centered_protein.xtc -o sasa_total.xvg
            """
        ),
    }


def _charmm_family_scripts() -> dict[str, str]:
    return {
        "05_post_processing/01_strip_waters.vmd.tcl": _normalize_script(
            """
            mol new ../system.psf type psf waitfor all
            mol addfile ../04_production/run_001/production.dcd type dcd waitfor all
            set protein [atomselect top "protein"]
            animate write dcd protein_only.dcd sel $protein waitfor all
            """
        ),
        "05_post_processing/02_center.vmd.tcl": _normalize_script(
            """
            package require pbctools
            mol new ../system.psf type psf waitfor all
            mol addfile protein_only.dcd type dcd waitfor all
            pbc wrap -all -compound residue -center com -centersel "protein"
            animate write dcd centered_protein.dcd waitfor all
            """
        ),
        "05_post_processing/03_merge_production.sh": _normalize_script(
            """
            #!/usr/bin/env bash
            set -euo pipefail
            catdcd -o merged_protein.dcd \
              ../04_production/run_001/production.dcd \
              ../04_production/run_002/production.dcd \
              ../04_production/run_003/production.dcd
            """
        ),
        "05_post_processing/04_visualize_merged.vmd.tcl": _normalize_script(
            """
            mol new ../system.psf type psf waitfor all
            mol addfile centered_protein.dcd type dcd waitfor all
            mol modstyle 0 0 NewCartoon
            """
        ),
        "06_analysis/01_rmsd.vmd.tcl": _normalize_script(
            """
            mol new ../system.psf type psf waitfor all
            mol addfile ../05_post_processing/centered_protein.dcd type dcd waitfor all
            set ref [atomselect top "protein and name CA" frame 0]
            set sel [atomselect top "protein and name CA"]
            set out [open rmsd_ca.dat w]
            set nf [molinfo top get numframes]
            for {set i 0} {$i < $nf} {incr i} {
                $sel frame $i
                puts $out "$i [measure rmsd $sel $ref]"
            }
            close $out
            """
        ),
        "06_analysis/02_rmsf.vmd.tcl": _normalize_script(
            """
            mol new ../system.psf type psf waitfor all
            mol addfile ../05_post_processing/centered_protein.dcd type dcd waitfor all
            set ca [atomselect top "protein and name CA"]
            set rmsf [measure rmsf $ca]
            set out [open rmsf_ca.dat w]
            foreach value $rmsf {puts $out $value}
            close $out
            """
        ),
        "06_analysis/03_radius_of_gyration.vmd.tcl": _normalize_script(
            """
            mol new ../system.psf type psf waitfor all
            mol addfile ../05_post_processing/centered_protein.dcd type dcd waitfor all
            set out [open rgyr.dat w]
            set sel [atomselect top "protein"]
            set nf [molinfo top get numframes]
            for {set i 0} {$i < $nf} {incr i} {
                $sel frame $i
                puts $out "$i [measure rgyr $sel]"
            }
            close $out
            """
        ),
        "06_analysis/04_hbond.vmd.tcl": _normalize_script(
            """
            mol new ../system.psf type psf waitfor all
            mol addfile ../05_post_processing/centered_protein.dcd type dcd waitfor all
            package require hbonds
            hbonds -sel1 "protein" -sel2 "protein" -dist 3.5 -ang 30 -writefile yes -outfile hbond_counts.dat
            """
        ),
        "06_analysis/05_sasa.vmd.tcl": _normalize_script(
            """
            mol new ../system.psf type psf waitfor all
            mol addfile ../05_post_processing/centered_protein.dcd type dcd waitfor all
            set out [open sasa_total.dat w]
            set sel [atomselect top "protein"]
            set nf [molinfo top get numframes]
            for {set i 0} {$i < $nf} {incr i} {
                $sel frame $i
                puts $out "$i [measure sasa 1.4 $sel]"
            }
            close $out
            """
        ),
    }


def _openmm_scripts() -> dict[str, str]:
    return {
        "05_post_processing/01_strip_waters.py": _normalize_script(
            """
            import mdtraj as md

            traj = md.load("merged.dcd", top="../system.pdb")
            protein = traj.atom_slice(traj.topology.select("protein"))
            protein.save_dcd("protein_only.dcd")
            """
        ),
        "05_post_processing/02_center.py": _normalize_script(
            """
            import mdtraj as md

            traj = md.load("protein_only.dcd", top="../system.pdb")
            traj.center_coordinates()
            traj.image_molecules(inplace=True)
            traj.save_dcd("centered_protein.dcd")
            """
        ),
        "05_post_processing/03_merge_production.py": _normalize_script(
            """
            import mdtraj as md

            parts = [
                md.load("../04_production/run_001/production.dcd", top="../system.pdb"),
                md.load("../04_production/run_002/production.dcd", top="../system.pdb"),
                md.load("../04_production/run_003/production.dcd", top="../system.pdb"),
            ]
            merged = md.join(parts)
            merged.save_dcd("merged.dcd")
            """
        ),
        "05_post_processing/04_visualize_merged.vmd.tcl": _normalize_script(
            """
            mol new ../system.pdb type pdb waitfor all
            mol addfile centered_protein.dcd type dcd waitfor all
            mol modstyle 0 0 NewCartoon
            """
        ),
        "06_analysis/01_rmsd.py": _normalize_script(
            """
            import mdtraj as md
            import numpy as np

            traj = md.load("../05_post_processing/centered_protein.dcd", top="../system.pdb")
            ca = traj.topology.select("protein and name CA")
            rmsd = md.rmsd(traj, traj, atom_indices=ca, frame=0)
            np.savetxt("rmsd_ca.dat", rmsd)
            """
        ),
        "06_analysis/02_rmsf.py": _normalize_script(
            """
            import mdtraj as md
            import numpy as np

            traj = md.load("../05_post_processing/centered_protein.dcd", top="../system.pdb")
            ca = traj.topology.select("protein and name CA")
            rmsf = md.rmsf(traj, traj, frame=0, atom_indices=ca)
            np.savetxt("rmsf_ca.dat", rmsf)
            """
        ),
        "06_analysis/03_radius_of_gyration.py": _normalize_script(
            """
            import mdtraj as md
            import numpy as np

            traj = md.load("../05_post_processing/centered_protein.dcd", top="../system.pdb")
            rg = md.compute_rg(traj)
            np.savetxt("rgyr.dat", rg)
            """
        ),
        "06_analysis/04_hbond.py": _normalize_script(
            """
            import mdtraj as md
            import numpy as np

            traj = md.load("../05_post_processing/centered_protein.dcd", top="../system.pdb")
            hbonds = md.baker_hubbard(traj, periodic=True)
            np.savetxt("hbond_triplets.dat", hbonds, fmt="%d")
            """
        ),
        "06_analysis/05_sasa.py": _normalize_script(
            """
            import mdtraj as md
            import numpy as np

            traj = md.load("../05_post_processing/centered_protein.dcd", top="../system.pdb")
            sasa = md.shrake_rupley(traj, mode="residue")
            np.savetxt("sasa_residue.dat", sasa)
            """
        ),
    }
