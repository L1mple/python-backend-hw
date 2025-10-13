-- Items queries

-- name: CreateItem :one
INSERT INTO items (name, price, deleted)
VALUES (sqlc.arg('name'), sqlc.arg('price')::float8, FALSE)
RETURNING id, name, price::float8 AS price, deleted, created_at;

-- name: GetItem :one
SELECT id, name, price::float8 AS price, deleted, created_at FROM items WHERE id = $1;

-- name: GetItems :many
SELECT id, name, price::float8 AS price, deleted, created_at FROM items
WHERE 
    (sqlc.arg(show_deleted)::boolean = TRUE OR deleted = FALSE)
    AND (sqlc.narg('min_price')::float8 IS NULL OR price >= sqlc.narg('min_price'))
    AND (sqlc.narg('max_price')::float8 IS NULL OR price <= sqlc.narg('max_price'))
ORDER BY id
LIMIT $1 OFFSET $2;

-- name: UpdateItem :one
UPDATE items
SET name = sqlc.arg('name'), price = sqlc.arg('price')::float8
WHERE id = sqlc.arg('id')
RETURNING id, name, price::float8 AS price, deleted, created_at;

-- name: PatchItemName :one
UPDATE items
SET name = sqlc.arg('name')
WHERE id = sqlc.arg('id') AND deleted = FALSE
RETURNING id, name, price::float8 AS price, deleted, created_at;

-- name: PatchItemPrice :one
UPDATE items
SET price = sqlc.arg('price')::float8
WHERE id = sqlc.arg('id') AND deleted = FALSE
RETURNING id, name, price::float8 AS price, deleted, created_at;

-- name: PatchItemBoth :one
UPDATE items
SET name = sqlc.arg('name'), price = sqlc.arg('price')::float8
WHERE id = sqlc.arg('id') AND deleted = FALSE
RETURNING id, name, price::float8 AS price, deleted, created_at;

-- name: DeleteItem :exec
UPDATE items
SET deleted = TRUE
WHERE id = $1;

-- Carts queries

-- name: CreateCart :one
INSERT INTO carts DEFAULT VALUES
RETURNING *;

-- name: GetCart :one
SELECT * FROM carts WHERE id = $1;

-- name: GetCarts :many
SELECT * FROM carts
ORDER BY id
LIMIT $1 OFFSET $2;

-- name: GetCartItems :many
SELECT ci.cart_id, ci.item_id, ci.quantity, i.name, i.price::float8 AS price, i.deleted
FROM cart_items ci
JOIN items i ON ci.item_id = i.id
WHERE ci.cart_id = $1
ORDER BY ci.item_id;

-- name: GetCartItemsForCarts :many
SELECT ci.cart_id, ci.item_id, ci.quantity, i.name, i.price::float8 AS price, i.deleted
FROM cart_items ci
JOIN items i ON ci.item_id = i.id
WHERE ci.cart_id = ANY($1::int[])
ORDER BY ci.cart_id, ci.item_id;

-- name: AddItemToCart :one
INSERT INTO cart_items (cart_id, item_id, quantity)
VALUES ($1, $2, 1)
ON CONFLICT (cart_id, item_id)
DO UPDATE SET quantity = cart_items.quantity + 1
RETURNING *;

-- name: GetCartTotalPrice :one
SELECT COALESCE(SUM(ci.quantity * i.price), 0)::float8 as total
FROM cart_items ci
JOIN items i ON ci.item_id = i.id
WHERE ci.cart_id = $1 AND i.deleted = FALSE;

-- name: GetCartTotalQuantity :one
SELECT COALESCE(SUM(ci.quantity), 0)::int8 as total
FROM cart_items ci
WHERE ci.cart_id = $1;

-- name: GetAllCartsWithStats :many
SELECT 
    c.id,
    COALESCE(SUM(ci.quantity), 0)::int8 as total_quantity,
    COALESCE(SUM(CASE WHEN i.deleted = FALSE THEN ci.quantity * i.price ELSE 0 END), 0)::float8 as total_price
FROM carts c
LEFT JOIN cart_items ci ON c.id = ci.cart_id
LEFT JOIN items i ON ci.item_id = i.id
GROUP BY c.id
HAVING 
    (sqlc.narg('min_price')::float8 IS NULL OR COALESCE(SUM(CASE WHEN i.deleted = FALSE THEN ci.quantity * i.price ELSE 0 END), 0) >= sqlc.narg('min_price'))
    AND (sqlc.narg('max_price')::float8 IS NULL OR COALESCE(SUM(CASE WHEN i.deleted = FALSE THEN ci.quantity * i.price ELSE 0 END), 0) <= sqlc.narg('max_price'))
    AND (sqlc.narg('min_quantity')::int IS NULL OR COALESCE(SUM(ci.quantity), 0) >= sqlc.narg('min_quantity'))
    AND (sqlc.narg('max_quantity')::int IS NULL OR COALESCE(SUM(ci.quantity), 0) <= sqlc.narg('max_quantity'))
ORDER BY c.id
LIMIT $1 OFFSET $2;

