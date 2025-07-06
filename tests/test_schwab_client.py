import builtins
import os
import pytest

os.environ.setdefault("SCHWAB_CLIENT_ID", "dummy")
os.environ.setdefault("SCHWAB_CLIENT_SECRET", "dummy")

from gex import schwab_api
from gex.schwab_api import SchwabClient


class DummyClient:
    def token_age(self):
        return 0


def test_existing_token_skips_oauth(tmp_path, monkeypatch):
    token_file = tmp_path / "schwab_token.json"
    token_file.write_text("{}")
    monkeypatch.chdir(tmp_path)

    calls = {"token": False, "manual": False, "input": False}

    def fake_token_file(path, api_key, secret):
        calls["token"] = True
        return DummyClient()

    def fake_manual_flow(*args, **kwargs):
        calls["manual"] = True
        builtins.input("url?")
        return DummyClient()

    def fake_input(prompt=""):
        calls["input"] = True
        return ""

    monkeypatch.setattr(schwab_api, "client_from_token_file", fake_token_file)
    monkeypatch.setattr(schwab_api, "client_from_manual_flow", fake_manual_flow)
    monkeypatch.setattr(builtins, "input", fake_input)

    SchwabClient()
    assert calls["token"]
    assert not calls["manual"]
    assert not calls["input"]


def test_missing_token_triggers_oauth(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    calls = {"token": False, "manual": False, "input": 0}

    def fake_token_file(*args, **kwargs):
        calls["token"] = True
        return DummyClient()

    def fake_manual_flow(*args, **kwargs):
        calls["manual"] = True
        builtins.input("url?")
        return DummyClient()

    def fake_input(prompt=""):
        calls["input"] += 1
        return "dummy"

    monkeypatch.setattr(schwab_api, "client_from_token_file", fake_token_file)
    monkeypatch.setattr(schwab_api, "client_from_manual_flow", fake_manual_flow)
    monkeypatch.setattr(builtins, "input", fake_input)

    SchwabClient()
    assert not calls["token"]
    assert calls["manual"]
    assert calls["input"] == 1
