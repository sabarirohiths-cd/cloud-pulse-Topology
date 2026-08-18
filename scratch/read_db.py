import sqlite3

try:
    conn = sqlite3.connect(r'd:\Topology Project\cloud-pulse-Topology\inventory and control module data.db')
    cursor = conn.cursor()
    
    cursor.execute("SELECT resource_type, COUNT(*) FROM inventory_resources GROUP BY resource_type ORDER BY COUNT(*) DESC;")
    print("Resource distribution in inventory_resources (ALL):")
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]}")
        
    conn.close()
except Exception as e:
    print("Error:", e)
