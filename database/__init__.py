import os
import re

import psycopg2


database_data = re.split(r'[:/@]', os.environ.get("DATABASE_URL"))[3:]

connection = psycopg2.connect(
    user=database_data[0],
    password=database_data[1],
    host=database_data[2],
    port=database_data[3],
    dbname=database_data[4]
)

cursor = connection.cursor()

for name in ["statements", "preliminary_protocols", "final_protocols"]:
    cursor.execute(
        "CREATE TABLE "
        f"IF NOT EXISTS {name} "
        "(id serial PRIMARY KEY, subject text UNIQUE, url text)"
    )
    connection.commit()

cursor.execute(
    "CREATE TABLE "
    "IF NOT EXISTS users "
    "(id serial PRIMARY KEY, telegram_id integer, "
    "is_subscribed_to_notifications bool)"
)
connection.commit()
