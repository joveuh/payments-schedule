import sqlite3

DB_NAME = "payment_schedule.db"
TABLE_NAME = "summary_table"


class DB_Ops:
    def __init__(self, db_name: str = DB_NAME, table_name: str = TABLE_NAME):
        # Table names can't be bound as parameters, so this name is interpolated
        # into the SQL below; reject anything that isn't a bare identifier.
        if not table_name.isidentifier():
            raise ValueError(f"invalid table name: {table_name!r}")
        self.table_name = table_name
        self.conn = sqlite3.connect(db_name)

    def create_table(self) -> None:
        self.conn.execute(
            f"CREATE TABLE IF NOT EXISTS {self.table_name}("
            "ID INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT NOT NULL, "
            "total REAL NOT NULL, balance REAL NOT NULL, "
            "CONSTRAINT unique_date UNIQUE(date))"
        )
        self.conn.commit()

    def insert_many(self, rows: list[tuple[str, float, float]]) -> None:
        """rows: (date, total, balance). An existing date is replaced."""
        self.conn.executemany(
            f"INSERT OR REPLACE INTO {self.table_name} (date, total, balance)"
            " VALUES (?, ?, ?)",
            rows,
        )
        self.conn.commit()

    def all_rows(self) -> list[tuple]:
        return self.conn.execute(f"SELECT * FROM {self.table_name}").fetchall()

    def close(self) -> None:
        self.conn.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
