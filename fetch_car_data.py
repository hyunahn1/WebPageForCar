import json
import requests
import mysql.connector
from config import db_config

APP_ID = 'hlhoNKjOvEhqzcVAJ1lxjicJLZNVv36GdbboZj3Z'
MASTER_KEY = 'SNMJJF0CZZhTPhLDIqGhTlUNV9r60M2Z5spyWfXW'

headers = {
    'X-Parse-Application-Id': APP_ID,
    'X-Parse-Master-Key': MASTER_KEY
}

def fetch_all_car_data():
    all_data = []
    limit = 1000
    total = 9800  # 전체 예상 데이터 수
    for skip in range(0, total, limit):
        print(f"⏳ Fetching records {skip} to {skip + limit}...")
        url = f'https://parseapi.back4app.com/classes/Car_Model_List?limit={limit}&skip={skip}&order=Make,Model'
        res = requests.get(url, headers=headers)
        data = json.loads(res.content.decode('utf-8'))

        if 'results' not in data:
            print("❌ API 오류 발생:", data)
            break

        all_data.extend(data['results'])
    print(f"✅ 총 {len(all_data)}개의 데이터 수집 완료!")
    return all_data

def save_to_db(data):
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()

    brand_cache = {}

    for car in data:
        make = car.get("Make", "Unknown")
        model = car.get("Model", "Unknown")
        category = car.get("Category", "Unknown")
        year = car.get("Year", 2024)

        # 브랜드가 없으면 삽입
        if make not in brand_cache:
            cursor.execute("SELECT id FROM brand WHERE name = %s", (make,))
            result = cursor.fetchone()

            if not result:
                cursor.execute(
                    "INSERT INTO brand (name, country, founded_year) VALUES (%s, %s, %s)",
                    (make, 'Unknown', 1900)
                )
                conn.commit()
                brand_id = cursor.lastrowid
            else:
                brand_id = result[0]

            brand_cache[make] = brand_id
        else:
            brand_id = brand_cache[make]

        # 모델 삽입
        cursor.execute(
            "INSERT INTO car_model (model_name, engine_type, year, brand_id) VALUES (%s, %s, %s, %s)",
            (model, category, year, brand_id)
        )

    conn.commit()
    cursor.close()
    conn.close()
    print("✅ 데이터베이스 저장 완료!")

if __name__ == '__main__':
    data = fetch_all_car_data()
    save_to_db(data)
