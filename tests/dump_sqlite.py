import sqlite3
import json

def dump_sqlite():
    db_path = r"services\vector_db_service\local_qdrant_db\collection\hr_policies\storage.sqlite"
    print(f"Connecting to SQLite: {db_path}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # List tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [t[0] for t in cursor.fetchall()]
    print(f"Tables in database: {tables}")
    
    # Search in tables
    for table in tables:
        try:
            cursor.execute(f"PRAGMA table_info({table});")
            columns = [c[1] for c in cursor.fetchall()]
            print(f"Table '{table}' columns: {columns}")
            
            # Let's search for "5553" in all text/blob columns
            cursor.execute(f"SELECT * FROM {table} LIMIT 10;")
            rows = cursor.fetchall()
            print(f"Sample rows from {table} (first 2):")
            for r in rows[:2]:
                print(r[:5]) # print first 5 elements
                
            # Search for '5553'
            print(f"Searching for '5553' in {table}...")
            cursor.execute(f"SELECT * FROM {table};")
            all_rows = cursor.fetchall()
            found_count = 0
            for row in all_rows:
                row_str = str(row)
                if "5553" in row_str or "تنظيم الإجازات" in row_str or "0١ يوم" in row_str:
                    found_count += 1
                    print(f"Match {found_count} in {table}:")
                    # Try to decode if it is JSON in some column
                    for item in row:
                        if isinstance(item, bytes):
                            try:
                                text_item = item.decode('utf-8', errors='ignore')
                                if "5553" in text_item or "تنظيم الإجازات" in text_item:
                                    print(f"  [Bytes/Text]: {text_item[:500]}")
                            except:
                                pass
                        elif isinstance(item, str):
                            if "5553" in item or "تنظيم الإجازات" in item:
                                print(f"  [Str]: {item[:500]}")
        except Exception as e:
            print(f"Error querying table {table}: {e}")
            
    conn.close()

if __name__ == "__main__":
    dump_sqlite()
