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
from opentelemetry import trace
from opentelemetry.trace.status import StatusCode
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    ConsoleSpanExporter,
)
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.psycopg2 import Psycopg2Instrumentor

app = Flask(__name__)

# Resource configuration for tracing
resource = Resource(attributes={
    "service.name": "Wylies-MacBook-Air",
    "os-version": 14.1,
    "cluster": "A",
    "datacentre": "us-east-1a"
})

# Configure the OTLP exporter
otlp_exporter = OTLPSpanExporter(
    endpoint="localhost:4317",  # Endpoint of the Otel Collector
    insecure=True  # Use TLS in production environments
)

# Set up OpenTelemetry Tracer Provider with OTLP exporter
provider = TracerProvider(resource=resource)
otlp_processor = BatchSpanProcessor(otlp_exporter)
provider.add_span_processor(otlp_processor)
trace.set_tracer_provider(provider)

tracer = trace.get_tracer("my.tracer.name")

#Adding logging to debug issue: 
logging.basicConfig(level=logging.DEBUG)

# This loads the environment variables from the .env file
load_dotenv() 

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

@tracer.start_as_current_span("index_start")
def index():
    with tracer.start_as_current_span("home_route") as span:
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
    with tracer.start_as_current_span("route: blog"):
        return render_template('blog.html')

@app.route('/products')
def products():
    with tracer.start_as_current_span("route: products"):
        return render_template('products.html')

def get_db_connection():
    with tracer.start_as_current_span("db_connection") as get_db_span:
        try:
            conn = psycopg2.connect(
                host=db_host,
                dbname=db_name,
                user=db_user,
                password=db_password)
            span.add_event("Database connection established successfully.")
            return conn
        except Exception as e:
            span.record_exception(e)
            span.set_status(Status(StatusCode.ERROR, "Failed to connect to the database"))
            return None

def read_recyclable_items():
    with tracer.start_as_current_span("recyclable_db_check") as read_recycle_span:
        conn = get_db_connection()
        if conn is not None:
            try:
                cursor = conn.cursor()
                query = 'SELECT l.name, m.name, i.name FROM items i JOIN materials m ON i.material_id = m.id JOIN locations l ON i.location_id = l.id;'
                cursor.execute(query)
                recyclable_items = {}
                for location, material, item_name in cursor.fetchall():
                    if location not in recyclable_items:
                        recyclable_items[location] = {}
                    if material not in recyclable_items[location]:
                        recyclable_items[location][material] = []
                    recyclable_items[location][material].append(item_name)
                cursor.close()
                conn.close()
                span.add_event("Items fetched successfully")
                return recyclable_items
            except Exception as e:
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, "Query failed"))
                return {}
        else:
            span.add_event("Failed to establish database connection")
            span.set_status(Status(StatusCode.ERROR, "Connection failed"))
            return {}

def recycle_me(location, material, item, recyclable_items):
    with tracer.start_as_current_span("recycler") as recycle_this_span:
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
    with tracer.start_as_current_span("write_non_item") as write_item_span:
        conn = get_db_connection()
        if conn is not None:
            cursor = conn.cursor()
            timestamp = datetime.datetime.now()
            query = "INSERT INTO non_recyclable_items (location, material, item_name, timestamp) VALUES (%s, %s, %s, %s);"
            cursor.execute(query, (location, material, item, timestamp))
            conn.commit()
            cursor.close()
            conn.close()
        else:
            span.set_status(Status(StatusCode.ERROR, "Failed to write non-recyclable item due to DB connection issue"))

def write_unavailable_location(location):
    with tracer.start_as_current_span("write_unavailable_item") as write_location_span:
        conn = get_db_connection()
        if conn is not None:
            cursor = conn.cursor()
            timestamp = datetime.datetime.now()
            query = "INSERT INTO unavailable_locations (location, timestamp) VALUES (%s, %s);"
            cursor.execute(query, (location, timestamp))
            conn.commit()
            cursor.close()
            conn.close()
        else:
            span.set_status(Status(StatusCode.ERROR, "Failed to write unavailable location due to DB connection issue"))

def find_available_port():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('', 0))
    port = s.getsockname()[1]
    s.close()
    return port

if __name__ == '__main__':
    port = find_available_port()
    app.run(host='0.0.0.0', port=port, debug=True)
