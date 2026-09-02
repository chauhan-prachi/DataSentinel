from __future__ import annotations

import re

import pandas as pd
from django.db import connections


class PostgreSQLConnector:
    
    def __init__(self, database: str = "default"):
        self.database = database

    def _validate_table_name(self, table_name: str) -> None:
        
        if not table_name:
            raise ValueError(
                "table_name is required."
            )

        if not re.match(
            r"^[A-Za-z_][A-Za-z0-9_]*$",
            table_name,
        ):
            raise ValueError(
                f"Invalid table name: {table_name}"
            )

    def table_exists(self, table_name: str) -> bool:
        """Return True if the table exists in the public schema."""

        self._validate_table_name(table_name)

        with connections[self.database].cursor() as cursor:
            cursor.execute(
                """
                SELECT EXISTS (
                    SELECT 1
                    FROM information_schema.tables
                    WHERE table_schema = 'public'
                    AND table_name = %s
                )
                """,
                [table_name],
            )

            return cursor.fetchone()[0]

    def read_table(
        self,
        table_name: str,
    ) -> pd.DataFrame:
        """
        Load an entire PostgreSQL table into a pandas DataFrame.
        """

        self._validate_table_name(table_name)

        if not self.table_exists(table_name):
            raise ValueError(
                f"Table not found: {table_name}"
            )

        query = f'SELECT * FROM "{table_name}"'

        with connections[self.database].cursor() as cursor:
            cursor.execute(query)

            columns = [
                column[0]
                for column in cursor.description
            ]

            rows = cursor.fetchall()

        return pd.DataFrame(
            rows,
            columns=columns,
        )

    def read_query(
        self,
        query: str,
        params: list | tuple | None = None,
    ) -> pd.DataFrame:
        """
        Execute a read-only SQL query and return a DataFrame.
        """

        if not query:
            raise ValueError(
                "query is required."
            )

        with connections[self.database].cursor() as cursor:
            cursor.execute(
                query,
                params or [],
            )

            columns = [
                column[0]
                for column in cursor.description
            ]

            rows = cursor.fetchall()

        return pd.DataFrame(
            rows,
            columns=columns,
        )