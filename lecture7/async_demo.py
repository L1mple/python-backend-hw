import asyncio
import time
from types import coroutine


async def fetch_user(user_id: int) -> dict:
    print(f"[{time.time():.2f}] 🔵 fetch_user({user_id}): начало")

    await asyncio.sleep(2)  # Имитация I/O операции (запрос к БД)

    print(f"[{time.time():.2f}] 🔵 fetch_user({user_id}): завершено")
    return {"id": user_id, "name": f"User {user_id}"}


async def fetch_orders(user_id: int) -> list:
    print(f"[{time.time():.2f}] 🟢 fetch_orders({user_id}): начало")

    await asyncio.sleep(1.5)  # Имитация I/O операции

    print(f"[{time.time():.2f}] 🟢 fetch_orders({user_id}): завершено")
    return [{"order_id": 1}, {"order_id": 2}]


async def send_email(user_id: int) -> None:
    print(f"[{time.time():.2f}] 🟡 send_email({user_id}): начало")

    await asyncio.sleep(1)  # Имитация I/O операции

    print(f"[{time.time():.2f}] 🟡 send_email({user_id}): завершено")


async def process_user(user_id: int) -> None:
    print(f"[{time.time():.2f}] process_user({user_id}): СТАРТ")

    user = await fetch_user(user_id)
    print(f"[{time.time():.2f}] Получен user: {user}")

    orders = await fetch_orders(user_id)
    print(f"[{time.time():.2f}] Получены orders: {orders}")

    await send_email(user_id)
    print(f"[{time.time():.2f}] Email отправлен")

    print(f"[{time.time():.2f}] process_user({user_id}): КОНЕЦ")


async def main_sequential():
    start = time.time()

    await process_user(1)
    await process_user(2)

    elapsed = time.time() - start
    print(f"Время выполнения: {elapsed:.2f} секунд")


async def main_concurrent():
    start = time.time()

    task1 = asyncio.create_task(process_user(1))
    task2 = asyncio.create_task(process_user(2))

    await task1
    await task2

    elapsed = time.time() - start
    print(f"Время выполнения: {elapsed:.2f} секунд")


async def main_gather():
    start = time.time()

    await asyncio.gather(
        process_user(1),
        process_user(2),
        process_user(3),
    )

    elapsed = time.time() - start
    print(f"Время выполнения: {elapsed:.2f} секунд")


async def demonstrate_event_loop_switching():
    async def task(name: str, sleep_time: float):
        for i in range(3):
            print(f"[{time.time():.2f}] {name}: шаг {i+1}")
            await asyncio.sleep(sleep_time)  # Точка переключения
        print(f"[{time.time():.2f}] {name}: ЗАВЕРШЕНО")

    await asyncio.gather(
        task("Задача A", 0.5),
        task("Задача B", 0.7),
        task("Задача C", 0.3),
    )


async def demonstrate_fire_and_forget_problem():

    async def background_task(task_id: int):
        print(f"Фоновая задача {task_id}: начало")
        await asyncio.sleep(1)
        print(f"Фоновая задача {task_id}: завершена")

    # Создаем задачу но НЕ ждем её завершения
    asyncio.create_task(background_task(1))
    asyncio.create_task(background_task(2))

    await asyncio.sleep(0)

    print("Основная функция завершается")

    tasks = [
        asyncio.create_task(background_task(3)),
        asyncio.create_task(background_task(4)),
    ]

    await asyncio.gather(*tasks)


if __name__ == "__main__":
    pass

    # 1. Последовательное выполнение
    # asyncio.run(main_sequential())

    # 2. Конкурентное выполнение
    # asyncio.run(main_concurrent())

    # # 3. Gather для множества задач
    # asyncio.run(main_gather())

    # # 4. Демонстрация переключения
    # asyncio.run(demonstrate_event_loop_switching())

    # # 5. Проблема: fire-and-forget
    asyncio.run(demonstrate_fire_and_forget_problem())
