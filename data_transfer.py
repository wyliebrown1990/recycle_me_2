import psycopg2

# Database connection parameters
HOST = 'localhost'
DBNAME = 'recycling'
USER = 'wyliebrown'  # replace with your PostgreSQL username
PASSWORD = 'test123'  # replace with your PostgreSQL password

def get_db_connection():
    return psycopg2.connect(host=HOST, dbname=DBNAME, user=USER, password=PASSWORD)

def insert_data(file_path):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    with open(file_path, 'r') as file:
        for line in file:
            line = line.strip()
            if line:
                parts = line.split(':')
                if len(parts) == 3:
                    location, material, items = parts
                    location = location.strip()
                    material = material.strip()
                    items = [item.strip() for item in items.split(',')]
                    
                    # Ensure location exists in the database or insert it
                    cursor.execute("INSERT INTO locations (name) VALUES (%s) ON CONFLICT (name) DO NOTHING", (location,))
                    cursor.execute("SELECT id FROM locations WHERE name = %s", (location,))
                    location_id = cursor.fetchone()[0]

                    # Ensure material exists in the database or insert it
                    cursor.execute("INSERT INTO materials (name) VALUES (%s) ON CONFLICT (name) DO NOTHING", (material,))
                    cursor.execute("SELECT id FROM materials WHERE name = %s", (material,))
                    material_id = cursor.fetchone()[0]
                    
                    # Insert items
                    for item in items:
                        cursor.execute("INSERT INTO items (name, material_id, location_id) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING", (item, material_id, location_id))

    conn.commit()  # Commit all transactions
    cursor.close()
    conn.close()

if __name__ == '__main__':
    insert_data('/Users/wyliebrown/recycle_me_2/recyclable_items.txt')  # Use the absolute path to your file

