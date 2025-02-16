import psycopg2
# Database setup
def init_db():
    conn = psycopg2.connect(
        host="localhost",
        database="water_bot",
        user="postgres",
        password="postgres"
    )
#     conn = psycopg2.connect(
#     "dbname=water_bot user=sultan password=sultan host=localhost port=5432",
#     client_encoding="UTF8"
# )

    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS households (
                      id SERIAL PRIMARY KEY ,
                      address TEXT UNIQUE,
                      longitude DOUBLE PRECISION,
                      latitude DOUBLE PRECISION,
                      bottle_balance INTEGER DEFAULT 5)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS bottle_points (
                      point_id SERIAL PRIMARY KEY ,
                      address TEXT UNIQUE,
                      longitude DOUBLE PRECISION,
                      latitude DOUBLE PRECISION,
                      bottle_amount INTEGER DEFAULT 0)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                      id SERIAL PRIMARY KEY ,
                      iin BIGINT UNIQUE,
                      name TEXT,
                      phone TEXT UNIQUE,
                      tg_id BIGINT,
                      bonus_amount INT,
                      household_id INTEGER,
                      verified INTEGER DEFAULT 0,
                      timestamp TIMESTAMP DEFAULT NOW(),
                      nearest_point TEXT,
                      n_longitude DOUBLE PRECISION,
                      n_latitude DOUBLE PRECISION,
                      FOREIGN KEY(household_id) REFERENCES households(id) ON DELETE SET NULL)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS transactions (
                      id SERIAL PRIMARY KEY ,
                      household_id INTEGER,
                      bottles_charged INTEGER,
                      timestamp TIMESTAMP DEFAULT NOW(),
                      point_id INTEGER,
                      FOREIGN KEY(point_id) REFERENCES bottle_points(point_id) ON DELETE CASCADE,
                      FOREIGN KEY(household_id) REFERENCES households(id) ON DELETE CASCADE)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS bonuses (
                      bonus_id SERIAL PRIMARY KEY ,
                      bonus_type TEXT UNIQUE,
                      amount INTEGER DEFAULT 0)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS Employees (
                      employee_id BIGINT PRIMARY KEY ,
                      name TEXT,
                      phone_number BIGINT,
                      employed_date TIMESTAMP)''')
    cursor.execute('''create table if not exists emp_work(
                      employee_id BIGINT PRIMARY KEY REFERENCES employees(employee_id) ON DELETE CASCADE,
                      bottle_per_month INT DEFAULT 0,
                      month_year TIMESTAMP)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS admins (
                      admin_id BIGINT PRIMARY KEY ,
                      name TEXT)''')

    conn.commit()
    conn.close()

init_db()