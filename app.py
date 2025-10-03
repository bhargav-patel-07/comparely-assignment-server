import json
import pandas as pd
import psycopg2
from flask import Flask, jsonify, request
from flask_cors import CORS 

# --- Configuration ---
# !!! IMPORTANT: Update these with your PostgreSQL credentials !!!
DB_CONFIG = {
    "dbname": "comparely_db",
    "user": "postgres",
    "password": "bhargav0710",
    "host": "localhost",
    "port": "5432"
}
DAILY_SALES_GUESS = 10 # Used for DOI calculation
OOS_ALERT_THRESHOLD_DAYS = 3 # DOI threshold for flagging

app = Flask(__name__)
CORS(app) # Enable CORS for React front-end (Part 3)

def get_db_connection():
    """Connects to the PostgreSQL database."""
    return psycopg2.connect(**DB_CONFIG)

def etl_process():
    """Reads data from JSON, transforms it (DOI, Alert), and loads to DB."""
    try:
        # T: Transform Phase (DOI and Alert Flagging)
        with open("stock_data.json", 'r') as f:
            data = json.load(f)
        
        df = pd.DataFrame(data)
        
        # Calculate Days of Inventory (DOI = stock count / average daily sales)
        df['days_of_inventory'] = df['stock_count'] / DAILY_SALES_GUESS
        
        # Flag OOS Alert (True if stock is 0 OR DOI is under 3 days)
        df['is_oos_alert'] = (df['stock_count'] == 0) | (df['days_of_inventory'] < OOS_ALERT_THRESHOLD_DAYS)
        
        # L: Load Phase (Inserting into stock_history table)
        conn = get_db_connection()
        cursor = conn.cursor()
        
        for index, row in df.iterrows():
            insert_query = """
            INSERT INTO stock_history 
            (timestamp, store_id, product_name, stock_status, stock_count, price, days_of_inventory, is_oos_alert) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(insert_query, (
                row['timestamp'], 
                row['store_id'], 
                row['product'], 
                row['stock_status'], 
                row['stock_count'], 
                row['price'], 
                row['days_of_inventory'], 
                bool(row['is_oos_alert']) # Ensures correct boolean type
            ))
            
        conn.commit()
        cursor.close()
        conn.close()
        return f"✅ Successfully loaded {len(df)} records into stock_history."

    except FileNotFoundError:
        return "🚨 Error: stock_data.json not found. Run the scraper first."
    except psycopg2.OperationalError as e:
        return f"🚨 Database Connection Error: Check DB_CONFIG and ensure PostgreSQL is running. Details: {e}"
    except Exception as e:
        return f"🚨 ETL Error: {e}"


@app.route('/api/process_data', methods=['POST'])
def process_data_endpoint():
    """Endpoint to manually trigger the ETL process."""
    result = etl_process()
    print(result)
    return jsonify({"message": result}), 200

@app.route('/api/stock', methods=['GET'])
def get_stock_summary():
    """
    API endpoint: /api/stock?area=400001
    Pulls the latest aggregated alert data for a specific area.
    (Required format for the prompt's example output)
    """
    area_code = request.args.get('area')
    if not area_code:
        return jsonify({"error": "Missing 'area' query parameter."}), 400
        
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Query to get the latest OOS/DOI alerts for the area
        query = """
        WITH latest_stock AS (
            -- Find the single latest entry for the product in each store
            SELECT 
                sh.*,
                ROW_NUMBER() OVER (PARTITION BY sh.store_id, sh.product_name ORDER BY sh.timestamp DESC) as rn
            FROM stock_history sh
            JOIN stores s ON sh.store_id = s.store_id
            WHERE s.area_code = %s
        )
        SELECT 
            stock_status,
            is_oos_alert
        FROM latest_stock
        WHERE rn = 1; -- Only consider the latest snapshot
        """
        cursor.execute(query, (area_code,))
        
        latest_records = cursor.fetchall()
        
        # Aggregation Logic to match the required output format
        oos_count = sum(1 for status, alert in latest_records if status == 'OOS')
        doi_alert_count = sum(1 for status, alert in latest_records if alert == True and status != 'OOS')
        
        # Determine the DOI alert message based on the count
        doi_alert_message = f"Low in {doi_alert_count} store(s)" if doi_alert_count > 0 else "None"

        response = {
            "area": area_code,
            "oos_products": oos_count,
            "doi_alert": doi_alert_message
        }
        
        cursor.close()
        conn.close()
        return jsonify(response)
        
    except Exception as e:
        print(f"🚨 API Query Error: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/api/stores', methods=['GET'])
def get_stores_by_area():
    """
    API endpoint: /api/stores?area=400001
    Gets all stores for a given area with their latest product details.
    (Needed for the table display in Part 3)
    """
    area_code = request.args.get('area')
    if not area_code:
        return jsonify({"error": "Missing 'area' query parameter."}), 400
        
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # This query is the same as the one used internally by /api/stock
        query = """
        WITH latest_stock AS (
            SELECT 
                sh.*,
                ROW_NUMBER() OVER (PARTITION BY sh.store_id, sh.product_name ORDER BY sh.timestamp DESC) as rn
            FROM stock_history sh
            JOIN stores s ON sh.store_id = s.store_id
            WHERE s.area_code = %s
        )
        SELECT 
            s.store_id, 
            s.store_name, 
            ls.product_name, 
            ls.stock_status, 
            ls.days_of_inventory
        FROM stores s
        LEFT JOIN latest_stock ls ON s.store_id = ls.store_id AND ls.rn = 1
        WHERE s.area_code = %s;
        """
        cursor.execute(query, (area_code, area_code))
        raw_records = cursor.fetchall()
        
        # Structure the data by store for the front-end
        stores_data = {}
        for store_id, store_name, product_name, status, doi in raw_records:
            if store_id not in stores_data:
                stores_data[store_id] = {
                    "store_id": store_id,
                    "store_name": store_name,
                    "products": []
                }
            if product_name: 
                stores_data[store_id]["products"].append({
                    "name": product_name,
                    "status": status,
                    "doi": float(doi) if doi is not None else 'N/A'
                })

        cursor.close()
        conn.close()
        return jsonify(list(stores_data.values()))
        
    except Exception as e:
        print(f"🚨 API Query Error: {e}")
        return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    # Start the Flask development server
    print("Starting Flask API on http://localhost:5000")
    print("Use /api/process_data (POST) to trigger ETL.")
    app.run(debug=True, port=5000)