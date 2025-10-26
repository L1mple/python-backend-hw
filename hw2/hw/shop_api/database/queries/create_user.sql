-- Создание пользователя
INSERT INTO users (email, name, age)
VALUES (:email, :name, :age)
RETURNING id, email, name, age, created_at;
