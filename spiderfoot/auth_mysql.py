import base64
import hashlib
import hmac
import os
import re

import pymysql


class AuthConfigurationError(RuntimeError):
    """Authentication requires operator configuration before it can start."""


class AuthDatabaseUnavailable(RuntimeError):
    """The persistent authentication database cannot serve the request."""


class MySQLAuthStore:
    """MySQL-backed authentication store."""

    def __init__(self, logger):
        self.log = logger
        self.host = os.getenv("SF_AUTH_MYSQL_HOST", "127.0.0.1")
        self.port = self._integer_setting("SF_AUTH_MYSQL_PORT", 3306, 1, 65535)
        self.user = os.getenv("SF_AUTH_MYSQL_USER", "").strip()
        self.password = os.getenv("SF_AUTH_MYSQL_PASSWORD")
        if not self.user:
            raise AuthConfigurationError("Set SF_AUTH_MYSQL_USER explicitly.")
        if not self.password:
            raise AuthConfigurationError("Set SF_AUTH_MYSQL_PASSWORD to the database account password.")
        self.admin_user = os.getenv("SF_AUTH_ADMIN_USER", "admin").strip()
        if not 3 <= len(self.admin_user) <= 32:
            raise AuthConfigurationError("SF_AUTH_ADMIN_USER must contain 3-32 characters after trimming.")
        self.database = os.getenv("SF_AUTH_MYSQL_DATABASE", "spiderfoot_auth")
        if not re.fullmatch(r"[A-Za-z0-9_]{1,64}", self.database):
            raise AuthConfigurationError("SF_AUTH_MYSQL_DATABASE must be a simple 1-64 character database name.")
        self.iterations = self._integer_setting("SF_AUTH_PBKDF2_ITERATIONS", 600000, 200000, 2000000)

    @staticmethod
    def _integer_setting(name, default, minimum, maximum):
        try:
            value = int(os.getenv(name, str(default)))
        except ValueError:
            raise AuthConfigurationError(f"{name} must be an integer.") from None
        if not minimum <= value <= maximum:
            raise AuthConfigurationError(f"{name} must be between {minimum} and {maximum}.")
        return value

    def _connect(self, with_database=True):
        kwargs = {
            "host": self.host,
            "port": self.port,
            "user": self.user,
            "password": self.password,
            "charset": "utf8mb4",
            "autocommit": True,
            "cursorclass": pymysql.cursors.Cursor,
            "connect_timeout": 5,
            "read_timeout": 5,
            "write_timeout": 5,
        }
        if with_database:
            kwargs["database"] = self.database
        try:
            return pymysql.connect(**kwargs)
        except pymysql.Error:
            raise AuthDatabaseUnavailable("MySQL authentication database is unavailable.") from None

    def initialize(self):
        """Create database, table, and optional bootstrap user."""
        conn = self._connect(with_database=False)
        try:
            with conn.cursor() as cursor:
                cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{self.database}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        except pymysql.Error:
            raise AuthDatabaseUnavailable("MySQL authentication database initialization failed.") from None
        finally:
            conn.close()

        conn = self._connect(with_database=True)
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS users (
                      id INT AUTO_INCREMENT PRIMARY KEY,
                      username VARCHAR(64) NOT NULL UNIQUE,
                      password_hash VARCHAR(255) NOT NULL,
                      created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                    """
                )
        except pymysql.Error:
            raise AuthDatabaseUnavailable("MySQL authentication database initialization failed.") from None
        finally:
            conn.close()

        admin_user = self.admin_user
        admin_pass = os.getenv("SF_AUTH_ADMIN_PASS")
        if os.getenv("SF_AUTH_ADMIN_RESET", "0") == "1":
            if not admin_pass:
                raise AuthConfigurationError("Administrator reset requires SF_AUTH_ADMIN_PASS.")
            self._validate_admin_password(admin_pass)
            if self.user_exists(admin_user):
                conn = self._connect(with_database=True)
                try:
                    with conn.cursor() as cursor:
                        cursor.execute(
                            "UPDATE users SET password_hash=%s WHERE username=%s",
                            (self._hash_password(admin_pass), admin_user),
                        )
                except pymysql.Error:
                    raise AuthDatabaseUnavailable("MySQL authentication database reset failed.") from None
                finally:
                    conn.close()
                self.log.warning("Reset the configured administrator password; unset SF_AUTH_ADMIN_RESET now.")
        if not self.user_exists(admin_user):
            if not admin_pass:
                raise AuthConfigurationError("First start requires SF_AUTH_ADMIN_PASS; no default password is created.")
            self._validate_admin_password(admin_pass)
            if not self.create_user(admin_user, admin_pass):
                raise AuthConfigurationError("Unable to initialize the administrator account.")
            self.log.info("Initialized the configured administrator account.")
        self.check_ready()

    def check_ready(self):
        """Check existing authentication storage without creating or changing data."""
        admin_user = self.admin_user
        for username in {admin_user, "admin"}:
            encoded = self._stored_password_hash(username)
            if encoded is None:
                if username == admin_user:
                    raise AuthConfigurationError("Administrator is not initialized; configure SF_AUTH_ADMIN_PASS and initialize.")
                continue
            try:
                self._decode_password_hash(encoded)
            except (ValueError, TypeError):
                raise AuthConfigurationError(
                    "Administrator password hash is invalid; configure the account and use SF_AUTH_ADMIN_RESET=1."
                ) from None
            if self._verify_password("admin123", encoded):
                raise AuthConfigurationError(
                    "Unsafe default administrator password detected. Set SF_AUTH_ADMIN_USER to that account, "
                    "SF_AUTH_ADMIN_PASS to a strong password and SF_AUTH_ADMIN_RESET=1 for one startup."
                )
        return True

    @staticmethod
    def _validate_admin_password(password):
        if (not 12 <= len(password) <= 1024
                or not any(c.isalpha() for c in password)
                or not any(c.isdigit() or (not c.isalnum() and not c.isspace()) for c in password)):
            raise AuthConfigurationError(
                "SF_AUTH_ADMIN_PASS must contain 12-1024 characters, including letters and a digit or symbol."
            )

    def create_user(self, username, password):
        username = (username or "").strip()
        pwd_hash = self._hash_password(password)
        conn = self._connect(with_database=True)
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO users (username, password_hash) VALUES (%s, %s)",
                    (username, pwd_hash),
                )
            return True
        except pymysql.IntegrityError:
            return False
        except pymysql.Error:
            raise AuthDatabaseUnavailable("MySQL authentication database registration failed.") from None
        finally:
            conn.close()

    def get_user(self, username):
        """Return the canonical persisted identity, never a client-supplied ID."""
        conn = self._connect(with_database=True)
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT id, username FROM users WHERE username=%s", (username.strip(),))
                row = cur.fetchone()
            return {"id": int(row[0]), "username": row[1]} if row else None
        except Exception:
            raise AuthDatabaseUnavailable("Authentication database is unavailable.") from None
        finally:
            conn.close()

    def user_exists(self, username):
        username = (username or "").strip()
        conn = self._connect(with_database=True)
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1 FROM users WHERE username=%s LIMIT 1", (username,))
                return cursor.fetchone() is not None
        except pymysql.Error:
            raise AuthDatabaseUnavailable("MySQL authentication database lookup failed.") from None
        finally:
            conn.close()

    def verify_user(self, username, password):
        username = (username or "").strip()
        encoded = self._stored_password_hash(username)
        return self._verify_password(password, encoded) if encoded is not None else False

    def _stored_password_hash(self, username):
        conn = self._connect(with_database=True)
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT password_hash FROM users WHERE username=%s LIMIT 1", (username,))
                row = cursor.fetchone()
                return row[0] if row else None
        except pymysql.Error:
            raise AuthDatabaseUnavailable("MySQL authentication database verification failed.") from None
        finally:
            conn.close()

    def _hash_password(self, password, salt=None):
        if salt is None:
            salt = os.urandom(16)
        dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, self.iterations)
        return "pbkdf2_sha256${}${}${}".format(
            self.iterations,
            base64.b64encode(salt).decode("ascii"),
            base64.b64encode(dk).decode("ascii"),
        )

    def _verify_password(self, password, encoded):
        try:
            if not isinstance(password, str):
                return False
            iterations, salt, expected = self._decode_password_hash(encoded)
            current = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
            return hmac.compare_digest(current, expected)
        except (ValueError, TypeError, UnicodeError):
            return False

    @staticmethod
    def _decode_password_hash(encoded):
        algorithm, cost, salt_b64, hash_b64 = encoded.split("$", 3)
        iterations = int(cost)
        salt = base64.b64decode(salt_b64, validate=True)
        digest = base64.b64decode(hash_b64, validate=True)
        if (algorithm != "pbkdf2_sha256" or not 200000 <= iterations <= 2000000
                or not 16 <= len(salt) <= 64 or len(digest) != 32):
            raise ValueError("Invalid password hash")
        return iterations, salt, digest
