DO
$$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'datastore_ro') THEN
        CREATE ROLE datastore_ro LOGIN PASSWORD 'datastore'
            NOSUPERUSER NOCREATEDB NOCREATEROLE INHERIT;
    ELSE
        ALTER ROLE datastore_ro WITH LOGIN PASSWORD 'datastore'
            NOSUPERUSER NOCREATEDB NOCREATEROLE INHERIT;
    END IF;
END
$$;

SELECT 'CREATE DATABASE datastore OWNER ckan ENCODING ''UTF8'''
WHERE NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = 'datastore') \gexec

GRANT CONNECT ON DATABASE datastore TO datastore_ro;
