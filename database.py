import sqlite3
from contextlib import contextmanager
from pathlib import Path

from config import DATABASE_PATH, UPLOADS_DIR


def get_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON;")
    return connection


@contextmanager
def get_db_cursor():
    connection = get_connection()
    try:
        cursor = connection.cursor()
        yield cursor
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def run_migrations() -> None:
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    Path(DATABASE_PATH).parent.mkdir(parents=True, exist_ok=True)

    with get_db_cursor() as cursor:
        cursor.executescript(
            """
            CREATE TABLE IF NOT EXISTS shelters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                city TEXT,
                address TEXT,
                phone TEXT,
                description TEXT,
                is_approved INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT CHECK(role IN ('user', 'shelter_admin', 'shelter_staff', 'global_admin')) DEFAULT 'user',
                name TEXT,
                shelter_id INTEGER REFERENCES shelters(id) ON DELETE SET NULL,
                is_verified INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS shelter_registration_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                shelter_name TEXT NOT NULL,
                shelter_city TEXT,
                shelter_address TEXT,
                shelter_phone TEXT,
                shelter_description TEXT,
                applicant_position TEXT,
                comment TEXT,
                status TEXT CHECK(status IN ('new', 'approved', 'rejected')) DEFAULT 'new',
                admin_comment TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS animals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                species TEXT NOT NULL,
                breed TEXT,
                name TEXT NOT NULL,
                age INTEGER,
                sex TEXT CHECK(sex IN ('male', 'female', 'unknown')) DEFAULT 'unknown',
                size TEXT CHECK(size IN ('small', 'medium', 'large')) DEFAULT 'medium',
                color TEXT,
                health TEXT,
                temperament TEXT,
                compatible_with_children INTEGER DEFAULT 0,
                compatible_with_animals INTEGER DEFAULT 0,
                description TEXT,
                status TEXT CHECK(status IN ('available', 'processing', 'adopted')) DEFAULT 'available',
                shelter_id INTEGER NOT NULL REFERENCES shelters(id) ON DELETE CASCADE,
                search_vector TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS animal_photos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                animal_id INTEGER NOT NULL REFERENCES animals(id) ON DELETE CASCADE,
                filename TEXT NOT NULL,
                is_main INTEGER DEFAULT 0,
                uploaded_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS favorites (
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                animal_id INTEGER NOT NULL REFERENCES animals(id) ON DELETE CASCADE,
                added_at TEXT DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, animal_id)
            );

            CREATE TABLE IF NOT EXISTS adoption_applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                animal_id INTEGER NOT NULL REFERENCES animals(id) ON DELETE CASCADE,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                applicant_name TEXT NOT NULL,
                applicant_phone TEXT NOT NULL,
                comment TEXT,
                status TEXT CHECK(status IN ('new', 'processing', 'rejected', 'adopted')) DEFAULT 'new',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS verification_tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                token TEXT NOT NULL,
                type TEXT CHECK(type IN ('email_verify', 'password_reset')) NOT NULL,
                expires_at TEXT NOT NULL,
                is_used INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS system_settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            """
        )

        cursor.executescript(
            """
            CREATE INDEX IF NOT EXISTS idx_animals_filters ON animals(species, sex, size, status, shelter_id);
            CREATE INDEX IF NOT EXISTS idx_animals_search_vector ON animals(search_vector);
            CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
            CREATE INDEX IF NOT EXISTS idx_applications_animal_status ON adoption_applications(animal_id, status);
            CREATE INDEX IF NOT EXISTS idx_shelter_requests_status ON shelter_registration_requests(status);
            """
        )

        cursor.execute("UPDATE users SET is_verified = 1 WHERE role = 'global_admin'")

