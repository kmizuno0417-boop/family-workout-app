from flask import Flask, render_template, request, redirect, jsonify
import sqlite3
from datetime import date, timedelta
import calendar
import json

app = Flask(__name__)
DB="workout.db"


# ストリーク計算
def calculate_streak(member_id):

    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    cur.execute("""
        SELECT DISTINCT day
        FROM workouts
        WHERE member_id=?
        ORDER BY day DESC
    """,(member_id,))

    rows = cur.fetchall()
    conn.close()

    dates = set(r[0] for r in rows)

    today = date.today()
    yesterday = today - timedelta(days=1)

    streak = 0

    # 今日やってるか
    if today.strftime("%Y-%m-%d") in dates:
        start = today
    else:
        start = yesterday

    for i in range(365):
        d = (start - timedelta(days=i)).strftime("%Y-%m-%d")

        if d in dates:
            streak += 1
        else:
            break

    return streak


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

    members = query("SELECT * FROM members")
    exercises = query("SELECT * FROM exercises")

    # メンバー色
    member_colors={}
    palette=[
        "#3498db","#f39c12","#27ae60","#e74c3c",
        "#9b59b6","#1abc9c","#e67e22","#2ecc71"
    ]

    for i,m in enumerate(members):
        member_colors[m[1]]=palette[i%len(palette)]

    # ワークアウト取得
    workouts=query("""
    SELECT w.id,w.day,m.id,m.name,e.id,e.name,w.reps
    FROM workouts w
    JOIN members m ON w.member_id=m.id
    JOIN exercises e ON w.exercise_id=e.id
    """)

    workout_map={}

    for w in workouts:
        wid,day,mid,mname,eid,ename,reps=w

        if day not in workout_map:
            workout_map[day]=[]

        workout_map[day].append({
            "id":wid,
            "member_id":mid,
            "member":mname,
            "exercise_id":eid,
            "exercise":ename,
            "reps":reps
        })


    # 今月ランキング
    ranking=query("""
    SELECT m.name,SUM(w.reps)
    FROM workouts w
    JOIN members m ON w.member_id=m.id
    WHERE strftime('%Y-%m',w.day)=?
    GROUP BY m.name
    ORDER BY SUM(w.reps) DESC
    """,(f"{year}-{month:02d}",))


    # 種目別ランキング
    ranking_by_exercise=query("""
    SELECT e.name,m.name,SUM(w.reps)
    FROM workouts w
    JOIN exercises e ON w.exercise_id=e.id
    JOIN members m ON w.member_id=m.id
    WHERE strftime('%Y-%m',w.day)=?
    GROUP BY e.name,m.name
    ORDER BY e.name,SUM(w.reps) DESC
    """,(f"{year}-{month:02d}",))


    # 種目統計
    exercise_stats=query("""
    SELECT e.name,SUM(w.reps)
    FROM workouts w
    JOIN exercises e ON w.exercise_id=e.id
    WHERE strftime('%Y-%m',w.day)=?
    GROUP BY e.name
    """,(f"{year}-{month:02d}",))


    # メンバー統計
    member_stats=query("""
    SELECT m.name,SUM(w.reps)
    FROM workouts w
    JOIN members m ON w.member_id=m.id
    WHERE strftime('%Y-%m',w.day)=?
    GROUP BY m.name
    """,(f"{year}-{month:02d}",))

    # レベルシステム
    member_levels = {}

    for m in members:

        name = m[1]

        # 合計回数取得
        row = query("""
        SELECT SUM(reps)
        FROM workouts w
        JOIN members m ON w.member_id=m.id
        WHERE m.name=?
        """,(name,),one=True)

        total = row[0] if row and row[0] else 0

        level = total // 100
        next_level = (level + 1) * 100

        progress = int((total % 100) / 100 * 100)

        remain = next_level - total

        # 称号
        if level >= 100:
            title = "👑 レジェンド"
        elif level >= 50:
            title = "🦾 マスター"
        elif level >= 20:
            title = "⚔ 戦士"
        elif level >= 5:
            title = "🥉 見習い"
        else:
            title = "🙂 ルーキー"

        member_levels[name] = {
            "level": level,
            "progress": progress,
            "remain": remain,
            "title": title
        }

        # 世界登山モード（1回 = 1m）
        mountains = [
            {"name":"高尾山","height":599},
            {"name":"筑波山","height":877},
            {"name":"富士山","height":3776},
            {"name":"マッターホルン","height":4478},
            {"name":"キリマンジャロ","height":5895},        
            {"name":"エベレスト","height":8848},
            {"name":"成層圏","height":50000},
            {"name":"宇宙","height":100000},
            {"name":"月","height":384400},
            {"name":"宇宙ステーション","height":408000}
        ]

        mountain_progress = []

        for m in member_stats:

            name = m[0]
            total = m[1] or 0

            climbed = total
            passed_height = 0

            current_mountain = mountains[-1]["name"]
            goal = mountains[-1]["height"]
            progress = 100
            remaining = 0

            for mt in mountains:

                if climbed < passed_height + mt["height"]:

                    current_mountain = mt["name"]
                    goal = mt["height"]

                    current_height = climbed - passed_height

                    progress = int((current_height / goal) * 100)
                    remaining = goal - current_height

                    break

                passed_height += mt["height"]

            mountain_progress.append({
                "name": name,
                "height": climbed,
                "mountain": current_mountain,
                "progress": progress,
                "remaining": remaining,
                "goal": goal
            })


    # 種目別メンバー統計
    member_exercise_stats={}

    for w in workouts:
        wid,day,mid,mname,eid,ename,reps=w

        if ename not in member_exercise_stats:
            member_exercise_stats[ename]={}

        if mname not in member_exercise_stats[ename]:
            member_exercise_stats[ename][mname]=0

        member_exercise_stats[ename][mname]+=reps


    # 種目別日詳細
    exercise_day_details={}

    for w in workouts:
        wid,day,mid,mname,eid,ename,reps=w

        if ename not in exercise_day_details:
            exercise_day_details[ename]=[]

        exercise_day_details[ename].append({
            "day":day,
            "member":mname,
            "reps":reps
        })


    today_str=date.today().strftime("%Y-%m-%d")


    # 連続記録
    member_streaks = []

    for m in members:

        member_id = m[0]
        member_name = m[1]

        streak = calculate_streak(member_id)

        member_streaks.append({
            "name": member_name,
            "streak": streak
        })

    # ストリークランキング
    streak_ranking = sorted(
        member_streaks,
        key=lambda x: x["streak"],
        reverse=True
    )

    return render_template(
        "index.html",
        members=members,
        exercises=exercises,
        calendar=cal,
        workouts=workout_map,
        year=year,
        month=month,
        member_colors=member_colors,
        ranking=ranking,
        exercise_stats=exercise_stats,
        member_stats=member_stats,
        member_exercise_stats=json.dumps(member_exercise_stats),
        exercise_day_details=json.dumps(exercise_day_details),
        ranking_by_exercise=ranking_by_exercise,
        current_date=today_str,
        member_streaks=member_streaks,
        streak_ranking=streak_ranking,
        member_levels=member_levels,
        mountain_progress=mountain_progress
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

    if wid:
        query(
        "UPDATE workouts SET member_id=?,exercise_id=?,reps=?,day=? WHERE id=?",
        (member,exercise,reps,day,wid)
        )
    else:
        query(
        "INSERT INTO workouts(member_id,exercise_id,reps,day) VALUES(?,?,?,?)",
        (member,exercise,reps,day)
        )

    return redirect("/")


@app.route("/delete_workout",methods=["POST"])
def delete_workout():

    data=json.loads(request.data)
    wid=data.get("id")

    if wid:
        conn=sqlite3.connect(DB)
        c=conn.cursor()
        c.execute("DELETE FROM workouts WHERE id=?",(wid,))
        conn.commit()
        conn.close()

    return "",204

@app.route("/delete_member", methods=["POST"])
def delete_member():

    member_id = request.form["id"]

    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    # ワークアウト削除
    cur.execute("DELETE FROM workouts WHERE member_id=?", (member_id,))

    # メンバー削除
    cur.execute("DELETE FROM members WHERE id=?", (member_id,))

    conn.commit()
    conn.close()

    return redirect("/")


@app.route("/delete_exercise", methods=["POST"])
def delete_exercise():

    exercise_id = request.form["id"]

    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    # ワークアウト削除
    cur.execute("DELETE FROM workouts WHERE exercise_id=?", (exercise_id,))

    # 種目削除
    cur.execute("DELETE FROM exercises WHERE id=?", (exercise_id,))

    conn.commit()
    conn.close()

    return redirect("/")

if __name__=="__main__":
    app.run(host="0.0.0.0",port=5000,debug=True)