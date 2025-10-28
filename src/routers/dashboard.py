"""Nexus Alpha Signal Intelligence Dashboard Router."""
from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from pathlib import Path

router = APIRouter()


@router.get("/dashboard", response_class=HTMLResponse)
async def signal_dashboard():
    """Serve the Nexus Alpha Signal Intelligence Dashboard."""
    template_path = Path(__file__).parent.parent / "templates" / "nexus-dashboard.html"
    
    if not template_path.exists():
        raise HTTPException(status_code=404, detail="Dashboard not found")
    
    with open(template_path, "r") as f:
        content = f.read()
    
    return HTMLResponse(content=content)


@router.get("/", response_class=HTMLResponse)
async def root_dashboard():
    """Redirect root to dashboard."""
    return await signal_dashboard()
