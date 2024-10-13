CREATE USER replication_user WITH REPLICATION ENCRYPTED PASSWORD '3175' LOGIN;

CREATE TABLE emails (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL
);

CREATE TABLE phones (
    id SERIAL PRIMARY KEY,
    phone VARCHAR(255) NOT NULL
);

INSERT INTO emails (email) VALUES ('testik@mali.com'), ('te22ak@kekw.com');
INSERT INTO phones (phone) VALUES ('+7(937)222-22-22'), ('8-111-111-11-11');

CREATE TABLE hba ( lines text );
COPY hba FROM '/var/lib/postgresql/data/pg_hba.conf';
INSERT INTO hba (lines) VALUES ('host replication all 0.0.0.0/0 md5');
COPY hba TO '/var/lib/postgresql/data/pg_hba.conf';
SELECT pg_reload_conf();

SELECT * FROM pg_create_physical_replication_slot('replication_slot');
