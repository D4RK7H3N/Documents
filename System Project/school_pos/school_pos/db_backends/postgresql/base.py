from django.db.backends.postgresql.base import DatabaseWrapper as PostgresDatabaseWrapper

import time


class DatabaseWrapper(PostgresDatabaseWrapper):
    """Retry only the TCP/auth handshake, never a query or a write.

    The Windows host intermittently drops new PostgreSQL connections with
    "server closed the connection unexpectedly". Without a timeout a worker
    thread waits long enough for all Waitress threads to queue up, which
    surfaces as 502 / canceled pages. Retrying connection *creation* is safe:
    no SQL has run yet, so a payment can never be duplicated.
    """

    CONNECT_ATTEMPTS = 3

    def get_new_connection(self, conn_params):
        last_error = None
        for attempt in range(self.CONNECT_ATTEMPTS):
            try:
                return super().get_new_connection(conn_params)
            except Exception as error:
                last_error = error
                if attempt + 1 < self.CONNECT_ATTEMPTS:
                    time.sleep(0.25 * (attempt + 1))
        raise last_error
