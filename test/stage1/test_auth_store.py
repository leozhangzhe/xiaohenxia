"""Behavior and persistence guarantees of the authentication store."""
import logging
import base64

import pytest

from spiderfoot.auth_mysql import AuthDatabaseUnavailable, MySQLAuthStore


def store():
    return MySQLAuthStore(logging.getLogger("stage1.auth"))


def test_first_start_requires_an_explicit_admin_password(mysql_boundary):
    with pytest.raises(RuntimeError, match="SF_AUTH_ADMIN_PASS"):
        store().initialize()


@pytest.mark.parametrize("password", ["admin123", "short", "aaaaaaaaaaaa", "onlyletterslong"])
def test_bootstrap_rejects_weak_passwords(monkeypatch, mysql_boundary, password):
    monkeypatch.setenv("SF_AUTH_ADMIN_PASS", password)
    with pytest.raises(RuntimeError, match="12"):
        store().initialize()


def test_existing_default_password_requires_explicit_reset(monkeypatch, mysql_boundary):
    with pytest.raises(RuntimeError):
        store().initialize()
    assert store().create_user("admin", "admin123")
    with pytest.raises(RuntimeError, match="default administrator password"):
        store().initialize()


def test_explicit_reset_replaces_legacy_default_without_deleting_account(monkeypatch, mysql_boundary):
    with pytest.raises(RuntimeError):
        store().initialize()
    assert store().create_user("admin", "admin123")
    monkeypatch.setenv("SF_AUTH_ADMIN_PASS", "StageOne-Reset-8675309")
    monkeypatch.setenv("SF_AUTH_ADMIN_RESET", "1")
    store().initialize()
    assert store().verify_user("admin", "StageOne-Reset-8675309")
    assert not store().verify_user("admin", "admin123")


@pytest.mark.parametrize("operation", ["initialize", "user_exists", "verify_user", "create_user"])
def test_database_failures_are_explicit_at_each_public_operation(mysql_boundary, operation):
    mysql_boundary.available = False
    args = {
        "initialize": (), "user_exists": ("someone",),
        "verify_user": ("someone", "TestPassword-4387"),
        "create_user": ("someone", "TestPassword-4387"),
    }
    with pytest.raises(AuthDatabaseUnavailable, match="authentication database"):
        getattr(store(), operation)(*args[operation])


def test_accounts_persist_with_salted_password_hashes(monkeypatch, mysql_boundary):
    password = "StageOne-Hash-Test-4387"
    monkeypatch.setenv("SF_AUTH_ADMIN_PASS", password)
    store().initialize()
    assert store().create_user("participant", password)
    first = mysql_boundary.stored_hash("admin")
    second = mysql_boundary.stored_hash("participant")
    algorithm, iterations, salt, digest = first.split("$")
    assert algorithm == "pbkdf2_sha256"
    assert int(iterations) >= 600000
    assert len(base64.b64decode(salt)) >= 16
    assert len(base64.b64decode(digest)) == 32
    assert password not in first and first != second
    monkeypatch.delenv("SF_AUTH_ADMIN_PASS")
    store().initialize()
    assert store().verify_user("admin", password)
    assert store().verify_user("participant", password)
    assert not store().verify_user("participant", "incorrect-password")


def test_usernames_are_normalized_at_the_storage_boundary(monkeypatch, mysql_boundary):
    monkeypatch.setenv("SF_AUTH_ADMIN_PASS", "StageOne-Admin-4387")
    store().initialize()
    assert store().create_user("  participant  ", "Participant-Password-4387")
    assert store().user_exists("participant")
    assert store().verify_user("  participant  ", "Participant-Password-4387")
    assert store().verify_user("participant", "Participant-Password-4387")


@pytest.mark.parametrize("name,value", [
    ("SF_AUTH_MYSQL_DATABASE", "bad`database"),
    ("SF_AUTH_MYSQL_PORT", "not-a-port"),
    ("SF_AUTH_PBKDF2_ITERATIONS", "1"),
])
def test_invalid_security_configuration_fails_clearly(monkeypatch, name, value):
    monkeypatch.setenv(name, value)
    with pytest.raises(RuntimeError, match=name):
        store()


def test_readiness_check_is_read_only_and_requires_an_initialized_admin(monkeypatch, mysql_boundary):
    with pytest.raises(AuthDatabaseUnavailable):
        store().check_ready()
    monkeypatch.setenv("SF_AUTH_ADMIN_PASS", "StageOne-Ready-4387")
    store().initialize()
    monkeypatch.delenv("SF_AUTH_ADMIN_PASS")
    assert store().check_ready() is True


def test_plaintext_admin_hash_is_never_accepted_and_requires_reset(monkeypatch, mysql_boundary):
    monkeypatch.setenv("SF_AUTH_ADMIN_PASS", "StageOne-Plaintext-4387")
    store().initialize()
    mysql_boundary.replace_stored_hash("admin", "admin123")
    assert not store().verify_user("admin", "admin123")
    with pytest.raises(RuntimeError, match="password hash"):
        store().initialize()


def test_legacy_200000_iteration_hashes_still_work(monkeypatch, mysql_boundary):
    monkeypatch.setenv("SF_AUTH_PBKDF2_ITERATIONS", "200000")
    monkeypatch.setenv("SF_AUTH_ADMIN_PASS", "StageOne-Legacy-4387")
    store().initialize()
    monkeypatch.delenv("SF_AUTH_PBKDF2_ITERATIONS")
    assert store().verify_user("admin", "StageOne-Legacy-4387")


@pytest.mark.parametrize("name", ["SF_AUTH_MYSQL_USER", "SF_AUTH_MYSQL_PASSWORD"])
def test_database_credentials_must_be_explicit(monkeypatch, name):
    monkeypatch.delenv(name)
    with pytest.raises(RuntimeError, match=name):
        store()


def test_invalid_administrator_name_is_rejected_before_initialization(monkeypatch):
    monkeypatch.setenv("SF_AUTH_ADMIN_USER", "  ")
    with pytest.raises(RuntimeError, match="SF_AUTH_ADMIN_USER"):
        store()


def test_an_environment_password_does_not_silently_reset_existing_accounts(monkeypatch, mysql_boundary):
    monkeypatch.setenv("SF_AUTH_ADMIN_PASS", "StageOne-Original-4387")
    store().initialize()
    monkeypatch.setenv("SF_AUTH_ADMIN_PASS", "StageOne-Unrequested-4387")
    store().initialize()
    assert store().verify_user("admin", "StageOne-Original-4387")
    assert not store().verify_user("admin", "StageOne-Unrequested-4387")
