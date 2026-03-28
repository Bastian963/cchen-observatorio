-- DSpace requires gen_random_uuid() during Flyway migrations.
CREATE EXTENSION IF NOT EXISTS pgcrypto;
