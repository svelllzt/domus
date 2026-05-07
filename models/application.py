from typing import Any

from database import get_db_cursor


class AdoptionApplicationModel:
    @staticmethod
    def create(
        animal_id: int,
        user_id: int,
        applicant_name: str,
        applicant_phone: str,
        comment: str,
    ) -> int:
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO adoption_applications
                (animal_id, user_id, applicant_name, applicant_phone, comment)
                VALUES (?, ?, ?, ?, ?)
                """,
                (animal_id, user_id, applicant_name, applicant_phone, comment),
            )
            return cursor.lastrowid

    @staticmethod
    def list_for_user(user_id: int) -> list[dict[str, Any]]:
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                SELECT aa.*, a.name as animal_name, s.name as shelter_name
                FROM adoption_applications aa
                JOIN animals a ON a.id = aa.animal_id
                JOIN shelters s ON s.id = a.shelter_id
                WHERE aa.user_id = ?
                ORDER BY aa.created_at DESC
                """,
                (user_id,),
            )
            return [dict(row) for row in cursor.fetchall()]

    @staticmethod
    def list_for_shelter(shelter_id: int) -> list[dict[str, Any]]:
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                SELECT aa.*, a.name as animal_name, u.email as user_email
                FROM adoption_applications aa
                JOIN animals a ON a.id = aa.animal_id
                JOIN users u ON u.id = aa.user_id
                WHERE a.shelter_id = ?
                ORDER BY aa.created_at DESC
                """,
                (shelter_id,),
            )
            return [dict(row) for row in cursor.fetchall()]

    @staticmethod
    def set_status(application_id: int, status: str) -> None:
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                UPDATE adoption_applications
                SET status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (status, application_id),
            )

    @staticmethod
    def get_by_id(application_id: int) -> dict[str, Any] | None:
        with get_db_cursor() as cursor:
            cursor.execute("SELECT * FROM adoption_applications WHERE id = ?", (application_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    @staticmethod
    def get_active_for_animal(animal_id: int) -> dict[str, Any] | None:
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                SELECT * FROM adoption_applications
                WHERE animal_id = ? AND status IN ('new', 'processing', 'adopted')
                ORDER BY created_at DESC LIMIT 1
                """,
                (animal_id,),
            )
            row = cursor.fetchone()
            return dict(row) if row else None


class ShelterRegistrationRequestModel:
    @staticmethod
    def create(request_data: dict[str, Any]) -> int:
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO shelter_registration_requests (
                    user_id, shelter_name, shelter_city, shelter_address,
                    shelter_phone, shelter_description, applicant_position, comment
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    request_data["user_id"],
                    request_data["shelter_name"],
                    request_data.get("shelter_city"),
                    request_data.get("shelter_address"),
                    request_data.get("shelter_phone"),
                    request_data.get("shelter_description"),
                    request_data.get("applicant_position"),
                    request_data.get("comment"),
                ),
            )
            return cursor.lastrowid

    @staticmethod
    def list_all() -> list[dict[str, Any]]:
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                SELECT r.*, u.email as user_email, u.name as user_name
                FROM shelter_registration_requests r
                JOIN users u ON u.id = r.user_id
                ORDER BY r.created_at DESC
                """
            )
            return [dict(row) for row in cursor.fetchall()]

    @staticmethod
    def get_by_id(request_id: int) -> dict[str, Any] | None:
        with get_db_cursor() as cursor:
            cursor.execute(
                "SELECT * FROM shelter_registration_requests WHERE id = ?",
                (request_id,),
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    @staticmethod
    def set_status(request_id: int, status: str, admin_comment: str) -> None:
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                UPDATE shelter_registration_requests
                SET status = ?, admin_comment = ?
                WHERE id = ?
                """,
                (status, admin_comment, request_id),
            )

    @staticmethod
    def has_pending_for_user(user_id: int) -> bool:
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                SELECT 1 FROM shelter_registration_requests
                WHERE user_id = ? AND status = 'new'
                LIMIT 1
                """,
                (user_id,),
            )
            return cursor.fetchone() is not None

    @staticmethod
    def get_for_user(user_id: int) -> list[dict[str, Any]]:
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                SELECT * FROM shelter_registration_requests
                WHERE user_id = ?
                ORDER BY created_at DESC
                """,
                (user_id,),
            )
            return [dict(row) for row in cursor.fetchall()]
