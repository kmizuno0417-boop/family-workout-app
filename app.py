from flask import Flask, render_template, request, redirect
import sqlite3
from datetime import date
import calendar

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
    )
    """)

    query("""
    CREATE TABLE IF NOT EXISTS exercises(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT
    )
    """)

    query("""
    CREATE TABLE IF NOT EXISTS workouts(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    member_id INTEGER,
    exercise_id INTEGER,
    reps INTEGER,
    day TEXT
    )
    """)

init_db()


@app.route("/")
def index():

    today=date.today()
    year=today.year
    month=today.month

    members=query("SELECT * FROM members")
    exercises=query("SELECT * FROM exercises")

    workouts=query("""
    SELECT day,members.name,exercises.name,reps
    FROM workouts
    JOIN members ON workouts.member_id=members.id
    JOIN exercises ON workouts.exercise_id=exercises.id
    """)

    workout_map={}

    for w in workouts:

        day,member,exercise,reps=w

        if day not in workout_map:
            workout_map[day]=[]

        workout_map[day].append({
            "member":member,
            "exercise":exercise,
            "reps":reps
        })

    cal=calendar.monthcalendar(year,month)

    ranking=query("""
    SELECT members.name,SUM(reps)
    FROM workouts
    JOIN members ON workouts.member_id=members.id
    WHERE strftime('%Y-%m',day)=?
    GROUP BY members.name
    ORDER BY SUM(reps) DESC
    """,(f"{year}-{month:02d}",))

    exercise_stats=query("""
    SELECT exercises.name,SUM(reps)
    FROM workouts
    JOIN exercises ON workouts.exercise_id=exercises.id
    WHERE strftime('%Y-%m',day)=?
    GROUP BY exercises.name
    """,(f"{year}-{month:02d}",))

    member_stats=query("""
    SELECT members.name,SUM(reps)
    FROM workouts
    JOIN members ON workouts.member_id=members.id
    WHERE strftime('%Y-%m',day)=?
    GROUP BY members.name
    """,(f"{year}-{month:02d}",))

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

    member=request.form["member"]
    exercise=request.form["exercise"]
    reps=request.form["reps"]
    day=request.form["day"]

    query("""
    INSERT INTO workouts(member_id,exercise_id,reps,day)
    VALUES(?,?,?,?)
    """,(member,exercise,reps,day))

    return redirect("/")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)