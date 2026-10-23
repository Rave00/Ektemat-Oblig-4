-- Ekte Mat Online: SQLite schema (data model in docs/plans/0 - Architecture-and-Skeleton.md, section 4).
-- Only the classes in this folder use it. Every statement is safe to run on an existing database.

CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY,
    email         TEXT    NOT NULL UNIQUE,
    name          TEXT    NOT NULL,
    password_hash TEXT    NOT NULL,
    role          TEXT    NOT NULL CHECK (role IN ('customer', 'admin')),
    created_at    TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS food_items (
    id            INTEGER PRIMARY KEY,
    name          TEXT    NOT NULL,
    description   TEXT    NOT NULL,
    price_nok     INTEGER NOT NULL CHECK (price_nok >= 0),
    min_order_qty INTEGER NOT NULL CHECK (min_order_qty >= 1),
    image_path    TEXT,
    no_allergens  INTEGER NOT NULL DEFAULT 0 CHECK (no_allergens IN (0, 1)),   -- plan 1, P1-2
    published     INTEGER NOT NULL DEFAULT 0 CHECK (published IN (0, 1)),
    created_at    TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS food_item_events (
    food_item_id INTEGER NOT NULL REFERENCES food_items(id) ON DELETE CASCADE,
    event        TEXT    NOT NULL,
    PRIMARY KEY (food_item_id, event)
);

CREATE TABLE IF NOT EXISTS food_item_allergens (
    food_item_id INTEGER NOT NULL REFERENCES food_items(id) ON DELETE CASCADE,
    allergen     TEXT    NOT NULL,
    PRIMARY KEY (food_item_id, allergen)
);

CREATE TABLE IF NOT EXISTS food_item_labels (
    food_item_id INTEGER NOT NULL REFERENCES food_items(id) ON DELETE CASCADE,
    label        TEXT    NOT NULL,
    PRIMARY KEY (food_item_id, label)
);

CREATE TABLE IF NOT EXISTS orders (
    id                INTEGER PRIMARY KEY,
    customer_id       INTEGER NOT NULL REFERENCES users(id),
    event_type        TEXT    NOT NULL,                                          -- V4
    event_date        TEXT    NOT NULL,                                          -- YYYY-MM-DD
    guest_count       INTEGER NOT NULL CHECK (guest_count > 0 AND guest_count <= 400),   -- V5, V6
    delivery_street   TEXT    NOT NULL,
    delivery_postcode TEXT    NOT NULL
                      CHECK (length(delivery_postcode) = 4 AND delivery_postcode NOT GLOB '*[^0-9]*'),  -- V10
    delivery_city     TEXT    NOT NULL,
    status            TEXT    NOT NULL DEFAULT 'submitted'
                      CHECK (status IN ('submitted', 'approved', 'in_preparation', 'delivered', 'rejected', 'cancelled')),
    payment_status    TEXT    NOT NULL DEFAULT 'not_paid'
                      CHECK (payment_status IN ('not_paid', 'deposit_paid', 'invoiced', 'paid')),
    submitted_at      TEXT    NOT NULL,                                          -- YYYY-MM-DD HH:MM:SS
    submission_key    TEXT    NOT NULL UNIQUE,                                   -- one order per click (plan 3; V1)
    status_reason     TEXT,                                                      -- plan 4, P4-2
    first_replied_at  TEXT                                                       -- plan 4, P4-3 (NFR-19)
);

CREATE TABLE IF NOT EXISTS order_lines (
    id             INTEGER PRIMARY KEY,
    order_id       INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    food_item_id   INTEGER NOT NULL REFERENCES food_items(id),
    quantity       INTEGER NOT NULL CHECK (quantity > 0),
    unit_price_nok INTEGER NOT NULL CHECK (unit_price_nok >= 0)
);

CREATE TABLE IF NOT EXISTS guest_groups (
    id            INTEGER PRIMARY KEY,
    order_id      INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    description   TEXT    NOT NULL,
    size          INTEGER NOT NULL CHECK (size > 0),
    allergy_notes TEXT,
    diet_notes    TEXT
);

CREATE TABLE IF NOT EXISTS questions (
    id          INTEGER PRIMARY KEY,
    order_id    INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    customer_id INTEGER NOT NULL REFERENCES users(id),
    text        TEXT    NOT NULL,
    asked_at    TEXT    NOT NULL DEFAULT (datetime('now')),
    answer      TEXT,
    answered_at TEXT,
    answered_by INTEGER REFERENCES users(id)
);
