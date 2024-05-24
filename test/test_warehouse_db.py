from pprint import pprint as pp
from pg8000.native import Connection, DatabaseError
import os
from dotenv import load_dotenv
from botocore.exceptions import ClientError
import pytest
from src.load_lambda.utils import insert_data_into_data_warehouse


load_dotenv()


psql_user = os.getenv("psql_username")
psql_password = os.getenv("psql_password")

#table_name:str, data
def root_warehouse_db() -> Connection:
    conn = Connection(user=psql_user, password=psql_password, port=5432, host="localhost")
    conn.run("DROP DATABASE IF EXISTS postgres;")
    conn.run("CREATE DATABASE postgres;")
    conn = Connection(user=psql_user, password=psql_password, database="postgres", port=5432, host="localhost")
    return conn

def seed_warehouse_db(table_name:str, data, connection:Connection):
    connection.run("""CREATE TABLE
        dim_date(
            date_id DATE PRIMARY KEY NOT NULL,
            year INT NOT NULL,
            month INT NOT NULL,
            day INT NOT NULL,
            day_of_week INT NOT NULL,
            month_name VARCHAR NOT NULL,
            quarter INT NOT NULL
            );""")
    connection.run("""CREATE TABLE
        dim_staff(
            staff_id INT PRIMARY KEY NOT NULL,
            first_name VARCHAR NOT NULL,
            last_name VARCHAR NOT NULL,
            department_name VARCHAR NOT NULL,
            location VARCHAR NOT NULL,
            email_address VARCHAR NOT NULL
            );""")
    connection.run("""CREATE TABLE
        dim_currency(
            currency_id INT PRIMARY KEY NOT NULL,
            currency_code VARCHAR NOT NULL,
            currency_name VARCHAR NOT NULL
            );""")
    connection.run("""CREATE TABLE
        dim_design(
            design_id INT PRIMARY KEY NOT NULL,
            design_name VARCHAR NOT NULL,
            file_location VARCHAR NOT NULL,
            file_name VARCHAR NOT NULL
            );""")
    connection.run("""CREATE TABLE
        dim_location(
            location_id INT PRIMARY KEY NOT NULL,
            address_line_1 VARCHAR NOT NULL,
            address_line_2 VARCHAR,
            district VARCHAR,
            city VARCHAR NOT NULL,
            postal_code VARCHAR NOT NULL,
            country VARCHAR NOT NULL,
            phone VARCHAR NOT NULL
            );""")
    connection.run("""CREATE TABLE
        dim_counterparty(
            counterparty_id INT PRIMARY KEY NOT NULL,
            counterparty_legal_name VARCHAR NOT NULL,
            counterparty_legal_address_line_1 VARCHAR NOT NULL,
            counterparty_legal_address_line2 VARCHAR NOT NULL,
            counterparty_legal_district VARCHAR NOT NULL,
            counterparty_legal_city VARCHAR NOT NULL,
            counterparty_legal_postal_code VARCHAR NOT NULL,
            counterparty_legal_country VARCHAR NOT NULL,
            counterparty_legal_phone_number VARCHAR NOT NULL
            );""")
    connection.run("""CREATE TABLE
        fact_sales_order(
            sales_record_id SERIAL PRIMARY KEY,
            sales_order_id INT NOT NULL,
            created_date DATE NOT NULL REFERENCES dim_date(date_id),
            created_time TIME NOT NULL,
            last_updated_date DATE NOT NULL REFERENCES dim_date(date_id),
            last_updated_time TIME NOT NULL,
            sales_staff_id INT NOT NULL REFERENCES dim_staff(staff_id),
            counterparty_id INT NOT NULL REFERENCES dim_counterparty(counterparty_id),
            units_sold INT NOT NULL,
            unit_price NUMERIC(10,2) NOT NULL,
            currency_id INT NOT NULL REFERENCES dim_currency(currency_id),
            design_id INT NOT NULL REFERENCES dim_design(design_id),
            agreed_payment_date DATE NOT NULL REFERENCES dim_date(date_id),
            agreed_delivery_date DATE NOT NULL REFERENCES dim_date(date_id),
            agreed_delivery_locatiion_id INT NOT NULL REFERENCES dim_location(location_id)
            );""")
    #seeding the database in the right way
    #test_result = conn.run(f"SELECT column_name FROM information_schema.columns where table_name = '{table_name}';")
    connection.run(f"INSERT INTO {table_name} VALUES ({data})")
    result = connection.run(f"SELECT * FROM {table_name}")
    connection.close()
    return result

class TestLoadLambda:
    def test_incorrect_table_name(self):
        with pytest.raises(DatabaseError):
            root_warehouse_db("blimble")
    
