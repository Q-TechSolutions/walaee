-- امتدادات مطلوبة عند تهيئة القاعدة لأول مرة.
CREATE EXTENSION IF NOT EXISTS "pg_trgm";      -- بحث نصّي على الأسماء
CREATE EXTENSION IF NOT EXISTS "btree_gin";    -- فهارس مركّبة على jsonb
