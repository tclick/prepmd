"""PDB input validation rules."""

from prepmd.config.models import ProjectConfig
from prepmd.config.validators.base import BaseValidator
from prepmd.structure.pdb_handler import validate_pdb_id


class PDBInputValidator(BaseValidator):
    """Validate mutually exclusive PDB input modes."""

    def validate(self, config: ProjectConfig) -> None:
        protein = config.protein
        if protein.pdb_id is not None:
            validate_pdb_id(protein.pdb_id)
