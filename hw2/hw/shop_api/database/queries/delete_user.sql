-- Удаление пользователя
DELETE FROM users
WHERE id = :user_id
RETURNING id;
