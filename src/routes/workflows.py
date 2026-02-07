from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

router = APIRouter()


class RunWithTraceRequest(BaseModel):
    """Request body for running a workflow with trace capture."""

    # Project workflow params
    comment_id: Optional[int] = None
    comment_text: Optional[str] = None
    comment_author: Optional[str] = None

    # Chatbot workflow params
    query: Optional[str] = None
    top_k: int = 5


@router.get("/api/workflow-visualization/workflows", tags=["workflow"])
async def list_available_workflows():
    """
    List available workflows that can be visualized.
    """
    from src.workflow_server import WORKFLOW_METADATA

    return {
        "workflows": list(WORKFLOW_METADATA.values()),
    }


@router.get("/api/workflow-visualization/structure/{name}", tags=["workflow"])
async def get_workflow_structure(name: str):
    """
    Generate and download a static HTML visualization of workflow structure.

    Shows all possible paths through the workflow.
    """
    from fastapi.responses import FileResponse

    from src.visualization import generate_workflow_structure
    from src.workflow_server import WORKFLOWS

    if name not in WORKFLOWS:
        raise HTTPException(
            status_code=404,
            detail=f"Workflow '{name}' not found. Available: {list(WORKFLOWS.keys())}",
        )

    try:
        filepath = generate_workflow_structure(WORKFLOWS[name], name)
        return FileResponse(
            filepath,
            media_type="text/html",
            filename=f"{name}_structure.html",
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate workflow structure: {str(e)}",
        )


@router.get("/api/workflow-visualization/executions", tags=["workflow"])
async def list_execution_traces():
    """
    List all saved execution trace visualizations.
    """
    from src.visualization import list_visualizations

    return list_visualizations()


@router.get("/api/workflow-visualization/executions/{filename}", tags=["workflow"])
async def get_execution_trace(filename: str):
    """
    Download a saved execution trace HTML file.
    """
    from fastapi.responses import FileResponse

    from src.visualization import get_visualization_path

    filepath = get_visualization_path(filename)

    if filepath is None:
        raise HTTPException(
            status_code=404,
            detail=f"Execution trace '{filename}' not found",
        )

    return FileResponse(
        filepath,
        media_type="text/html",
        filename=filename,
    )


@router.post("/api/workflow-visualization/run-with-trace/{name}", tags=["workflow"])
async def run_workflow_with_trace(
    name: str,
    query: Optional[str] = Query(None, description="Chat query for chatbot workflow"),
    comment_id: Optional[int] = Query(
        None, description="Comment ID for project workflow"
    ),
    comment_text: Optional[str] = Query(
        None, description="Comment text for project workflow"
    ),
    top_k: int = Query(5, description="Number of results for chatbot"),
):
    """
    Run a workflow and capture its execution trace.

    For chatbot workflow, provide 'query' parameter.
    For project workflow, provide 'comment_id' and 'comment_text' parameters.
    """
    import uuid

    from src.visualization import save_execution_trace
    from src.workflow_server import create_chatbot_workflow, create_project_workflow

    execution_id = str(uuid.uuid4())[:8]

    if name == "chatbot":
        if not query:
            raise HTTPException(
                status_code=400,
                detail="Query parameter required for chatbot workflow",
            )

        workflow = create_chatbot_workflow()

        try:
            # Run the workflow
            handler = workflow.run(query=query, top_k=top_k)
            result = await handler

            # Save execution trace
            trace_file = save_execution_trace(handler, name, execution_id)

            return {
                "execution_id": execution_id,
                "workflow": name,
                "trace_file": trace_file,
                "result": {
                    "response": result.response,
                    "source_projects": result.source_projects,
                    "projects_found": result.projects_found,
                },
            }
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Workflow execution failed: {str(e)}",
            )

    elif name == "project":
        if not comment_id or not comment_text:
            raise HTTPException(
                status_code=400,
                detail="comment_id and comment_text parameters required for project workflow",
            )

        workflow = create_project_workflow()

        try:
            # Run the workflow
            handler = workflow.run(
                comment_id=comment_id,
                comment_text=comment_text,
            )
            result = await handler

            # Save execution trace
            trace_file = save_execution_trace(handler, name, execution_id)

            return {
                "execution_id": execution_id,
                "workflow": name,
                "trace_file": trace_file,
                "result": result,
            }
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Workflow execution failed: {str(e)}",
            )

    else:
        raise HTTPException(
            status_code=404,
            detail=f"Workflow '{name}' not found. Available: project, chatbot",
        )
