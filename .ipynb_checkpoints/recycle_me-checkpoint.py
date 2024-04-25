import psycopg2
from flask import Flask, request, render_template
from fuzzywuzzy import process
import datetime

app = Flask(__name__)

def get_db_connection():
    return psycopg2.connect(host='localhost', dbname='recycling', user='your_username', password='your_password')

def read_recyclable_items():
    conn = get_db_connection()
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

def write_unavailable_location(location):
    timestamp = datetime.datetime.now()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO unavailable_locations (location, timestamp) VALUES (%s, %s)", (location, timestamp))
    conn.commit()
    cursor.close()
    conn.close()

def write_non_recyclable_item(location, material, item):
    timestamp = datetime.datetime.now()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO non_recyclable_items (location, material, item_name, timestamp) VALUES (%s, %s, %s, %s)", (location, material, item, timestamp))
    conn.commit()
    cursor.close()
    conn.close()

def recycle_me(location, material, item, recyclable_items):
    location_matches = process.extractOne(location, recyclable_items.keys(), scorer=process.fuzz.ratio)
    if location_matches[1] > 70:
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

if __name__ == '__main__':
    app.run(debug=True)

