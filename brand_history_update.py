import csv
import mysql.connector
from config import db_config

# CSV 열기
with open('car_brand_history.csv', newline='', encoding='utf-8') as f:
    reader = csv.DictReader(f)

    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()

    for row in reader:
        cursor.execute("""
            UPDATE brand
            SET logo_url = %s, history = %s
            WHERE name = %s
        """, (row['logo_url'], row['history'], row['name']))

    conn.commit()
    cursor.close()
    conn.close()

print("✅ 브랜드 logo_url과 history 업데이트 완료!")
