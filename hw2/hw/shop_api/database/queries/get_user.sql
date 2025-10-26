-- Получение пользователя по ID
SELECT id, email, name, age, created_at
FROM users
WHERE id = :user_id;
