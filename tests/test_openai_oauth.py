import base64
import hashlib
import json
import tempfile
import threading
import time
import unittest
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlsplit
from urllib.request import urlopen
from unittest.mock import patch

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from jose import jwk, jwt

from replicable import openai_oauth as oauth


class ChatGPTSignInTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        cls.private = private.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                          serialization.NoEncryption())
        public = private.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
        cls.jwks = {"keys": [{**jwk.construct(public, "RS256").to_dict(), "kid": "test-key"}]}

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "openai" / "session.json"
        self.session = oauth.ChatGPTSession(self.path)
        self.authorizations = []
        self.callbacks = []
        self.callback_errors = []
        self.subject = "test-account"
        self.scopes = oauth.SCOPES
        self.fail_exchange = False

    def response(self, client="oaiapp_test", nonce=None, token="test-access", subject=None):
        claims = {"iss": oauth.ISSUER, "sub": subject or self.subject, "aud": client,
                  "iat": int(time.time()), "exp": int(time.time()) + 3600}
        if nonce:
            claims["nonce"] = nonce
        claims["at_hash"] = base64.urlsafe_b64encode(hashlib.sha256(token.encode()).digest()[:16]).decode().rstrip("=")
        return {"access_token": token, "refresh_token": "test-refresh-" + token,
                "id_token": jwt.encode(claims, self.private, algorithm="RS256", headers={"kid": "test-key"}),
                "scope": self.scopes, "expires_in": 3600, "token_type": "Bearer"}

    def request(self, url, *, form=None, bearer=None):
        if url.endswith("openid-configuration"):
            return {"issuer": oauth.ISSUER, "authorization_endpoint": oauth.AUTHORIZE,
                    "token_endpoint": oauth.TOKEN, "jwks_uri": oauth.JWKS}
        if url == oauth.JWKS:
            return self.jwks
        if url == oauth.TOKEN:
            if self.fail_exchange:
                raise oauth.SignInError("Test exchange failure")
            if form["grant_type"] == "refresh_token":
                self.assertTrue(form["refresh_token"].startswith("test-refresh-"))
                return self.response(token="test-rotated-access")
            parameters = self.authorizations[-1]
            self.assertEqual(form["redirect_uri"], parameters["redirect_uri"])
            self.assertEqual(form["resource"], oauth.RESOURCE)
            self.assertEqual(form["client_id"], "oaiapp_test")
            challenge = base64.urlsafe_b64encode(hashlib.sha256(form["code_verifier"].encode()).digest()).decode().rstrip("=")
            self.assertEqual(challenge, parameters["code_challenge"])
            return self.response(nonce=parameters["nonce"])
        if url == oauth.RESOURCE + "/models":
            self.assertTrue(bearer.startswith("test-"))
            return {"models": [{"slug": "model-one", "display_name": "Model One", "visibility": "list"},
                               {"slug": "hidden-model", "visibility": "hide"}]}
        self.fail("Unexpected authentication request")

    def browser(self, url):
        parsed = urlsplit(url)
        self.assertEqual(parsed.scheme + "://" + parsed.netloc + parsed.path, oauth.AUTHORIZE)
        parameters = {key: values[0] for key, values in parse_qs(parsed.query).items()}
        self.authorizations.append(parameters)
        self.assertEqual(urlsplit(parameters["redirect_uri"]).hostname, "127.0.0.1")
        self.assertTrue(parameters["ext_agent_host_id"].startswith("urn:uuid:"))
        self.assertEqual(parameters["scope"], oauth.SCOPES)

        def callback():
            try:
                # A request with invalid state must not consume the pending login.
                invalid = parameters["redirect_uri"] + "?" + urlencode({"state": "wrong-state", "code": "test-code"})
                try:
                    urlopen(invalid, timeout=5)
                except Exception:
                    pass
                target = parameters["redirect_uri"] + "?" + urlencode({"state": parameters["state"],
                                                                           "code": "test-code", "client_id": "oaiapp_test"})
                with urlopen(target, timeout=5) as response:
                    self.assertEqual(response.status, 200)
            except Exception as error:
                self.callback_errors.append(error)

        thread = threading.Thread(target=callback)
        thread.start()
        self.callbacks.append(thread)
        return True

    def sign_in(self):
        with patch.object(oauth, "_request", side_effect=self.request), patch.object(oauth.webbrowser, "open", side_effect=self.browser), patch("builtins.print"):
            try:
                self.session.sign_in(timeout=5)
            finally:
                for thread in self.callbacks:
                    thread.join(timeout=6)
        self.assertEqual(self.callback_errors, [])

    def test_browser_flow_verifies_signed_identity_pkce_and_saves_private_session(self):
        self.sign_in()
        self.assertTrue(self.session.connected())
        data = json.loads(self.path.read_text())
        self.assertEqual(data["tokens"]["subject"], "test-account")
        self.assertEqual(data["registration"]["client_id"], "oaiapp_test")
        self.assertEqual(self.path.stat().st_mode & 0o777, 0o600)
        with patch.object(oauth, "_request", side_effect=self.request):
            self.assertEqual(self.session.models(), [{"slug": "model-one", "display_name": "Model One"}])

    def test_reauthorization_keeps_client_and_host_ids(self):
        self.sign_in()
        self.sign_in()
        self.assertEqual(self.authorizations[0]["client_id"], "dynamic_agent_client")
        self.assertEqual(self.authorizations[1]["client_id"], "oaiapp_test")
        self.assertEqual(self.authorizations[0]["ext_agent_host_id"], self.authorizations[1]["ext_agent_host_id"])

    def test_issued_client_survives_failed_exchange(self):
        self.fail_exchange = True
        with self.assertRaises(oauth.SignInError):
            self.sign_in()
        self.assertEqual(json.loads(self.path.read_text())["registration"]["client_id"], "oaiapp_test")
        self.fail_exchange = False
        self.sign_in()
        self.assertEqual(self.authorizations[1]["client_id"], "oaiapp_test")

    def test_declined_plan_usage_is_not_accepted_for_inference(self):
        self.scopes = "openid profile email"
        with self.assertRaisesRegex(oauth.SignInError, "plan usage was not authorized"):
            self.sign_in()
        self.assertFalse(self.session.connected())

    def test_refresh_rotates_tokens_and_preserves_account(self):
        self.sign_in()
        data = json.loads(self.path.read_text())
        data["tokens"]["expires_at"] = time.time() - 1
        oauth._save(self.path, data)
        with patch.object(oauth, "_request", side_effect=self.request):
            self.assertEqual(self.session.access_token(), "test-rotated-access")
        self.assertEqual(json.loads(self.path.read_text())["tokens"]["refresh_token"], "test-refresh-test-rotated-access")

    def test_refresh_cannot_switch_accounts(self):
        self.sign_in()
        data = json.loads(self.path.read_text())
        data["tokens"]["expires_at"] = time.time() - 1
        oauth._save(self.path, data)
        self.subject = "different-account"
        with patch.object(oauth, "_request", side_effect=self.request), self.assertRaisesRegex(oauth.SignInError, "identity could not be verified"):
            self.session.access_token()
        self.assertEqual(json.loads(self.path.read_text())["tokens"]["subject"], "test-account")

    def test_signature_audience_nonce_and_access_token_are_verified(self):
        response = self.response(nonce="original-nonce")
        with patch.object(oauth, "_request", return_value=self.jwks):
            for client, nonce, access in (("oaiapp_other", "original-nonce", "test-access"),
                                          ("oaiapp_test", "wrong-nonce", "test-access"),
                                          ("oaiapp_test", "original-nonce", "wrong-access")):
                with self.assertRaises(oauth.SignInError):
                    oauth._verify_identity(response["id_token"], client, access, nonce=nonce)
            bogus = jwt.encode({"sub": "forged"}, "untrusted-secret", algorithm="HS256")
            with self.assertRaises(oauth.SignInError):
                oauth._verify_identity(bogus, "oaiapp_test", "test-access")

    def test_missing_session_does_not_attempt_refresh(self):
        with patch.object(oauth, "_request") as request, self.assertRaises(oauth.SignInError):
            self.session.access_token()
        request.assert_not_called()


if __name__ == "__main__":
    unittest.main()
