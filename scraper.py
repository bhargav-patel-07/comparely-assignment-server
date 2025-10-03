import json
import time
import random
from datetime import datetime

PRODUCT_NAME = "Mango Oatmeal"
AREAS = {
    "400001": ["BLK_MUM_101", "BLK_MUM_102"],  # Mumbai
    "201301": ["BLK_NOI_201", "BLK_NOI_202", "BLK_NOI_203"]  # Noida
}
OUTPUT_FILE = "stock_data.json"
CHECK_INTERVAL_SECONDS = 5 * 60 # 5 minutes (Use 10 seconds for testing)
# CHECK_INTERVAL_SECONDS = 10 

def simulate_fetch_stock_data(area_code, store_id):
    stock_options = {
        "full": {"stock_count": random.randint(30, 100), "price": 199.00},
        "low": {"stock_count": random.randint(1, 15), "price": 199.00},
        "OOS": {"stock_count": 0, "price": 199.00}
    }
    
    # 60% chance of 'full', 25% 'low', 15% 'OOS'
    status_choice = random.choices(
        list(stock_options.keys()), 
        weights=[60, 25, 15], 
        k=1
    )[0]
    
    data = stock_options[status_choice]
    
    return {
        "timestamp": datetime.now().isoformat(),
        "area": area_code,
        "store_id": store_id,
        "product": PRODUCT_NAME,
        "stock_status": status_choice,
        "stock_count": data["stock_count"], # New field for Part 2
        "price": data["price"]
    }

def run_scraper():
    """Main loop to scrape and save data."""
    all_records = []
    
    for area, store_list in AREAS.items():
        for store_id in store_list:
            try:
                # Simulate data fetching
                record = simulate_fetch_stock_data(area, store_id)
                all_records.append(record)
                print(f"[{record['timestamp']}] Fetched data for {record['area']} - {record['store_id']} | Status: {record['stock_status']}")
                
                # Small, random delay to be respectful of a real API/site
                time.sleep(random.uniform(1, 3)) 
                
            except Exception as e:
                # Handle network issues, blocks, or parsing errors
                print(f"🚨 ERROR fetching data for Area {area}, Store {store_id}: {e}")
                
    # Save all records to a single JSON file
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(all_records, f, indent=4)
        
    print(f"\n✅ Data saved to {OUTPUT_FILE} with {len(all_records)} records.")

if __name__ == "__main__":
    while True:
        run_scraper()
        print(f"\n--- Waiting for {CHECK_INTERVAL_SECONDS} seconds... ---\n")
        time.sleep(CHECK_INTERVAL_SECONDS)