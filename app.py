from flask import Flask, render_template, request, redirect, url_for, flash, session
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
import mysql.connector
from config import db_config

app = Flask(__name__)
app.secret_key = 'hyunjun-carbase-2025'
@app.route('/')
def home():
    return render_template('home.html')

# 📋 브랜드 목록 페이지 (전체 브랜드 보기)
@app.route('/brands')
def show_brands():
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM brand ORDER BY name")
        brands = cursor.fetchall()
        cursor.close()
        conn.close()

        return render_template('brands.html', brands=brands)
    except Exception as e:
        return f"DB 연결 오류: {e}"

# 🔍 브랜드 상세 페이지 (특정 브랜드의 모델들 보여주기)
@app.route('/brands/<int:brand_id>')
def brand_detail(brand_id):
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT * FROM brand WHERE id = %s", (brand_id,))
        brand = cursor.fetchone()

        if not brand:
            return "해당 브랜드를 찾을 수 없습니다."

        cursor.execute("SELECT * FROM car_model WHERE brand_id = %s", (brand_id,))
        models = cursor.fetchall()

        cursor.close()
        conn.close()

        return render_template('brand_detail.html', brand=brand, models=models)

    except Exception as e:
        return f"DB 오류: {e}"

@app.route('/add_brand', methods=['GET', 'POST'])
def add_brand():
    if request.method == 'POST':
        name = request.form['name']
        country = request.form['country']
        founded_year = request.form['founded_year']

        try:
            conn = mysql.connector.connect(**db_config)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO brand (name, country, founded_year) VALUES (%s, %s, %s)",
                (name, country, founded_year)
            )
            conn.commit()
            cursor.close()
            conn.close()
            return redirect(url_for('show_brands'))  # 등록 후 목록으로 이동
        except Exception as e:
            return f"DB 오류: {e}"

    # GET 요청일 때는 폼 보여주기
    return render_template('add_brand.html')

@app.route('/add_model', methods=['GET', 'POST'])
def add_model():
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        model_name = request.form['model_name']
        year = request.form['year']
        engine_type = request.form['engine_type']
        brand_id = request.form['brand_id']

        try:
            cursor.execute(
                "INSERT INTO car_model (model_name, year, engine_type, brand_id) VALUES (%s, %s, %s, %s)",
                (model_name, year, engine_type, brand_id)
            )
            conn.commit()
            return redirect(url_for('show_brands'))
        except Exception as e:
            return f"DB 오류: {e}"
        finally:
            cursor.close()
            conn.close()

    # GET 요청 시 브랜드 목록 미리 불러오기
    cursor.execute("SELECT id, name FROM brand ORDER BY name")
    brands = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('add_model.html', brands=brands)

@app.route('/search')
def search():
    keyword = request.args.get('keyword', '').strip()

    if not keyword:
        return "검색어를 입력해주세요."

    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)

        # 브랜드 검색
        cursor.execute("SELECT * FROM brand WHERE name LIKE %s", (f"%{keyword}%",))
        brand_results = cursor.fetchall()

        # 모델 검색 (브랜드 이름도 조인)
        cursor.execute("""
            SELECT car_model.*, brand.name AS brand_name
            FROM car_model
            JOIN brand ON car_model.brand_id = brand.id
            WHERE car_model.model_name LIKE %s
        """, (f"%{keyword}%",))
        model_results = cursor.fetchall()

        cursor.close()
        conn.close()

        return render_template('search.html',
                               keyword=keyword,
                               brands=brand_results,
                               models=model_results)
    except Exception as e:
        return f"DB 오류: {e}"

@app.route('/delete_brand/<int:brand_id>')
def delete_brand(brand_id):
    if not session.get('admin'):
        flash("⛔ 관리자만 삭제할 수 있습니다.", "danger")
        return redirect(url_for('show_brands'))
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()

        cursor.execute("DELETE FROM car_model WHERE brand_id = %s", (brand_id,))
        cursor.execute("DELETE FROM brand WHERE id = %s", (brand_id,))

        conn.commit()
        cursor.close()
        conn.close()

        flash("✅ 브랜드가 삭제되었습니다.", "success")
        return redirect(url_for('show_brands'))

    except Exception as e:
        flash(f"❌ 삭제 중 오류 발생: {e}", "danger")
        return redirect(url_for('show_brands'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        try:
            conn = mysql.connector.connect(**db_config)
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM user WHERE email = %s", (email,))
            user = cursor.fetchone()
            if user and check_password_hash(user['password_hash'], password):
                session['user_id'] = user['id']
                session['username'] = user['username']
                session['is_admin'] = user['is_admin']
                flash("✅ 로그인 성공", "success")
                return redirect(url_for('home'))
            else:
                flash("❌ 이메일 또는 비밀번호가 잘못되었습니다.", "danger")
        except mysql.connector.Error as e:
            flash(f"❌ DB 오류: {e}", "danger")
        finally:
            cursor.close()
            conn.close()

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm = request.form['confirm_password']

        if password != confirm:
            flash("❌ 비밀번호가 일치하지 않습니다.", "danger")
            return redirect(url_for('register'))

        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')

        try:
            conn = mysql.connector.connect(**db_config)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO user (username, email, password_hash)
                VALUES (%s, %s, %s)
            """, (username, email, hashed_password))
            conn.commit()
            flash("✅ 회원가입이 완료되었습니다. 로그인해주세요.", "success")
        except mysql.connector.Error as e:
            flash(f"❌ DB 오류: {e}", "danger")
        finally:
            cursor.close()
            conn.close()

        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('로그아웃 되었습니다.', 'info')
    return redirect(url_for('home'))


@app.route('/delete_model/<int:model_id>')
def delete_model(model_id):
    if not session.get('admin'):
        flash("⛔ 관리자만 모델을 삭제할 수 있습니다.", "danger")
        return redirect(url_for('home'))

    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()

        # 모델 삭제
        cursor.execute("DELETE FROM car_model WHERE id = %s", (model_id,))
        conn.commit()
        cursor.close()
        conn.close()

        flash("✅ 모델이 삭제되었습니다.", "success")
        return redirect(request.referrer or url_for('home'))  # 이전 페이지로 돌아감
    except Exception as e:
        flash(f"❌ 삭제 중 오류 발생: {e}", "danger")
        return redirect(request.referrer or url_for('home'))
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('is_admin'):
            return "권한이 없습니다.", 403
        return f(*args, **kwargs)
    return decorated

if __name__ == '__main__':
    app.run(debug=True)
