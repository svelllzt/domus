from database import get_db_cursor


class FavoriteModel:
    @staticmethod
    def add(user_id: int, animal_id: int) -> None:
        with get_db_cursor() as cursor:
            cursor.execute(
                "INSERT OR IGNORE INTO favorites (user_id, animal_id) VALUES (?, ?)",
                (user_id, animal_id),
            )

    @staticmethod
    def remove(user_id: int, animal_id: int) -> None:
        with get_db_cursor() as cursor:
            cursor.execute(
                "DELETE FROM favorites WHERE user_id = ? AND animal_id = ?",
                (user_id, animal_id),
            )

    @staticmethod
    def is_favorite(user_id: int, animal_id: int) -> bool:
        with get_db_cursor() as cursor:
            cursor.execute(
                "SELECT 1 FROM favorites WHERE user_id = ? AND animal_id = ?",
                (user_id, animal_id),
            )
            return cursor.fetchone() is not None

    @staticmethod
    def list_ids_for_user(user_id: int) -> set[int]:
        with get_db_cursor() as cursor:
            cursor.execute(
                "SELECT animal_id FROM favorites WHERE user_id = ?",
                (user_id,),
            )
            return {int(row["animal_id"]) for row in cursor.fetchall()}

    @staticmethod
    def list_for_user(user_id: int) -> list[dict]:
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                SELECT a.*, p.filename as main_photo, s.name as shelter_name
                FROM favorites f
                JOIN animals a ON a.id = f.animal_id
                JOIN shelters s ON s.id = a.shelter_id
                LEFT JOIN animal_photos p ON p.animal_id = a.id AND p.is_main = 1
                WHERE f.user_id = ?
                ORDER BY f.added_at DESC
                """,
                (user_id,),
            )
            return [dict(row) for row in cursor.fetchall()]
