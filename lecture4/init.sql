-- схемы
CREATE TABLE IF NOT EXISTS items (
  id SERIAL PRIMARY KEY,
  name TEXT NOT NULL,
  price NUMERIC(12,2) NOT NULL,
  deleted BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS carts (
  id SERIAL PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS cart_items (
  cart_id INT NOT NULL REFERENCES carts(id) ON DELETE CASCADE,
  item_id INT NOT NULL REFERENCES items(id),
  quantity INT NOT NULL CHECK (quantity > 0),
  PRIMARY KEY (cart_id, item_id)
);

-- начальные данные для скриптов
TRUNCATE cart_items, carts, items RESTART IDENTITY;
INSERT INTO items(name, price, deleted) VALUES ('A', 100, FALSE), ('B', 200, FALSE);

CREATE INDEX IF NOT EXISTS idx_items_price_not_deleted
  ON items(price) WHERE deleted = FALSE;
