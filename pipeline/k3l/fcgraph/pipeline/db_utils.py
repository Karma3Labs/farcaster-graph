from collections.abc import Iterable
from contextlib import contextmanager

import psycopg2.extensions
import psycopg2.extras
from pydantic import BaseModel

from k3l.fcgraph.pipeline.models import psycopg2_context


class EmptyModel(BaseModel):
    """Empty Pydantic model."""


def psycopg2_query[P: BaseModel, R: BaseModel](
    cur: psycopg2.extensions.cursor,
    query: str,
    args: P | None = None,
    model: type[R] | None = None,
) -> Iterable[R]:
    """
    Execute a query on a psycopg2 cursor and optionally map the results to a Pydantic model.

    The method executes the given query, processes the query arguments, and if a
    Pydantic model is provided, yields the rows of the result set as instances of
    this model.

    :param cur: The database cursor to execute the SQL query on.
    :param query: The SQL query to execute.
    :param args: The arguments for parameter substitution in the SQL query.
    :param model: A Pydantic model class to map the resulting rows. If not provided,
        the query is executed without yielding mapped results.
    :return: Rows of the query's result set, with each row converted into the specified Pydantic model.
    """
    if args is None:
        args = EmptyModel()
    import logging

    logging.info(f"{query=}, {args=}")
    cur.execute(query, args.model_dump(context=psycopg2_context))
    if model is None:
        return []
    return (model.model_validate(row, context=psycopg2_context) for row in cur)


@contextmanager
def psycopg2_cursor(
    conn: psycopg2.extensions.connection,
) -> Iterable[psycopg2.extensions.cursor]:
    """Get a cursor for the given connection."""
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        psycopg2.extras.register_uuid(conn_or_curs=cur)
        yield cur
