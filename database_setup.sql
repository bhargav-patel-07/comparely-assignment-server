-- DDL for PostgreSQL Setup (database_setup.sql)

-- 1. Areas Table
CREATE TABLE IF NOT EXISTS areas (
    area_code VARCHAR(10) PRIMARY KEY,
    area_name VARCHAR(100) NOT NULL
);

-- 2. Stores Table (Links stores to areas)
CREATE TABLE IF NOT EXISTS stores (
    store_id VARCHAR(50) PRIMARY KEY,
    area_code VARCHAR(10) NOT NULL,
    store_name VARCHAR(100),
    FOREIGN KEY (area_code) REFERENCES areas(area_code)
);

-- 3. Stock History Table (Fact Table - stores the scraped data + calculated metrics)
CREATE TABLE IF NOT EXISTS stock_history (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    store_id VARCHAR(50) NOT NULL,
    product_name VARCHAR(100) NOT NULL,
    stock_status VARCHAR(20) NOT NULL,
    stock_count INTEGER NOT NULL,
    price NUMERIC(10, 2) NOT NULL,
    -- Calculated Fields (The 'T' in ETL)
    days_of_inventory NUMERIC(10, 2),
    is_oos_alert BOOLEAN NOT NULL DEFAULT FALSE,
    FOREIGN KEY (store_id) REFERENCES stores(store_id)
);

-- Initial Data Load
INSERT INTO areas (area_code, area_name) VALUES
('400001', 'Mumbai - Fort'),
('201301', 'Noida - Sector 62')
ON CONFLICT (area_code) DO NOTHING;

INSERT INTO stores (store_id, area_code, store_name) VALUES
('BLK_MUM_101', '400001', 'QuickStore 101'),
('BLK_MUM_102', '400001', 'QuickStore 102'),
('BLK_NOI_201', '201301', 'QuickStore 201'),
('BLK_NOI_202', '201301', 'QuickStore 202'),
('BLK_NOI_203', '201301', 'QuickStore 203')
ON CONFLICT (store_id) DO NOTHING;