"""
Workflow visualization utilities for waywo.

Provides functions to generate static HTML visualizations of workflow
structures and execution traces using llama-index-utils-workflow.
"""

import os
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional

from llama_index.core.workflow import Workflow
from llama_index.utils.workflow import (
    draw_all_possible_flows,
    draw_most_recent_execution,
)

from src.settings import DATA_DIR

# Default visualization directory
DEFAULT_VIZ_DIR = DATA_DIR + "/visualizations"


@contextmanager
def working_directory(path: Path):
    """Context manager to temporarily change working directory."""
    prev_cwd = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(prev_cwd)


def ensure_viz_dir(viz_dir: str = DEFAULT_VIZ_DIR) -> Path:
    """
    Ensure the visualization directory exists.

    Args:
        viz_dir: Path to the visualization directory

    Returns:
        Path object for the visualization directory
    """
    path = Path(viz_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def generate_workflow_structure(
    workflow: Workflow,
    workflow_name: str,
    viz_dir: str = DEFAULT_VIZ_DIR,
) -> str:
    """
    Generate a static HTML visualization of the workflow structure.

    Uses draw_all_possible_flows() to create a diagram showing all
    possible paths through the workflow.

    Args:
        workflow: The LlamaIndex Workflow instance
        workflow_name: Name identifier for the workflow
        viz_dir: Directory to save the visualization

    Returns:
        Path to the generated HTML file
    """
    viz_path = ensure_viz_dir(viz_dir)
    filename = f"{workflow_name}_structure.html"
    filepath = viz_path / filename

    # Change to viz directory to avoid permission issues with intermediate files
    with working_directory(viz_path):
        draw_all_possible_flows(workflow, filename=filename)

    return str(filepath)


def save_execution_trace(
    handler,
    workflow_name: str,
    execution_id: Optional[str] = None,
    viz_dir: str = DEFAULT_VIZ_DIR,
) -> str:
    """
    Save an execution trace HTML visualization.

    Uses draw_most_recent_execution() to create a diagram showing
    the actual execution path taken during a workflow run.

    Args:
        handler: The workflow handler from running the workflow
        workflow_name: Name identifier for the workflow
        execution_id: Optional unique ID for this execution
        viz_dir: Directory to save the visualization

    Returns:
        Path to the generated HTML file
    """
    viz_path = ensure_viz_dir(viz_dir)

    if execution_id is None:
        execution_id = datetime.now().strftime("%Y%m%d_%H%M%S")

    filename = f"{workflow_name}_execution_{execution_id}.html"
    filepath = viz_path / filename

    # Change to viz directory to avoid permission issues with intermediate files
    with working_directory(viz_path):
        draw_most_recent_execution(handler, filename=filename)

    return str(filepath)


def list_visualizations(viz_dir: str = DEFAULT_VIZ_DIR) -> dict:
    """
    List all saved visualization files.

    Returns:
        Dictionary with structure and execution trace lists
    """
    viz_path = Path(viz_dir)

    if not viz_path.exists():
        return {
            "structures": [],
            "executions": [],
            "directory": str(viz_path),
        }

    structures = []
    executions = []

    for filepath in sorted(viz_path.glob("*.html")):
        file_info = {
            "filename": filepath.name,
            "path": str(filepath),
            "size_bytes": filepath.stat().st_size,
            "modified": datetime.fromtimestamp(filepath.stat().st_mtime).isoformat(),
        }

        if "_structure" in filepath.name:
            # Extract workflow name from filename
            file_info["workflow"] = filepath.name.replace("_structure.html", "")
            structures.append(file_info)
        elif "_execution_" in filepath.name:
            # Extract workflow name and execution ID
            parts = filepath.stem.split("_execution_")
            file_info["workflow"] = parts[0]
            file_info["execution_id"] = parts[1] if len(parts) > 1 else "unknown"
            executions.append(file_info)

    return {
        "structures": structures,
        "executions": executions,
        "directory": str(viz_path),
    }


def get_visualization_path(
    filename: str,
    viz_dir: str = DEFAULT_VIZ_DIR,
) -> Optional[str]:
    """
    Get the full path to a visualization file.

    Args:
        filename: Name of the visualization file
        viz_dir: Directory containing visualizations

    Returns:
        Full path to the file, or None if not found
    """
    viz_path = Path(viz_dir)
    filepath = viz_path / filename

    if filepath.exists():
        return str(filepath)

    return None
