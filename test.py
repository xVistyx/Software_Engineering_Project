import sqlite3
from pathlib import Path


DB_PATH = Path("DataBase/grove.sqlite3")


def print_table(cursor, table_name):
    print(f"\n--- {table_name.upper()} ---")

    try:
        rows = cursor.execute(
            f"SELECT * FROM {table_name}"
        ).fetchall()

        if not rows:
            print("No rows found.")
            return

        for row in rows:
            print(dict(row))

    except sqlite3.Error as error:
        print(f"Error reading {table_name}: {error}")


def main():
    if not DB_PATH.exists():
        print("Database not found:", DB_PATH.resolve())
        return

    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row

    cursor = connection.cursor()

    print("Connected to:")
    print(DB_PATH.resolve())

    print_table(cursor, "users")
    print_table(cursor, "access_keys")
    print_table(cursor, "sessions")

    connection.close()


if __name__ == "__main__":
    main()