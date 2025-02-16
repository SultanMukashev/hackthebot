import psycopg2
from decouple import config

class DBHandler:
    def __init__(self):
        self.conn = psycopg2.connect(
            dbname=config("DB_NAME", default="water_bot"),
            user=config("DB_USER", default="postgres"),
            password=config("DB_PASSWORD", default="postgres"),
            host=config("DB_HOST", default="localhost"),
            port=config("DB_PORT", default="5432"),
        )
        self.cursor = self.conn.cursor()

    def execute_query(self, query, params=None, fetch_one=False, fetch_all=False, commit=False):
        """Execute a general SQL query."""
        try:
            self.cursor.execute(query, params or ())
            if commit:
                self.conn.commit()
            if fetch_one:
                return self.cursor.fetchone()
            if fetch_all:
                return self.cursor.fetchall()
        except Exception as e:
            self.conn.rollback()
            print(f"❌ Error executing query: {e}")
            return None

    def call_function(self, function_name, params):
        """Call a stored SQL function."""
        try:
            query = f"SELECT {function_name}({', '.join(['%s'] * len(params))})"
            self.cursor.execute(query, params)
            result = self.cursor.fetchone()
            if result:
                return result[0]  # Assuming function returns a single value
        except Exception as e:
            self.conn.rollback()
            print(f"❌ Error calling function {function_name}: {e}")
            return None

    def insert(self, table, data):
        """Insert data into a given table."""
        columns = ", ".join(data.keys())
        values_placeholders = ", ".join(["%s"] * len(data))
        query = f"INSERT INTO {table} ({columns}) VALUES ({values_placeholders}) RETURNING *"
        return self.execute_query(query, tuple(data.values()), fetch_one=True, commit=True)

    def update(self, table, data, condition):
        """Update a row in a given table."""
        set_clause = ", ".join([f"{key} = %s" for key in data.keys()])
        condition_clause = " AND ".join([f"{key} = %s" for key in condition.keys()])
        query = f"UPDATE {table} SET {set_clause} WHERE {condition_clause} RETURNING *"
        return self.execute_query(query, tuple(data.values()) + tuple(condition.values()), fetch_one=True, commit=True)

    def fetch_one(self, table, condition):
        """Fetch a single row from a table."""
        condition_clause = " AND ".join([f"{key} = %s" for key in condition.keys()])
        query = f"SELECT * FROM {table} WHERE {condition_clause} LIMIT 1"
        return self.execute_query(query, tuple(condition.values()), fetch_one=True)

    def fetch_all(self, table, condition=None):
        """Fetch all rows from a table (with optional condition)."""
        query = f"SELECT * FROM {table}"
        if condition:
            condition_clause = " AND ".join([f"{key} = %s" for key in condition.keys()])
            query += f" WHERE {condition_clause}"
        return self.execute_query(query, tuple(condition.values()) if condition else (), fetch_all=True)

    def fetch_column(self, table,column, condition=None):
        """Fetch all rows from a table (with optional condition)."""
        query = f"SELECT {column} FROM {table}"
        if condition:
            condition_clause = " AND ".join([f"{key} = %s" for key in condition.keys()])
            query += f" WHERE {condition_clause}"
        return self.execute_query(query, tuple(condition.values()) if condition else (), fetch_all=True)

    def close(self):
        """Close the database connection."""
        self.cursor.close()
        self.conn.close()
