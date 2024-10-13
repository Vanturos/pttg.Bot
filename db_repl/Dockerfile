FROM postgres:15.8

ENV POSTGRES_USER=replication_user \
    POSTGRES_PASSWORD=replication_user_password \
    POSTGRES_DB=postgres \
    POSTGRES_HOST=db_image \
    PG_PORT=5432 \
    DATA_DIR_PERM=0700

RUN mkdir -p /var/log/postgresql && \
    touch /var/log/postgresql/postgresql-15-main.log && \
    chown -R postgres:postgres /var && \
    chmod -R 755 /var/log/postgresql

RUN echo '#!/bin/bash\n\
\n\
rm -rf /var/lib/postgresql/data/*\n\
\n\
until PGPASSWORD=$POSTGRES_PASSWORD pg_basebackup --pgdata=/var/lib/postgresql/data -R --slot=replication_slot --username=$POSTGRES_USER --host=$POSTGRES_HOST --port=$PG_PORT; do\n\
  echo "Waiting for primary to connect..."\n\
  sleep 1s\n\
done\n\
\n\
psql -h $POSTGRES_HOST -U $POSTGRES_USER -d $POSTGRES_DB -c "SELECT * FROM pg_create_physical_replication_slot('replication_slot');"\n\
\n\
echo "Backup done, starting replica..."\n\
chmod $DATA_DIR_PERM /var/lib/postgresql/data\n\
exec postgres' > /init.sh && \
    chmod +x /init.sh

USER postgres

CMD ["/init.sh"]
