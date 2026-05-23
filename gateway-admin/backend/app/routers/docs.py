"""
Unauthenticated documentation endpoints.

Schemas, examples, and reference material exposed for build pipelines /
external app authors that need to discover the appliance's API surface
without holding a session cookie. FastAPI's auto-generated `/api/docs`
and `/api/openapi.json` are wired up publicly in main.py for the same
reason.

Nothing here exposes operational state, secrets, or anything that lets
an unauthenticated caller do work — just structure that's already
implied by the running code.
"""

from fastapi import APIRouter

from app.models.app_manifest import AppManifest

router = APIRouter(prefix="/api/docs", tags=["docs"])


@router.get("/manifest-schema")
def manifest_schema():
    """Canonical JSON Schema for an app's `manifest.json`, generated
    from the live `AppManifest` Pydantic model so consumers pull the
    truth from the appliance instead of mirroring a static copy that
    drifts."""
    return AppManifest.model_json_schema()
