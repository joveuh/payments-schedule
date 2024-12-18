import sqlite3


DB_NAME = "payment_schedule.db"
TABLE_NAME = "summary_table"


class DB_Ops:
    def __init__(self, db_name: str = DB_NAME, table_name: str = TABLE_NAME):
        self.db_name = db_name
        self.table_name = table_name
        self.conn = None
        self.cursor = None
        self.init_cursor()

    def get_create_table_command(self) -> str:
        CREATE_TABLE_CMD = f"CREATE TABLE IF NOT EXISTS {self.table_name}(ID INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT NOT NULL, total, balance NOT NULL, CONSTRAINT unique_date UNIQUE(date))"
        return CREATE_TABLE_CMD

    def open_connection(self) -> sqlite3.Connection:
        try:
            self.conn = sqlite3.connect(self.db_name)
            self.cursor = self.conn.cursor()
        except sqlite3.Error as e:
            print(f"Error connecting to database: {e}")
            self.conn = None
            self.cursor = None

    # Use this to open conn then get the cursor right away
    def init_cursor(self) -> sqlite3.Cursor:
        self.open_connection()

    # Use this to close conn
    def close_conn(self):
        if self.cursor:
            self.cursor.close()

    def insert_into_table_default_cmd_with_data(self, data: tuple = None):
        if data == None:
            raise Exception(
                "Method cannot be called with None data.\n Provide valid INSERT INTO date: date, total, balance"
            )
        date, total, balance = data
        INSERT_INTO_TABLE_CMD = f"INSERT OR REPLACE INTO {TABLE_NAME} (date, total, balance) VALUES('{date}', {total}, {balance})"
        return INSERT_INTO_TABLE_CMD

    def create_table(self):
        # create given table in the db if it doesn't exist, else create default table_name in the db
        self.cursor.execute(self.get_create_table_command())

    # they can give you some command, and no data
    # they can give you no command, some data
    # they can give you no command, no data
    # they can give you a command, and data

    def cursor_execute(
        self,
        cmd: str = None,
        data: tuple = None,
    ) -> sqlite3.Cursor:
        # execute given command with data, else execute default INSERT command
        (
            self.cursor.execute(cmd, data)
            if cmd and data
            else (
                self.cursor.execute(cmd)
                if data is None
                else self.cursor.execute(
                    self.insert_into_table_default_cmd_with_data(data)
                )
            )
        )
        self.conn.commit()
        return self.cursor

    def show_db_table(self):
        print("TABLES EXIST: ")
        existing_tables = self.cursor.execute("SELECT name from sqlite_master")
        print(existing_tables.fetchall())

        all_transactions = self.cursor.execute(f"SELECT * FROM {self.table_name}")
        print(all_transactions.fetchall())
