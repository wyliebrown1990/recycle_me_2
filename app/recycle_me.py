import os
from dotenv import load_dotenv
import psycopg2
import logging
from flask import Flask, request, render_template
from flask_sqlalchemy import SQLAlchemy
from fuzzywuzzy import process
import datetime
import socket
import sys

load_dotenv()  # This loads the environment variables from the .env file

app = Flask(__name__)

# Update the database URI to use environment variables with your RDS instance as the default
db_user = os.getenv('DATABASE_USER', 'postgres')  # Default to 'postgres' if not set
db_password = os.getenv('DATABASE_PASSWORD', 'your_default_password')  # Set your default password if needed
db_host = os.getenv('DATABASE_HOST', 'recycle-me-instance.c97nvm5e6tbs.us-east-1.rds.amazonaws.com')
db_port = os.getenv('DATABASE_PORT', '5432')  # Default to 5432 if not set
db_name = os.getenv('DATABASE_NAME', 'initial')  # Default to 'initial' if not set

#Validate the db access is correct
print("Database Host:", os.getenv('DATABASE_HOST'))
print("Database User:", os.getenv('DATABASE_USER'))
print("Database Name:", os.getenv('DATABASE_NAME'))
print("Database Port:", os.getenv('DATABASE_PORT'))
print("Database Password:", os.getenv('DATABASE_PASSWORD'))

app.config['SQLALCHEMY_DATABASE_URI'] = f'postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Set up basic logging to stdout with a level that captures more details
logging.basicConfig(level=logging.DEBUG)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        location = request.form['location'].lower()
        material = request.form['material']
        item = request.form['item']
        
        recyclable_items = read_recyclable_items()
        if not recyclable_items:
            return "No recyclable items found.", 400
        
        response = recycle_me(location, material, item, recyclable_items)
        return render_template('response.html', response=response)
    else:
        return render_template('form.html')

@app.route('/blog')
def blog():
    return render_template('blog.html')

@app.route('/products')
def products():
    return render_template('products.html')

def get_db_connection():
    # Use environment variables for database connection
    try:
        conn = psycopg2.connect(
            host=db_host,
            dbname=db_name,
            user=db_user,
            password=db_password)
        print("Database connection established successfully.")
        return conn
    except Exception as e:
        print("Error establishing database connection:", e)
        return None

def read_recyclable_items():
    conn = get_db_connection()
    if conn is not None:
        cursor = conn.cursor()
        cursor.execute('SELECT l.name, m.name, i.name FROM items i JOIN materials m ON i.material_id = m.id JOIN locations l ON i.location_id = l.id;')
        recyclable_items = {}
        for location, material, item_name in cursor.fetchall():
            if location not in recyclable_items:
                recyclable_items[location] = {}
            if material not in recyclable_items[location]:
                recyclable_items[location][material] = []
            recyclable_items[location][material].append(item_name)
        cursor.close()
        conn.close()
        return recyclable_items
    else:
        return {}

def recycle_me(location, material, item, recyclable_items):
        location_matches = process.extractOne(location, recyclable_items.keys(), scorer=process.fuzz.ratio)
        if location_matches and location_matches[1] > 70:
            location = location_matches[0]
            if material in recyclable_items[location]:
                if item in recyclable_items[location][material]:
                    return "Yes, recycle this! But please always remember to clean and remove any food waste attached."
                else:
                    write_non_recyclable_item(location, material, item)
                    return "Sorry, this item is not recyclable in {} for {} material.".format(location, material)
            else:
                write_non_recyclable_item(location, material, item)
                return "Sorry, recycling information for {} material is not available for {}.".format(material, location)
        else:
            write_unavailable_location(location)
            return "Sorry, recycling information for {} is not available.".format(location)

def write_non_recyclable_item(location, material, item):
        conn = get_db_connection()
        if conn is not None:
            cursor = conn.cursor()
            timestamp = datetime.datetime.now()
            query = "INSERT INTO non_recyclable_items (location, material, item_name, timestamp) VALUES (%s, %s, %s, %s);"
            cursor.execute(query, (location, material, item, timestamp))
            conn.commit()
            cursor.close()
            conn.close()

def write_unavailable_location(location):
        conn = get_db_connection()
        if conn is not None:
            cursor = conn.cursor()
            timestamp = datetime.datetime.now()
            query = "INSERT INTO unavailable_locations (location, timestamp) VALUES (%s, %s);"
            cursor.execute(query, (location, timestamp))
            conn.commit()
            cursor.close()
            conn.close()

# Use socket to find an available port
def find_available_port():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('', 0))  # Bind to a free port provided by the host.
    port = s.getsockname()[1]  # Return the port number assigned.
    s.close()
    return port

if __name__ == '__main__':
    port = find_available_port()  # Find a free port
    app.run(host='0.0.0.0', port=port, debug=True)  # Listen on all network interfaces
