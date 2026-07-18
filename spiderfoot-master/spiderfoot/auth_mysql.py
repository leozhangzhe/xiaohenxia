import base64
import hashlib
import hmac
import os

import pymysql


class MySQLAuthStore:
    """MySQL-backed authentication store."""

    def __init__(self, logger):
        self.log = logger
        self.host = os.getenv("SF_AUTH_MYSQL_HOST", "127.0.0.1")
        self.port = int(os.getenv("SF_AUTH_MYSQL_PORT", "3306"))
        self.user = os.getenv("SF_AUTH_MYSQL_USER", "root")
        self.password = os.getenv("SF_AUTH_MYSQL_PASSWORD", "")
        self.database = os.getenv("SF_AUTH_MYSQL_DATABASE", "spiderfoot_auth")
        self.iterations = int(os.getenv("SF_AUTH_PBKDF2_ITERATIONS", "200000"))

    def _connect(self, with_database=True):
        kwargs = {
            "host": self.host,
            "port": self.port,
            "user": self.user,
            "password": self.password,
            "charset": "utf8mb4",
            "autocommit": True,
            "cursorclass": pymysql.cursors.Cursor,
        }
        if with_database:
            kwargs["database"] = self.database
        return pymysql.connect(**kwargs)

    def initialize(self):
        """Create database, table, and optional bootstrap user."""
        conn = self._connect(with_database=False)
        try:
            with conn.cursor() as cursor:
                cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{self.database}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
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
        finally:
            conn.close()

        admin_user = os.getenv("SF_AUTH_ADMIN_USER", "admin")
        admin_pass = os.getenv("SF_AUTH_ADMIN_PASS", "<ADMIN_PASSWORD>")
        if not self.user_exists(admin_user):
            self.create_user(admin_user, admin_pass)
            self.log.warning("Created default MySQL login user '%s'. Please change password immediately.", admin_user)

    def create_user(self, username, password):
        pwd_hash = self._hash_password(password)
        conn = self._connect(with_database=True)
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO users (username, password_hash) VALUES (%s, %s)",
                    (username, pwd_hash),
                )
            return True
        except Exception as e:
            self.log.error("Failed to create user %s: %s", username, e)
            return False
        finally:
            conn.close()

    def user_exists(self, username):
        conn = self._connect(with_database=True)
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1 FROM users WHERE username=%s LIMIT 1", (username,))
                return cursor.fetchone() is not None
        finally:
            conn.close()

    def verify_user(self, username, password):
        conn = self._connect(with_database=True)
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT password_hash FROM users WHERE username=%s LIMIT 1", (username,))
                row = cursor.fetchone()
                if not row:
                    return False
                return self._verify_password(password, row[0])
        except Exception as e:
            self.log.error("MySQL auth verification failed: %s", e)
            return False
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
            algorithm, iterations, salt_b64, hash_b64 = encoded.split("$", 3)
            if algorithm != "pbkdf2_sha256":
                return False
            salt = base64.b64decode(salt_b64.encode("ascii"))
            expected = base64.b64decode(hash_b64.encode("ascii"))
            current = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, int(iterations))
            return hmac.compare_digest(current, expected)
        except Exception:
            return False
