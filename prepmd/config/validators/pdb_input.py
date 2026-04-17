"""PDB input validation rules."""

from prepmd.config.models import ProjectConfig
from prepmd.config.validators.base import BaseValidator
from prepmd.exceptions import PDBMutualExclusivityError
from prepmd.structure.pdb_handler import validate_pdb_id


class PDBInputValidator(BaseValidator):
    """Validate mutually exclusive PDB input modes."""

    def validate(self, config: ProjectConfig) -> None:
        protein = config.protein
        has_variant_local = any(path for path in protein.pdb_files.values() if path)
        has_local = protein.pdb_file is not None or has_variant_local
        has_remote = protein.pdb_id is not None

        if has_local and has_remote:
            raise PDBMutualExclusivityError("Specify either a local PDB file or a PDB ID, not both.")
        if not has_local and not has_remote:
            raise PDBMutualExclusivityError("Specify exactly one PDB input method: local file or PDB ID.")
        if protein.pdb_id is not None:
            protein.pdb_id = validate_pdb_id(protein.pdb_id)
