from flask import Flask, render_template, request, redirect, jsonify
import sqlite3
from datetime import date
import calendar
import json

app = Flask(__name__)
DB="workout.db"

def query(sql,args=(),one=False):
    con=sqlite3.connect(DB)
    cur=con.cursor()
    cur.execute(sql,args)
    r=cur.fetchall()
    con.commit()
    con.close()
    return (r[0] if r else None) if one else r

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

@app.route("/")
def index():
    y = request.args.get("year", type=int)
    m = request.args.get("month", type=int)
    today = date.today()
    year = y or today.year
    month = m or today.month

    calendar.setfirstweekday(calendar.SUNDAY)
    cal = calendar.monthcalendar(year, month)

    members=query("SELECT * FROM members")
    exercises=query("SELECT * FROM exercises")

    # ワークアウト取得
    workouts=query("""
    SELECT w.id, w.day, m.id, m.name, e.id, e.name, w.reps
    FROM workouts w
    JOIN members m ON w.member_id=m.id
    JOIN exercises e ON w.exercise_id=e.id
    """)

    # 日ごとマッピング
    workout_map={}
    for w in workouts:
        wid, day, mid, mname, eid, ename, reps = w
        if day not in workout_map:
            workout_map[day]=[]
        workout_map[day].append({
            "id": wid,
            "member_id": mid,
            "member": mname,
            "exercise_id": eid,
            "exercise": ename,
            "reps": reps
        })

    # ランキング
    ranking=query("""
    SELECT m.name,SUM(w.reps)
    FROM workouts w
    JOIN members m ON w.member_id=m.id
    WHERE strftime('%Y-%m',w.day)=?
    GROUP BY m.name
    ORDER BY SUM(w.reps) DESC
    """,(f"{year}-{month:02d}",))

    # 種目別ランキング
    ranking_by_exercise = query("""
    SELECT e.name, m.name, SUM(w.reps) as total
    FROM workouts w
    JOIN exercises e ON w.exercise_id = e.id
    JOIN members m ON w.member_id = m.id
    WHERE strftime('%Y-%m', w.day)=?
    GROUP BY e.name, m.name
    ORDER BY e.name, total DESC
    """, (f"{year}-{month:02d}",))

    # 種目統計（既存）
    exercise_stats=query("""
    SELECT e.name,SUM(w.reps)
    FROM workouts w
    JOIN exercises e ON w.exercise_id=e.id
    WHERE strftime('%Y-%m',w.day)=?
    GROUP BY e.name
    """,(f"{year}-{month:02d}",))

    # メンバー統計（既存）
    member_stats=query("""
    SELECT m.name,SUM(w.reps)
    FROM workouts w
    JOIN members m ON w.member_id=m.id
    WHERE strftime('%Y-%m',w.day)=?
    GROUP BY m.name
    """,(f"{year}-{month:02d}",))

    # 種目ごとにメンバー内訳
    member_exercise_stats = {}
    for w in workouts:
        wid, day, mid, mname, eid, ename, reps = w
        if ename not in member_exercise_stats:
            member_exercise_stats[ename] = {}
        if mname not in member_exercise_stats[ename]:
            member_exercise_stats[ename][mname] = 0
        member_exercise_stats[ename][mname] += reps

    # 種目ごとの日別詳細
    exercise_day_details = {}
    for w in workouts:
        wid, day, mid, mname, eid, ename, reps = w
        if ename not in exercise_day_details:
            exercise_day_details[ename] = []
        exercise_day_details[ename].append({
            "day": day,
            "member": mname,
            "reps": reps
        })
    

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
        member_stats=member_stats,
        member_exercise_stats=json.dumps(member_exercise_stats),
        exercise_day_details=json.dumps(exercise_day_details),
        ranking_by_exercise=ranking_by_exercise
    )

@app.route("/add_member",methods=["POST"])
def add_member():
    name=request.form["name"]
    query("INSERT INTO members(name) VALUES(?)",(name,))
    return redirect("/")

@app.route("/add_exercise",methods=["POST"])
def add_exercise():
    name=request.form["name"]
    query("INSERT INTO exercises(name) VALUES(?)",(name,))
    return redirect("/")

@app.route("/add_workout",methods=["POST"])
def add_workout():
    wid=request.form.get("id")
    member=request.form["member"]
    exercise=request.form["exercise"]
    reps=request.form["reps"]
    day=request.form["day"]

    if wid:  # 編集
        query("UPDATE workouts SET member_id=?, exercise_id=?, reps=?, day=? WHERE id=?",
              (member, exercise, reps, day, wid))
    else:    # 新規
        query("INSERT INTO workouts(member_id,exercise_id,reps,day) VALUES(?,?,?,?)",
              (member, exercise, reps, day))

    return redirect("/")

@app.route("/delete_workout", methods=["POST"])
def delete_workout():
    data = json.loads(request.data)
    wid = data.get("id")
    if wid:
        conn=sqlite3.connect(DB)
        c=conn.cursor()
        c.execute("DELETE FROM workouts WHERE id=?",(wid,))
        conn.commit()
        conn.close()
    return "", 204

if __name__=="__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)