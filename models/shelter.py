from typing import Any

from database import get_db_cursor


class ShelterModel:
    @staticmethod
    def create(
        name: str,
        city: str,
        address: str,
        phone: str,
        description: str,
        is_approved: int = 1,
    ) -> int:
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO shelters (name, city, address, phone, description, is_approved)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (name, city, address, phone, description, is_approved),
            )
            return cursor.lastrowid

    @staticmethod
    def get_by_id(shelter_id: int) -> dict[str, Any] | None:
        with get_db_cursor() as cursor:
            cursor.execute("SELECT * FROM shelters WHERE id = ?", (shelter_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    @staticmethod
    def list_approved() -> list[dict[str, Any]]:
        with get_db_cursor() as cursor:
            cursor.execute(
                "SELECT * FROM shelters WHERE is_approved = 1 ORDER BY created_at DESC"
            )
            return [dict(row) for row in cursor.fetchall()]

    @staticmethod
    def list_all() -> list[dict[str, Any]]:
        with get_db_cursor() as cursor:
            cursor.execute("SELECT * FROM shelters ORDER BY created_at DESC")
            return [dict(row) for row in cursor.fetchall()]

    @staticmethod
    def delete(shelter_id: int) -> None:
        with get_db_cursor() as cursor:
            cursor.execute("DELETE FROM shelters WHERE id = ?", (shelter_id,))
