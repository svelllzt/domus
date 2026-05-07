from datetime import datetime
from typing import Any

from database import get_db_cursor


class UserModel:
    @staticmethod
    def create(email: str, password_hash: str, name: str, role: str = "user") -> int:
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO users (email, password_hash, name, role)
                VALUES (?, ?, ?, ?)
                """,
                (email.lower().strip(), password_hash, name.strip(), role),
            )
            return cursor.lastrowid

    @staticmethod
    def get_by_email(email: str) -> dict[str, Any] | None:
        with get_db_cursor() as cursor:
            cursor.execute("SELECT * FROM users WHERE email = ?", (email.lower().strip(),))
            row = cursor.fetchone()
            return dict(row) if row else None

    @staticmethod
    def get_by_id(user_id: int) -> dict[str, Any] | None:
        with get_db_cursor() as cursor:
            cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    @staticmethod
    def verify_email(user_id: int) -> None:
        with get_db_cursor() as cursor:
            cursor.execute("UPDATE users SET is_verified = 1 WHERE id = ?", (user_id,))

    @staticmethod
    def update_password(user_id: int, password_hash: str) -> None:
        with get_db_cursor() as cursor:
            cursor.execute(
                "UPDATE users SET password_hash = ? WHERE id = ?",
                (password_hash, user_id),
            )

    @staticmethod
    def set_role_and_shelter(user_id: int, role: str, shelter_id: int | None) -> None:
        with get_db_cursor() as cursor:
            cursor.execute(
                "UPDATE users SET role = ?, shelter_id = ? WHERE id = ?",
                (role, shelter_id, user_id),
            )

    @staticmethod
    def list_recent(limit: int = 20) -> list[dict[str, Any]]:
        with get_db_cursor() as cursor:
            cursor.execute(
                "SELECT * FROM users ORDER BY created_at DESC LIMIT ?",
                (limit,),
            )
            return [dict(row) for row in cursor.fetchall()]

    @staticmethod
    def delete_by_shelter(shelter_id: int) -> None:
        with get_db_cursor() as cursor:
            cursor.execute("DELETE FROM users WHERE shelter_id = ?", (shelter_id,))


class VerificationTokenModel:
    @staticmethod
    def create(user_id: int, token: str, token_type: str, expires_at: datetime) -> None:
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO verification_tokens (user_id, token, type, expires_at)
                VALUES (?, ?, ?, ?)
                """,
                (user_id, token, token_type, expires_at.isoformat()),
            )

    @staticmethod
    def get_valid(token: str, token_type: str) -> dict[str, Any] | None:
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                SELECT * FROM verification_tokens
                WHERE token = ? AND type = ? AND is_used = 0
                """,
                (token, token_type),
            )
            row = cursor.fetchone()
            if not row:
                return None
            token_data = dict(row)
            if datetime.fromisoformat(token_data["expires_at"]) < datetime.now():
                return None
            return token_data

    @staticmethod
    def get_valid_for_user(user_id: int, token: str, token_type: str) -> dict[str, Any] | None:
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                SELECT * FROM verification_tokens
                WHERE user_id = ? AND token = ? AND type = ? AND is_used = 0
                ORDER BY id DESC
                LIMIT 1
                """,
                (user_id, token, token_type),
            )
            row = cursor.fetchone()
            if not row:
                return None
            token_data = dict(row)
            if datetime.fromisoformat(token_data["expires_at"]) < datetime.now():
                return None
            return token_data

    @staticmethod
    def get_latest_valid_for_user(user_id: int, token_type: str) -> dict[str, Any] | None:
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                SELECT * FROM verification_tokens
                WHERE user_id = ? AND type = ? AND is_used = 0
                ORDER BY id DESC
                LIMIT 1
                """,
                (user_id, token_type),
            )
            row = cursor.fetchone()
            if not row:
                return None
            token_data = dict(row)
            if datetime.fromisoformat(token_data["expires_at"]) < datetime.now():
                return None
            return token_data

    @staticmethod
    def mark_all_used(user_id: int, token_type: str) -> None:
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                UPDATE verification_tokens
                SET is_used = 1
                WHERE user_id = ? AND type = ? AND is_used = 0
                """,
                (user_id, token_type),
            )

    @staticmethod
    def mark_used(token_id: int) -> None:
        with get_db_cursor() as cursor:
            cursor.execute(
                "UPDATE verification_tokens SET is_used = 1 WHERE id = ?",
                (token_id,),
            )
