"""Shared verification output checks."""

from pathlib import Path


def case_outputs_complete(case_dir, sample_counts):
    """Return whether every expected sample output exists for a case."""
    case_dir = Path(case_dir)
    return all(
        (case_dir / f"output_{int(count)}.h5").is_file() for count in sample_counts
    )
