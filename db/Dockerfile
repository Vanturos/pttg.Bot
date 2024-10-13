FROM postgres:15.8

ENV POSTGRES_USER=user \
    POSTGRES_PASSWORD=password \
    POSTGRES_DB=db_tg_bot \
    POSTGRES_CONFIG="log_replication_commands = on" \
    POSTGRES_INITDB_ARGS="--auth-host=scram-sha-256" \
    POSTGRES_HOST_AUTH_METHOD=scram-sha-256

COPY ./init.sql /docker-entrypoint-initdb.d/init.sql

RUN mkdir -p /var/log/postgresql
RUN touch /var/log/postgresql/postgresql-15-main.log
RUN chown -R postgres:postgres /var
RUN chmod -R 777 /var/log/postgresql
