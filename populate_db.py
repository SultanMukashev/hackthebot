import psycopg2
import random
import faker
from datetime import datetime

# Initialize Faker for realistic data
fake = faker.Faker()

# Latitude & Longitude Boundaries
LAT_MIN, LAT_MAX = 43.178644, 43.365625
LON_MIN, LON_MAX = 76.594621, 77.086588

# PostgreSQL Connection
DB_CONFIG = {
    "dbname": "water_bot",
    "user": "postgres",
    "password": "postgres",
    "host": "localhost",  # Change if hosted elsewhere
    "port": "5432"
}

conn = psycopg2.connect(**DB_CONFIG)
cursor = conn.cursor()

# Generate random coordinates
def random_coordinates():
    lat = random.uniform(LAT_MIN, LAT_MAX)
    lon = random.uniform(LON_MIN, LON_MAX)
    return lat, lon

# Generate random households
def generate_households(n=200):
    households = []
    for _ in range(n):
        address = fake.address().replace("\n", ", ")
        lat, lon = random_coordinates()
        households.append((address, lon, lat, random.randint(1, 20)))
    cursor.executemany("""
        INSERT INTO households (address, longitude, latitude, bottle_balance) 
        VALUES (%s, %s, %s, %s)
    """, households)
    conn.commit()
    return households

# Generate bottle collection points
def generate_bottle_points(n=15):
    points = []
    for _ in range(n):
        address = fake.address().replace("\n", ", ")
        lat, lon = random_coordinates()
        points.append((address, lon, lat, random.randint(10, 100)))
    cursor.executemany("""
        INSERT INTO bottle_points (address, longitude, latitude, bottle_amount) 
        VALUES (%s, %s, %s, %s)
    """, points)
    conn.commit()
    return points

# Generate random users linked to households
def generate_users(n=1000):
    users = []
    for _ in range(n):
        household_id = random.randint(1, 200)
        iin = random.randint(100000000000, 999999999999)  # Fake IIN
        name = fake.name()
        phone = fake.phone_number()
        bonus_amount = random.randint(0, 500)
        n_lat, n_lon = random_coordinates()
        users.append((iin, name, phone, bonus_amount, household_id, 1, n_lon, n_lat))
    cursor.executemany("""
        INSERT INTO users (iin, name, phone, bonus_amount, household_id, verified, n_longitude, n_latitude) 
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """, users)
    conn.commit()
    return users

# Generate transactions using the transfer_bottles function
def generate_transactions(n=100):
    for _ in range(n):
        household_id = random.randint(1, 200)
        point_id = random.randint(1, 15)
        bottles_charged = random.randint(1, 5)

        try:
            cursor.execute("SELECT transfer_bottles(%s, %s, %s)", (household_id, point_id, bottles_charged))
            result = cursor.fetchone()[0]  # Get function return message
            print(result)

            if "✅" in result:  # If transaction is successful, commit
                conn.commit()
            else:
                conn.rollback()  # Rollback if failed (bottles not enough)

        except Exception as e:
            conn.rollback()  # Rollback in case of unexpected errors
            print(f"❌ Unexpected error: {e}")

    print("✅ Transactions processing complete.")

# Generate bonuses
def generate_bonuses():
    bonuses = [("Referral", 50), ("First Order", 100), ("Loyalty", 200)]
    cursor.executemany("""
        INSERT INTO bonuses (bonus_type, amount) 
        VALUES (%s, %s)
    """, bonuses)
    conn.commit()

# Generate employees
def generate_employees(n=15):
    employees = []
    emp_works = []
    for _ in range(n):
        id = random.randint(100000,99999999)
        name = fake.name()
        bottle_per_month = random.randint(10, 50)
        month_year = fake.date_this_year().strftime("%Y-%m") + "-01" 
        employed_date = fake.date_this_decade().strftime("%Y-%m-%d")
        phone_number = fake.phone_number()
        employees.append((id, name,employed_date,phone_number))
        emp_works.append((id, bottle_per_month, month_year))
    cursor.executemany("""
        INSERT INTO Employees (employee_id, name, employed_date, phone_number)) 
        VALUES (%s, %s, %s)
    """, employees)
    cursor.executemany("""
        INSERT INTO Emp_works (employee_id, bottle_per_month, month_year) VALUES (%s, %s, %s)
    """, employees)
    conn.commit()

# Generate admins
def generate_admins(n=5):
    admins = [(fake.name(),) for _ in range(n)]
    cursor.executemany("""
        INSERT INTO admins (name) 
        VALUES (%s)
    """, admins)
    conn.commit()

# Run data generation
households = generate_households()
bottle_points = generate_bottle_points()
users = generate_users()
generate_transactions()  # Uses function transfer_bottles()
generate_bonuses()
generate_employees()
generate_admins()

print("✅ PostgreSQL synthetic data generation complete!")

cursor.close()
conn.close()
