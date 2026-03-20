from flask import Flask, request, jsonify, render_template
import sqlite3
import pandas as pd
import os
from datetime import datetime

app = Flask(__name__)

DB_NAME = 'birthdays.db'
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

MONTH_TABLES = {
    1: 'january', 2: 'february', 3: 'march', 4: 'april',
    5: 'may', 6: 'june', 7: 'july', 8: 'august',
    9: 'september', 10: 'october', 11: 'november', 12: 'december'
}

# ================= DB INIT =================
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    for table in MONTH_TABLES.values():
        cursor.execute(f'''
            CREATE TABLE IF NOT EXISTS {table} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                day INTEGER,
                phone TEXT
            )
        ''')

    conn.commit()
    conn.close()

init_db()

# ================= HOME =================
@app.route('/')
def home():
    today = datetime.now()
    table = MONTH_TABLES[today.month]

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute(f"SELECT name, phone FROM {table} WHERE day=?", (today.day,))
    rows = cursor.fetchall()
    conn.close()

    people = [{'name': r[0], 'phone': r[1]} for r in rows]

    return render_template("html1.html", people=people, count=len(people))

# ================= DATA =================
@app.route('/data', methods=['GET', 'POST'])
def data_page():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    if request.method == 'POST':
        data = request.get_json()

        dob = pd.to_datetime(data['dob'])
        table = MONTH_TABLES[dob.month]

        cursor.execute(
        f"INSERT INTO {table} (name, phone, dob, day) VALUES (?, ?, ?, ?)",
            (
                data['name'],
                data['phone'],
                dob.strftime('%Y-%m-%d'),
                dob.day
            )
        )

        conn.commit()
        conn.close()
        return jsonify({'message': 'Added successfully'})

    all_data = []

    for table in MONTH_TABLES.values():
        cursor.execute(f"SELECT name, day, phone FROM {table} LIMIT 20")
        rows = cursor.fetchall()

        for r in rows:
            all_data.append({
                'name': r[0],
                'dob': f"{r[1]} ({table})",
                'phone': r[2]
            })

    conn.close()
    return render_template("data_page.html", data=all_data)

# ================= UPLOAD =================
@app.route('/upload')
def upload_page():
    return render_template("excel_page.html")

@app.route('/upload_file', methods=['POST'])
def upload_file():
    file = request.files['file']
    path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(path)

    df = pd.read_excel(path) if file.filename.endswith('.xlsx') else pd.read_csv(path)
    df.columns = [c.lower().strip() for c in df.columns]

    name_col = next(c for c in df.columns if 'name' in c)
    phone_col = next(c for c in df.columns if 'phone' in c)
    dob_col = next(c for c in df.columns if 'dob' in c or 'birth' in c)

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    count = 0

    for _, row in df.iterrows():
        try:
            dob = pd.to_datetime(row[dob_col])
            table = MONTH_TABLES[dob.month]

            cursor.execute(
            f"INSERT INTO {table} (name, phone, dob, day) VALUES (?, ?, ?, ?)",
                (
                    str(row[name_col]),
                    str(row[phone_col]),
                    dob.strftime('%Y-%m-%d'),
                    dob.day
                )
            )
            count += 1
        except Exception as e:
            print(e)
            continue

    conn.commit()
    conn.close()

    return jsonify({'message': f'{count} records uploaded'})

# ================= SEND =================
@app.route('/send_wishes')
def send_wishes():
    today = datetime.now()
    table = MONTH_TABLES[today.month]

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute(f"SELECT name, phone FROM {table} WHERE day=?", (today.day,))
    users = cursor.fetchall()
    conn.close()

    for u in users:
        print(f"Send WhatsApp to {u[0]} -> {u[1]}")

    return jsonify({'message': f'{len(users)} messages triggered'})


@app.route('/data_preview')
def data_preview():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    preview = []

    for table in MONTH_TABLES.values():
        cursor.execute(f"SELECT name, day, phone FROM {table} LIMIT 10")
        rows = cursor.fetchall()

        for r in rows:
            preview.append({
                'name': r[0],
                'dob': f"{r[1]} ({table})",
                'phone': r[2]
            })

    conn.close()
    return jsonify(preview)


@app.route('/manage')
def manage():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    data = []

    for table in MONTH_TABLES.values():
        cursor.execute(f"SELECT id, name, phone, dob FROM {table}")
        for r in cursor.fetchall():
            data.append({
                'id': r[0],
                'name': r[1],
                'phone': r[2],
                'dob': r[3],
                'table': table
            })

    conn.close()
    return render_template("delete_page.html", data=data)


@app.route('/delete_all', methods=['POST'])
def delete_all():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    for table in MONTH_TABLES.values():
        cursor.execute(f"DELETE FROM {table}")

    conn.commit()
    conn.close()
    return jsonify({'message': 'deleted'})


@app.route('/delete/<table>/<int:id>', methods=['POST'])
def delete_row(table, id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute(f"DELETE FROM {table} WHERE id=?", (id,))
    conn.commit()
    conn.close()

    return jsonify({'message': 'deleted'})


@app.route('/edit/<table>/<int:id>', methods=['POST'])
def edit_row(table, id):
    data = request.get_json()
    dob = pd.to_datetime(data['dob'])

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute(
        f"UPDATE {table} SET name=?, phone=?, dob=?, day=? WHERE id=?",
        (data['name'], data['phone'], dob.strftime('%Y-%m-%d'), dob.day, id)
    )

    conn.commit()
    conn.close()

    return jsonify({'message': 'updated'})

@app.route('/search')
def search():
    try:
        search_type = request.args.get('type')
        value = request.args.get('value', '')

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()

        results = []

        for table in MONTH_TABLES.values():

            if search_type == 'name':
                cursor.execute(
                f"SELECT id,name,phone,dob FROM {table} WHERE LOWER(name) = LOWER(?)",
                (value,)
                )

            elif search_type == 'dob':
                cursor.execute(
                    f"SELECT id,name,phone,dob FROM {table} WHERE dob LIKE ?",
                    (f"%{value}%",)
                )

            elif search_type == 'month':
                if value.lower() == table.lower():
                    cursor.execute(f"SELECT id,name,phone,dob FROM {table}")
                else:
                    continue

            rows = cursor.fetchall()

            for r in rows:
                results.append({
                    "id": r[0],
                    "name": r[1],
                    "phone": r[2],
                    "dob": r[3],
                    "table": table
                })

        conn.close()
        return jsonify(results)

    except Exception as e:
        print("SEARCH ERROR:", e)
        return jsonify([]), 500

# ================= RUN =================
if __name__ == '__main__':
    app.run(debug=True)