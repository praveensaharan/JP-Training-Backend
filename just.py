import datetime
import re
from collections import defaultdict
import ast
from db import get_connection

# Make sure to have get_connection() defined or imported from your previous code

def fetch_all_common_classes():
    connection = get_connection()
    if connection is None:
        print("Failed to connect to the database.")
        return

    select_query = "SELECT * FROM common_classes ORDER BY day_of_week;"

    try:
        cursor = connection.cursor()
        cursor.execute(select_query)
        rows = cursor.fetchall()
        if not rows:
            print("No records found in common_classes.")
            return
        
        for row in rows:
            print(row)

    except Exception as e:
        print(f"Error fetching data: {e}")
    finally:
        cursor.close()
        connection.close()


if __name__ == "__main__":
    fetch_all_common_classes()
