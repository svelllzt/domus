from passlib.context import CryptContext

from config import GLOBAL_ADMIN_EMAIL, GLOBAL_ADMIN_PASSWORD
from database import run_migrations
from database import get_db_cursor
from models.animal import AnimalModel
from models.favorite import FavoriteModel
from models.shelter import ShelterModel
from models.user import UserModel


password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def seed() -> None:
    run_migrations()
    admin = UserModel.get_by_email(GLOBAL_ADMIN_EMAIL)
    if not admin:
        UserModel.create(
            email=GLOBAL_ADMIN_EMAIL,
            password_hash=password_context.hash(GLOBAL_ADMIN_PASSWORD),
            name="Глобальный администратор",
            role="global_admin",
        )
        admin = UserModel.get_by_email(GLOBAL_ADMIN_EMAIL)

    if admin:
        UserModel.update_password(admin["id"], password_context.hash(GLOBAL_ADMIN_PASSWORD))
        with get_db_cursor() as cursor:
            cursor.execute(
                "UPDATE users SET role = 'global_admin', shelter_id = NULL, is_verified = 1 WHERE id = ?",
                (admin["id"],),
            )
            cursor.execute(
                "DELETE FROM users WHERE role = 'global_admin' AND email != ?",
                (GLOBAL_ADMIN_EMAIL,),
            )
        UserModel.verify_email(admin["id"])
    print("В системе оставлен единственный global admin из конфига.")


def clear_demo_data() -> None:
    run_migrations()
    with get_db_cursor() as cursor:
        cursor.execute("DELETE FROM adoption_applications")
        cursor.execute("DELETE FROM favorites")
        cursor.execute("DELETE FROM animal_photos")
        cursor.execute("DELETE FROM animals")
        cursor.execute("DELETE FROM shelter_registration_requests")
        cursor.execute("DELETE FROM shelters")
        cursor.execute("DELETE FROM verification_tokens")
        cursor.execute(
            "DELETE FROM users WHERE role != 'global_admin' OR email != ?",
            (GLOBAL_ADMIN_EMAIL,),
        )
        cursor.execute(
            """
            UPDATE users
            SET role = 'global_admin', shelter_id = NULL, is_verified = 1
            WHERE email = ?
            """,
            (GLOBAL_ADMIN_EMAIL,),
        )
    print("Демо-данные очищены. Оставлен только global admin.")


def seed_test_data() -> None:
    run_migrations()
    clear_demo_data()

    shelter_id = ShelterModel.create(
        name="[TEST] Теплый дом",
        city="Москва",
        address="ул. Пример, 1",
        phone="+7 900 000-00-00",
        description="Тестовый приют для локальной разработки.",
        is_approved=1,
    )

    test_user = UserModel.get_by_email("test-user@example.com")
    if not test_user:
        user_id = UserModel.create(
            email="test-user@example.com",
            password_hash=password_context.hash("test12345"),
            name="[TEST] Пользователь",
            role="user",
        )
        UserModel.verify_email(user_id)
    else:
        user_id = test_user["id"]

    test_staff = UserModel.get_by_email("test-staff@example.com")
    if not test_staff:
        staff_id = UserModel.create(
            email="test-staff@example.com",
            password_hash=password_context.hash("test12345"),
            name="[TEST] Сотрудник",
            role="shelter_staff",
        )
    else:
        staff_id = test_staff["id"]
    UserModel.verify_email(staff_id)

    animals = [
        {
            "species": "dog",
            "breed": "Метис",
            "name": "[TEST] Барни",
            "age": 3,
            "sex": "male",
            "size": "medium",
            "color": "рыжий",
            "health": "здоров",
            "temperament": "спокойный",
            "description": "Тестовая анкета собаки.",
            "compatible_with_children": True,
            "compatible_with_animals": True,
            "status": "available",
            "shelter_id": shelter_id,
        },
        {
            "species": "cat",
            "breed": "Метис",
            "name": "[TEST] Мия",
            "age": 2,
            "sex": "female",
            "size": "small",
            "color": "серый",
            "health": "здоров",
            "temperament": "ласковая",
            "description": "Тестовая анкета кошки.",
            "compatible_with_children": True,
            "compatible_with_animals": True,
            "status": "available",
            "shelter_id": shelter_id,
        },
    ]

    created_ids: list[int] = []
    for item in animals:
        animal_id = AnimalModel.create(item)
        created_ids.append(animal_id)
        AnimalModel.add_photo(animal_id, "placeholder.svg", is_main=True)

    if created_ids:
        FavoriteModel.add(user_id, created_ids[0])

    print("Тестовые данные добавлены.")
    print("Логин тест-пользователя: test-user@example.com")
    print("Пароль тест-пользователя: test12345")
    print("Логин тест-стаффа: test-staff@example.com")
    print("Пароль тест-стаффа: test12345")


if __name__ == "__main__":
    seed()
