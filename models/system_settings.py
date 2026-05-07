from database import get_db_cursor


class SystemSettingsModel:
    @staticmethod
    def get_many(keys: list[str]) -> dict[str, str]:
        if not keys:
            return {}
        placeholders = ",".join("?" for _ in keys)
        with get_db_cursor() as cursor:
            cursor.execute(
                f"SELECT key, value FROM system_settings WHERE key IN ({placeholders})",
                tuple(keys),
            )
            return {row["key"]: row["value"] for row in cursor.fetchall()}

    @staticmethod
    def set_many(values: dict[str, str]) -> None:
        if not values:
            return
        with get_db_cursor() as cursor:
            for key, value in values.items():
                cursor.execute(
                    """
                    INSERT INTO system_settings (key, value, updated_at)
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(key) DO UPDATE SET
                        value = excluded.value,
                        updated_at = CURRENT_TIMESTAMP
                    """,
                    (key, value),
                )
