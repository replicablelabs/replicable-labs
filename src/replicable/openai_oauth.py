"""Local Sign in with ChatGPT, adapted from Replicable's Improve connection.

Uses this lab's own registration and credentials, never another app's login.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import math
import os
import re
import secrets
import tempfile
import time
import uuid
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

ISSUER = "https://auth.openai.com"
AUTHORIZE = ISSUER + "/api/accounts/authorize"
TOKEN = ISSUER + "/api/accounts/oauth/token"
JWKS = ISSUER + "/.well-known/jwks.json"
RESOURCE = "https://api.openai.com/v1"
SCOPES = "openid profile email offline_access resource.invoke chatgpt.tokens.use.direct"
REQUIRED = {"resource.invoke", "chatgpt.tokens.use.direct"}


class SignInError(RuntimeError):
    """A credential-free message suitable for the terminal."""


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *_args, **_kwargs):
        return None


def _request(url: str, *, form: dict | None = None, bearer: str | None = None) -> dict:
    if url not in {TOKEN, JWKS, ISSUER + "/.well-known/openid-configuration", RESOURCE + "/models"}:
        raise SignInError("OpenAI authentication endpoint is not supported.")
    headers = {"Accept": "application/json"}
    if bearer:
        headers["Authorization"] = "Bearer " + bearer
    data = None
    if form is not None:
        data = urlencode(form).encode()
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    try:
        with build_opener(ProxyHandler({}), _NoRedirect()).open(Request(url, data=data, headers=headers), timeout=20) as response:
            raw = response.read(4 * 1024 * 1024 + 1)
            if len(raw) > 4 * 1024 * 1024:
                raise SignInError("OpenAI authentication response was too large.")
            value = json.loads(raw)
            if not isinstance(value, dict):
                raise ValueError()
            return value
    except HTTPError as error:
        raise SignInError(f"OpenAI rejected the authentication request (HTTP {error.code}). Sign in again.") from None
    except (URLError, OSError, ValueError):
        raise SignInError("Could not complete the OpenAI authentication request. Check your connection and try again.") from None


def _read(path: Path) -> dict:
    try:
        data = json.loads(path.read_text())
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _save(path: Path, data: dict) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", dir=path.parent, delete=False) as file:
            temporary = Path(file.name)
            os.chmod(temporary, 0o600)
            json.dump(data, file)
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def _verify_identity(id_token: str, client_id: str, access_token: str, *, nonce=None, subject=None) -> dict:
    from jose import jwt

    try:
        claims = jwt.decode(
            id_token, _request(JWKS), algorithms=["RS256", "ES256"],
            audience=client_id, issuer=ISSUER, access_token=access_token,
            options={"require_exp": True, "require_iat": True, "require_sub": True,
                     "require_aud": True, "require_iss": True},
        )
        if not isinstance(claims.get("sub"), str) or not claims["sub"]:
            raise ValueError()
        if ("azp" in claims or isinstance(claims.get("aud"), list) and len(claims["aud"]) > 1) and claims.get("azp") != client_id:
            raise ValueError()
        if nonce is not None and not hmac.compare_digest(str(claims.get("nonce", "")), nonce):
            raise ValueError()
        if subject is not None and not hmac.compare_digest(claims["sub"], subject):
            raise ValueError()
        return claims
    except Exception:
        raise SignInError("OpenAI identity could not be verified. Sign in again with the same ChatGPT account.") from None


def _tokens(response: dict, claims: dict, client_id: str) -> dict:
    try:
        scopes = response.get("scope", "").split()
        if not REQUIRED.issubset(scopes):
            raise SignInError("ChatGPT plan usage was not authorized. Sign in and allow plan usage to run the lab.")
        lifetime = int(response["expires_in"])
        if response.get("token_type", "").lower() != "bearer" or not 30 <= lifetime <= 86400:
            raise ValueError()
        if any(not isinstance(response.get(key), str) or not response[key] for key in ("access_token", "refresh_token", "id_token")):
            raise ValueError()
        return {"issuer": ISSUER, "subject": claims["sub"], "client_id": client_id,
                "access_token": response["access_token"], "refresh_token": response["refresh_token"],
                "id_token": response["id_token"], "scopes": scopes, "expires_at": time.time() + lifetime}
    except SignInError:
        raise
    except (KeyError, ValueError, TypeError, AttributeError):
        raise SignInError("OpenAI did not return a renewable ChatGPT session. Sign in again.") from None


class ChatGPTSession:
    def __init__(self, path: Path):
        self.path = Path(path).expanduser().resolve()

    def connected(self) -> bool:
        tokens = _read(self.path).get("tokens") or {}
        try:
            return bool(tokens.get("issuer") == ISSUER and tokens.get("subject")
                        and tokens.get("client_id") and tokens.get("access_token")
                        and tokens.get("refresh_token") and tokens.get("id_token")
                        and type(tokens["expires_at"]) in (int, float) and math.isfinite(tokens["expires_at"])
                        and REQUIRED.issubset(tokens.get("scopes", [])))
        except (AttributeError, KeyError, TypeError, ValueError):
            return False

    def access_token(self) -> str:
        from filelock import FileLock

        if not self.connected():
            raise SignInError("Sign in to ChatGPT through 'replicable labs start deep-agents-langgraph-101'.")
        with FileLock(str(self.path) + ".lock", timeout=30):
            data = _read(self.path)
            tokens = data["tokens"]
            if tokens["expires_at"] <= time.time() + 60:
                response = _request(TOKEN, form={"grant_type": "refresh_token", "client_id": tokens["client_id"],
                                                "refresh_token": tokens["refresh_token"], "resource": RESOURCE})
                claims = _verify_identity(response.get("id_token"), tokens["client_id"], response.get("access_token"), subject=tokens["subject"])
                data["tokens"] = _tokens(response, claims, tokens["client_id"])
                _save(self.path, data)
                tokens = data["tokens"]
            return tokens["access_token"]

    def models(self) -> list[dict]:
        data = _request(RESOURCE + "/models", bearer=self.access_token())
        items = data.get("models")
        models = []
        for item in items if isinstance(items, list) else []:
            if (isinstance(item, dict) and item.get("visibility") == "list"
                    and isinstance(item.get("slug"), str) and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,199}", item["slug"])):
                models.append({"slug": item["slug"], "display_name": str(item.get("display_name") or item["slug"])[:160]})
        if not models:
            raise SignInError("No models are available for this ChatGPT account. Check its plan usage permissions.")
        return models

    def sign_in(self, *, timeout: float = 180) -> None:
        discovery = _request(ISSUER + "/.well-known/openid-configuration")
        expected = {"issuer": ISSUER, "authorization_endpoint": AUTHORIZE, "token_endpoint": TOKEN, "jwks_uri": JWKS}
        if any(discovery.get(key) != value for key, value in expected.items()):
            raise SignInError("OpenAI OIDC discovery could not be verified.")
        data = _read(self.path)
        registration = data.setdefault("registration", {})
        registration.setdefault("host_id", "urn:uuid:" + str(uuid.uuid4()))
        _save(self.path, data)
        requested = registration.get("client_id") or "dynamic_agent_client"
        state, nonce, verifier = (secrets.token_urlsafe(32) for _ in range(3))
        challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
        result = {}

        class Callback(BaseHTTPRequestHandler):
            def setup(self):
                super().setup()
                self.connection.settimeout(5)

            def log_message(self, *_args):
                pass  # Callback query strings contain credentials.

            def do_GET(self):
                parsed = urlsplit(self.path)
                query = parse_qs(parsed.query)
                valid = parsed.path == "/auth/callback" and hmac.compare_digest(query.get("state", [""])[0], state)
                if valid:
                    result.update({key: value[0] for key, value in query.items()})
                self.send_response(200 if valid else 400)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(b"You can return to the Replicable lab terminal." if valid else b"Invalid sign-in callback.")

        with HTTPServer(("127.0.0.1", 0), Callback) as server:
            server.timeout = 1
            redirect = f"http://127.0.0.1:{server.server_port}/auth/callback"
            parameters = {"client_id": requested, "response_type": "code", "redirect_uri": redirect,
                          "scope": SCOPES, "resource": RESOURCE, "state": state, "nonce": nonce,
                          "code_challenge_method": "S256", "code_challenge": challenge,
                          "ext_agent_host_id": registration["host_id"]}
            if requested == "dynamic_agent_client":
                parameters["agent_name_hint"] = "Replicable Deep Agents Lab"
            url = AUTHORIZE + "?" + urlencode(parameters)
            print("Continue with ChatGPT in your browser and allow ChatGPT plan usage.")
            print("If the browser does not open, visit:\n" + url)
            webbrowser.open(url)
            deadline = time.monotonic() + timeout
            while not result and time.monotonic() < deadline:
                server.handle_request()
        if not result:
            raise SignInError("ChatGPT sign-in timed out. Start the lab again to retry.")
        if result.get("error") or not result.get("code"):
            raise SignInError("ChatGPT sign-in was cancelled or denied. Start the lab again to retry.")
        issued = result.get("client_id") or requested
        if requested == "dynamic_agent_client":
            if not re.fullmatch(r"oaiapp_[A-Za-z0-9_-]{1,249}", issued):
                raise SignInError("ChatGPT client registration was not completed. Sign in again.")
        elif issued != requested:
            raise SignInError("ChatGPT returned a different registration. Sign in again with the same account.")
        registration["client_id"] = issued
        _save(self.path, data)  # Retain the issued ID even if this code expires.
        response = _request(TOKEN, form={"grant_type": "authorization_code", "client_id": issued,
                                        "code": result["code"], "code_verifier": verifier,
                                        "redirect_uri": redirect, "resource": RESOURCE})
        claims = _verify_identity(response.get("id_token"), issued, response.get("access_token"),
                                  nonce=nonce, subject=registration.get("subject"))
        data["tokens"] = _tokens(response, claims, issued)
        registration["subject"] = claims["sub"]
        _save(self.path, data)
