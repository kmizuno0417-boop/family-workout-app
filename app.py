from flask import Flask, render_template, request, redirect, jsonify
import sqlite3
from datetime import date
import calendar

app = Flask(__name__)
DB = "workout.db"

# DBクエリ関数
def query(sql, args=(), one=False):
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row  # dictのようにアクセス可能
    cur = con.cursor()
    cur.execute(sql, args)
    r = cur.fetchall()
    con.commit()
    con.close()
    return (r[0] if r else None) if one else r

# 初期化
def init_db():
    query("""
    CREATE TABLE IF NOT EXISTS members(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT
    )""")
    query("""
    CREATE TABLE IF NOT EXISTS exercises(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT
    )""")
    query("""
    CREATE TABLE IF NOT EXISTS workouts(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        member_id INTEGER,
        exercise_id INTEGER,
        reps INTEGER,
        day TEXT
    )""")

init_db()

# トップページ（カレンダー＋グラフ）
@app.route("/")
def index():
    # URLパラメータで年月を取得
    y = request.args.get("year", type=int)
    m = request.args.get("month", type=int)
    today = date.today()
    year = y or today.year
    month = m or today.month

    # 日曜始まりカレンダー
    calendar.setfirstweekday(calendar.SUNDAY)
    cal = calendar.monthcalendar(year, month)

    members = query("SELECT * FROM members")
    exercises = query("SELECT * FROM exercises")

    workouts = query("""
    SELECT workouts.id, day, members.id AS member_id, members.name AS member_name,
           exercises.id AS exercise_id, exercises.name AS exercise_name, reps
    FROM workouts
    JOIN members ON workouts.member_id = members.id
    JOIN exercises ON workouts.exercise_id = exercises.id
    """)

    # 日付ごとにワークアウトをまとめる
    workout_map = {}
    for w in workouts:
        wid, day, mid, mname, eid, ename, reps = w
        if day not in workout_map:
            workout_map[day] = []
        workout_map[day].append({
            "id": wid,
            "member_id": mid,
            "member": mname,
            "exercise_id": eid,
            "exercise": ename,
            "reps": reps
        })

    # 今月ランキング
    ranking = query("""
    SELECT members.name, SUM(reps) AS total
    FROM workouts
    JOIN members ON workouts.member_id = members.id
    WHERE strftime('%Y-%m', day) = ?
    GROUP BY members.name
    ORDER BY total DESC
    """, (f"{year}-{month:02d}",))

    # 種目ごとの集計
    exercise_stats = query("""
    SELECT exercises.name, SUM(reps) AS total
    FROM workouts
    JOIN exercises ON workouts.exercise_id = exercises.id
    WHERE strftime('%Y-%m', day) = ?
    GROUP BY exercises.name
    """, (f"{year}-{month:02d}",))

    # メンバーごとの集計
    member_stats = query("""
    SELECT members.name, SUM(reps) AS total
    FROM workouts
    JOIN members ON workouts.member_id = members.id
    WHERE strftime('%Y-%m', day) = ?
    GROUP BY members.name
    """, (f"{year}-{month:02d}",))

    return render_template(
        "index.html",
        members=members,
        exercises=exercises,
        calendar=cal,
        workouts=workout_map,
        year=year,
        month=month,
        ranking=ranking,
        exercise_stats=exercise_stats,
        member_stats=member_stats
    )

# メンバー追加
@app.route("/add_member", methods=["POST"])
def add_member():
    name = request.form["name"]
    query("INSERT INTO members(name) VALUES(?)", (name,))
    return redirect("/")

# 種目追加
@app.route("/add_exercise", methods=["POST"])
def add_exercise():
    name = request.form["name"]
    query("INSERT INTO exercises(name) VALUES(?)", (name,))
    return redirect("/")

# ワークアウト追加・編集
@app.route("/add_workout", methods=["POST"])
def add_workout():
    wid = request.form.get("id")
    member = request.form["member"]
    exercise = request.form["exercise"]
    reps = request.form["reps"]
    day = request.form["day"]

    if wid:  # 編集
        query("UPDATE workouts SET member_id=?, exercise_id=?, reps=?, day=? WHERE id=?",
              (member, exercise, reps, day, wid))
    else:    # 新規
        query("INSERT INTO workouts(member_id, exercise_id, reps, day) VALUES(?,?,?,?)",
              (member, exercise, reps, day))
    return redirect("/")

# ワークアウト削除
@app.route("/delete_workout", methods=["POST"])
def delete_workout():
    import json
    data = json.loads(request.data)
    wid = data.get("id")
    if wid:
        query("DELETE FROM workouts WHERE id=?", (wid,))
    return "", 204

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)