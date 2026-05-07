from typing import Any

from config import ITEMS_PER_PAGE
from database import get_db_cursor


def _as_str_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(x) for x in value if x]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


class AnimalModel:
    @staticmethod
    def create(animal_data: dict[str, Any]) -> int:
        search_vector = " ".join(
            [
                animal_data.get("name", ""),
                animal_data.get("species", ""),
                animal_data.get("breed", ""),
                animal_data.get("color", ""),
                animal_data.get("temperament", ""),
                animal_data.get("description", ""),
            ]
        ).lower()

        with get_db_cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO animals (
                    species, breed, name, age, sex, size, color, health, temperament,
                    compatible_with_children, compatible_with_animals, description,
                    status, shelter_id, search_vector
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    animal_data["species"],
                    animal_data.get("breed"),
                    animal_data["name"],
                    animal_data.get("age"),
                    animal_data.get("sex", "unknown"),
                    animal_data.get("size", "medium"),
                    animal_data.get("color"),
                    animal_data.get("health"),
                    animal_data.get("temperament"),
                    int(bool(animal_data.get("compatible_with_children"))),
                    int(bool(animal_data.get("compatible_with_animals"))),
                    animal_data.get("description"),
                    animal_data.get("status", "available"),
                    animal_data["shelter_id"],
                    search_vector,
                ),
            )
            return cursor.lastrowid

    @staticmethod
    def get_by_id(animal_id: int) -> dict[str, Any] | None:
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                SELECT a.*, s.name as shelter_name, s.city as shelter_city, p.filename as main_photo
                FROM animals a
                JOIN shelters s ON s.id = a.shelter_id
                LEFT JOIN animal_photos p ON p.animal_id = a.id AND p.is_main = 1
                WHERE a.id = ?
                """,
                (animal_id,),
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    @staticmethod
    def add_photo(animal_id: int, filename: str, is_main: bool = False) -> None:
        with get_db_cursor() as cursor:
            if is_main:
                cursor.execute(
                    "UPDATE animal_photos SET is_main = 0 WHERE animal_id = ?",
                    (animal_id,),
                )
            cursor.execute(
                "INSERT INTO animal_photos (animal_id, filename, is_main) VALUES (?, ?, ?)",
                (animal_id, filename, int(is_main)),
            )

    @staticmethod
    def get_photos(animal_id: int) -> list[dict[str, Any]]:
        with get_db_cursor() as cursor:
            cursor.execute(
                "SELECT * FROM animal_photos WHERE animal_id = ? ORDER BY is_main DESC, uploaded_at DESC",
                (animal_id,),
            )
            return [dict(row) for row in cursor.fetchall()]

    @staticmethod
    def _append_filter_sql(query: str, params: list[Any], filters: dict[str, Any]) -> tuple[str, list[Any]]:
        species = _as_str_list(filters.get("species"))
        if species:
            placeholders = ",".join("?" * len(species))
            query += f" AND a.species IN ({placeholders})"
            params.extend(species)

        sexes = _as_str_list(filters.get("sex"))
        if sexes:
            placeholders = ",".join("?" * len(sexes))
            query += f" AND a.sex IN ({placeholders})"
            params.extend(sexes)

        sizes = _as_str_list(filters.get("size"))
        if sizes:
            placeholders = ",".join("?" * len(sizes))
            query += f" AND a.size IN ({placeholders})"
            params.extend(sizes)

        cities = _as_str_list(filters.get("city"))
        if cities:
            placeholders = ",".join("?" * len(cities))
            query += f" AND s.city IN ({placeholders})"
            params.extend(cities)

        age_ranges = _as_str_list(filters.get("age_ranges"))
        if age_ranges:
            age_parts: list[str] = []
            for bucket in age_ranges:
                if bucket == "0-1":
                    age_parts.append("(a.age IS NOT NULL AND a.age <= 1)")
                elif bucket == "1-3":
                    age_parts.append("(a.age BETWEEN 1 AND 3)")
                elif bucket == "4-7":
                    age_parts.append("(a.age BETWEEN 4 AND 7)")
                elif bucket == "8+":
                    age_parts.append("(a.age >= 8)")
            if age_parts:
                query += " AND (" + " OR ".join(age_parts) + ")"

        status = filters.get("status")
        if status:
            query += " AND a.status = ?"
            params.append(status)

        search_query = filters.get("query")
        if search_query:
            query += " AND a.search_vector LIKE ?"
            params.append(f"%{str(search_query).lower()}%")

        return query, params

    @staticmethod
    def filter_animals(filters: dict[str, Any], page: int = 1) -> list[dict[str, Any]]:
        query = """
            SELECT a.*, s.name as shelter_name, p.filename as main_photo
            FROM animals a
            JOIN shelters s ON s.id = a.shelter_id
            LEFT JOIN animal_photos p ON p.animal_id = a.id AND p.is_main = 1
            WHERE 1=1
        """
        params: list[Any] = []
        query, params = AnimalModel._append_filter_sql(query, params, filters)

        query += " ORDER BY a.created_at DESC LIMIT ? OFFSET ?"
        params.append(ITEMS_PER_PAGE)
        params.append(max(page - 1, 0) * ITEMS_PER_PAGE)

        with get_db_cursor() as cursor:
            cursor.execute(query, tuple(params))
            return [dict(row) for row in cursor.fetchall()]

    @staticmethod
    def count_filtered(filters: dict[str, Any]) -> int:
        query = """
            SELECT COUNT(*) as total
            FROM animals a
            JOIN shelters s ON s.id = a.shelter_id
            WHERE 1=1
        """
        params: list[Any] = []
        query, params = AnimalModel._append_filter_sql(query, params, filters)

        with get_db_cursor() as cursor:
            cursor.execute(query, tuple(params))
            row = cursor.fetchone()
            return row["total"] if row else 0

    @staticmethod
    def update_status(animal_id: int, status: str) -> None:
        with get_db_cursor() as cursor:
            cursor.execute("UPDATE animals SET status = ? WHERE id = ?", (status, animal_id))

    @staticmethod
    def list_by_shelter(shelter_id: int) -> list[dict[str, Any]]:
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                SELECT a.*, p.filename as main_photo
                FROM animals a
                LEFT JOIN animal_photos p ON p.animal_id = a.id AND p.is_main = 1
                WHERE a.shelter_id = ?
                ORDER BY a.created_at DESC
                """,
                (shelter_id,),
            )
            return [dict(row) for row in cursor.fetchall()]

    @staticmethod
    def update(animal_id: int, animal_data: dict[str, Any]) -> None:
        search_vector = " ".join(
            [
                animal_data.get("name", ""),
                animal_data.get("species", ""),
                animal_data.get("breed", ""),
                animal_data.get("color", ""),
                animal_data.get("temperament", ""),
                animal_data.get("description", ""),
            ]
        ).lower()
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                UPDATE animals
                SET species = ?, breed = ?, name = ?, age = ?, sex = ?, size = ?, color = ?,
                    health = ?, temperament = ?, compatible_with_children = ?,
                    compatible_with_animals = ?, description = ?, status = ?, search_vector = ?
                WHERE id = ?
                """,
                (
                    animal_data["species"],
                    animal_data.get("breed"),
                    animal_data["name"],
                    animal_data.get("age"),
                    animal_data.get("sex", "unknown"),
                    animal_data.get("size", "medium"),
                    animal_data.get("color"),
                    animal_data.get("health"),
                    animal_data.get("temperament"),
                    int(bool(animal_data.get("compatible_with_children"))),
                    int(bool(animal_data.get("compatible_with_animals"))),
                    animal_data.get("description"),
                    animal_data.get("status", "available"),
                    search_vector,
                    animal_id,
                ),
            )

    @staticmethod
    def delete(animal_id: int) -> None:
        with get_db_cursor() as cursor:
            cursor.execute("DELETE FROM animals WHERE id = ?", (animal_id,))
