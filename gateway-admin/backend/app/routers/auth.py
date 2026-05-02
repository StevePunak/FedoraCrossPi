from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel

from app.services import auth

router = APIRouter(prefix="/api/auth", tags=["auth"])

SESSION_COOKIE = "gateway_session"


def _cookie_kwargs() -> dict:
    return {
        "key": SESSION_COOKIE,
        "httponly": True,
        "samesite": "lax",
        # Secure is enforced only in production (behind HTTPS reverse proxy)
        "secure": False,  # set True via env if desired
        "path": "/",
    }


class LoginBody(BaseModel):
    username: str
    password: str


class BootstrapBody(BaseModel):
    username: str
    password: str


class ChangePasswordBody(BaseModel):
    current_password: str
    new_password: str


def require_auth(request: Request) -> str:
    """FastAPI dependency: returns username, or raises 401."""
    if auth.is_dev_bypass():
        return "dev"
    token = request.cookies.get(SESSION_COOKIE)
    username = auth.validate_session(token)
    if not username:
        raise HTTPException(status_code=401, detail="not authenticated")
    return username


@router.get("/check")
def check(_: str = Depends(require_auth)):
    """Cheap auth probe used by nginx auth_request when fronting installed apps.
    Returns 204 if authenticated, 401 otherwise (raised by require_auth)."""
    return Response(status_code=204)


@router.get("/status")
def status(request: Request):
    token = request.cookies.get(SESSION_COOKIE)
    username = auth.validate_session(token) if token else None
    return {
        "authenticated": bool(username) or auth.is_dev_bypass(),
        "bootstrap": auth.is_bootstrap(),
        "username": username or (auth.get_username() if username else None),
        "dev_bypass": auth.is_dev_bypass(),
    }


@router.post("/bootstrap")
def bootstrap(body: BootstrapBody, request: Request, response: Response):
    if not auth.is_bootstrap():
        raise HTTPException(status_code=400, detail="already configured")
    try:
        auth.bootstrap_password(body.username, body.password)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Auto-login after bootstrap
    client_ip = request.client.host if request.client else "0.0.0.0"
    token = auth.login(body.username, body.password, client_ip)
    response.set_cookie(value=token, **_cookie_kwargs())
    return {"status": "ok", "username": body.username}


@router.post("/login")
def login(body: LoginBody, request: Request, response: Response):
    client_ip = request.client.host if request.client else "0.0.0.0"
    try:
        token = auth.login(body.username, body.password, client_ip)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    response.set_cookie(value=token, **_cookie_kwargs())
    return {"status": "ok", "username": body.username}


@router.post("/logout")
def logout(request: Request, response: Response):
    token = request.cookies.get(SESSION_COOKIE)
    if token:
        auth.logout(token)
    response.delete_cookie(key=SESSION_COOKIE, path="/")
    return {"status": "ok"}


@router.post("/change-password")
def change_password(
    body: ChangePasswordBody,
    username: str = Depends(require_auth),
):
    try:
        auth.change_password(body.current_password, body.new_password)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"status": "ok"}
