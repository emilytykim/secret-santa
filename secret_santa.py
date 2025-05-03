from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import random
import sqlite3
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

app = Flask(__name__)
app.secret_key = "supersecretkey"

# 이메일 설정
SENDER_EMAIL = "whoisyoursantaclaus@gmail.com"
SENDER_PASSWORD = "tpxk fqbg jtra dpgf"

# 이메일 전송 함수
def send_email(sender_email, sender_password, recipient_email, subject, body):
    msg = MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = recipient_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "html"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, recipient_email, msg.as_string())
        print(f"✅ 이메일 발송 성공: {recipient_email}")
    except Exception as e:
        print(f"❌ 이메일 발송 실패: {recipient_email}, 오류: {e}")
def init_db():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    # 기존 테이블 생성
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS groups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            size INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        group_id INTEGER NOT NULL,
        sender_id INTEGER NOT NULL,
        receiver_id INTEGER NOT NULL,
        message TEXT NOT NULL,
        sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        read INTEGER DEFAULT 0,  -- ✅ 새롭게 추가된 컬럼 (0 = 읽지 않음, 1 = 읽음)
        reply TEXT,
        FOREIGN KEY (group_id) REFERENCES groups (id),
        FOREIGN KEY (sender_id) REFERENCES participants (id),
        FOREIGN KEY (receiver_id) REFERENCES participants (id)
    )
""")


    cursor.execute("""
        CREATE TABLE IF NOT EXISTS participants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            group_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            password TEXT NOT NULL,
            joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (group_id) REFERENCES groups (id),
            UNIQUE (group_id, name)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS matches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            group_id INTEGER NOT NULL,
            giver_id INTEGER NOT NULL,
            receiver_id INTEGER NOT NULL,
            FOREIGN KEY (group_id) REFERENCES groups (id),
            FOREIGN KEY (giver_id) REFERENCES participants (id)
        )
    """)


    # ✅ `read` 컬럼이 없으면 추가
    try:
        cursor.execute("ALTER TABLE messages ADD COLUMN read INTEGER DEFAULT 0;")
        print("✅ Column 'read' added successfully!")
    except sqlite3.OperationalError:
        print("⚠️ Column 'read' already exists, skipping.")


    # Alter table: reply 컬럼 추가
    try:
        cursor.execute("ALTER TABLE messages ADD COLUMN reply TEXT;")
        print("✅ Column 'reply' added successfully!")
    except sqlite3.OperationalError:
        # 이미 컬럼이 존재하면 에러를 무시
        print("⚠️ Column 'reply' already exists, skipping.")

    conn.commit()
    conn.close()



@app.route("/admin", methods=["GET", "POST"])
def admin():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        if username == "admin" and password == "secret_password":
            session["admin"] = True
            flash("관리자 로그인 성공!", "success")
            return redirect(url_for("manage"))
        else:
            flash("잘못된 사용자 이름 또는 비밀번호입니다.", "danger")
    return render_template("admin.html")

@app.route("/manage", methods=["GET", "POST"])
def manage():
    if not session.get("admin"):
        flash("🚫 Access Denied. Admins only.", "danger")
        return redirect(url_for("admin"))

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    if request.method == "POST":
        group_name = request.form["group_name"]
        group_size = int(request.form["group_size"])

        try:
            cursor.execute("INSERT INTO groups (name, size) VALUES (?, ?)", (group_name, group_size))
            conn.commit()
            flash(f"그룹 '{group_name}'이(가) 생성되었습니다!", "success")
        except sqlite3.Error as e:
            flash(f"데이터베이스 오류: {e}", "danger")

    cursor.execute("SELECT id, name, size FROM groups")
    groups = cursor.fetchall()
    conn.close()

    return render_template("manage.html", groups=groups)
@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        group_name = request.form["group_name"]
        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]

        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()

        # 그룹 존재 여부 확인
        cursor.execute("SELECT id, size FROM groups WHERE name = ?", (group_name,))
        group = cursor.fetchone()

        if not group:
            flash("그룹이 존재하지 않습니다!", "danger")
            return redirect(url_for("home"))

        group_id, group_size = group

        # 중복 참가자 확인
        cursor.execute("SELECT id FROM participants WHERE group_id = ? AND name = ?", (group_id, name))
        existing_participant = cursor.fetchone()

        if existing_participant:
            flash(f"'{name}'님은 이미 등록되었습니다. 로그인 해주세요.", "info")
            return redirect(url_for("login"))

        # 참가자 추가
        cursor.execute("INSERT INTO participants (group_id, name, email, password) VALUES (?, ?, ?, ?)",
                       (group_id, name, email, password))
        conn.commit()

        # 현재 참가자 수 확인
        cursor.execute("SELECT COUNT(*) FROM participants WHERE group_id = ?", (group_id,))
        participant_count = cursor.fetchone()[0]

        # ✅ `n명`이 모두 등록되었을 때, 랜덤 매칭 실행 + 이메일 전송
        if participant_count == group_size:
            cursor.execute("SELECT COUNT(*) FROM matches WHERE group_id = ?", (group_id,))
            existing_matches = cursor.fetchone()[0]

            if existing_matches == 0:  # 매칭이 없을 경우에만 실행
                generate_random_matches(group_id)

                # 🔹 참가자 이메일 가져오기
                cursor.execute("SELECT email FROM participants WHERE group_id = ?", (group_id,))
                participant_emails = [row[0] for row in cursor.fetchall()]

                # 🔹 Secret Santa 시작 안내 이메일 전송 (매칭 결과 X)
                for recipient_email in participant_emails:
                    subject = "🎄 Secret Santa Party Has Started! 🎁"
                    body = f"""
                    <h1>🎄 The Secret Santa Party Has Begun! 🎁</h1>
                    <p>All participants have joined, and the matching is now complete!</p>
                    <p><strong>Log in to see who your Secret Santa match is!</strong></p>
                    <a href='http://127.0.0.1:5000/login'>Click Here to Log In</a>
                    <p>Have fun and enjoy the party! 🎅</p>
                    """
                    send_email(SENDER_EMAIL, SENDER_PASSWORD, recipient_email, subject, body)

                flash("모든 참가자가 등록 완료! 랜덤 매칭이 실행되었으며, 이메일이 전송되었습니다.", "success")
            else:
                flash("랜덤 매칭이 이미 완료되었습니다.", "info")

        conn.close()
        return redirect(url_for("home"))

    return render_template("index.html")


# @app.route("/", methods=["GET", "POST"])
# def home():
#     if request.method == "POST":
#         group_name = request.form["group_name"]
#         name = request.form["name"]
#         email = request.form["email"]
#         password = request.form["password"]

#         conn = sqlite3.connect("database.db")
#         cursor = conn.cursor()

#         cursor.execute("SELECT id, size FROM groups WHERE name = ?", (group_name,))
#         group = cursor.fetchone()

#         if not group:
#             flash("그룹이 존재하지 않습니다!", "danger")
#             return redirect(url_for("home"))

#         group_id, group_size = group

#         cursor.execute("SELECT COUNT(*) FROM participants WHERE group_id = ?", (group_id,))
#         participant_count = cursor.fetchone()[0]

#         if participant_count >= group_size:
#             flash("이미 등록되었습니다. 로그인을 해주세요.", "danger")
#             return redirect(url_for("login"))

#         cursor.execute("INSERT INTO participants (group_id, name, email, password) VALUES (?, ?, ?, ?)",
#                        (group_id, name, email, password))
#         conn.commit()

#         participant_count += 1
#         if participant_count == group_size:
#             generate_random_matches(group_id)
#             flash("모든 참가자가 등록 완료! 이메일이 발송됩니다.", "success")

#         conn.close()
#         return redirect(url_for("home"))
    
#     return render_template("index.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        group_name = request.form["group_name"]
        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]

        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()

        # 그룹과 사용자 확인
        cursor.execute("""
            SELECT p.id, p.group_id
            FROM participants p
            JOIN groups g ON p.group_id = g.id
            WHERE g.name = ? AND p.name = ? AND p.email = ? AND p.password = ?
        """, (group_name, name, email, password))
        user = cursor.fetchone()

        if user:
            user_id, group_id = user
            session["user_id"] = user_id
            session["group_id"] = group_id
            session["name"] = name

            flash("로그인 성공!", "success")
            return redirect(url_for("draw", group_id=group_id, name=name))  # ✅ 로그인 후 매칭 페이지로 이동
        else:
            flash("로그인 실패. 정보를 확인해주세요.", "danger")
            return redirect(url_for("login"))

    return render_template("login.html")

@app.route("/draw/<int:group_id>/<name>", methods=["GET"])
def draw(group_id, name):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    # 현재 사용자의 ID 가져오기
    cursor.execute("SELECT id FROM participants WHERE group_id = ? AND name = ?", (group_id, name))
    participant = cursor.fetchone()

    if not participant:
        flash("You are not part of this group!", "danger")
        conn.close()
        return redirect(url_for("home"))

    giver_id = participant[0]

    # 🔹 이미 생성된 랜덤 매칭을 불러오기
    cursor.execute("""
        SELECT receiver.id, receiver.name 
        FROM matches 
        JOIN participants AS receiver ON matches.receiver_id = receiver.id
        WHERE matches.group_id = ? AND matches.giver_id = ?
    """, (group_id, giver_id))
    match = cursor.fetchone()

    if not match:
        flash("매칭 정보가 없습니다. 모든 참가자가 등록되었는지 확인하세요.", "danger")
        conn.close()
        return redirect(url_for("home"))

    receiver_id, receiver_name = match
    conn.close()

    # ✅ result.html로 리다이렉트 (match 결과를 전달)
    return redirect(url_for("result", group_id=group_id, name=name))

@app.route("/send_message/<int:group_id>/<int:sender_id>/<int:receiver_id>", methods=["POST"])
def send_message(group_id, sender_id, receiver_id):
    if not session.get("user_id"):
        return jsonify({"success": False, "error": "Please log in to send messages."})

    text = request.form.get("message")
    reply_to = request.form.get("reply_to")  # 답장할 message id

    if not text:
        return jsonify({"success": False, "error": "Message cannot be empty."})

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    # 질문인지 답장인지 구분
    if reply_to:
        # 답장 저장
        cursor.execute(
            "UPDATE messages SET reply = ?, read = 0 WHERE id = ? AND receiver_id = ?",
            (text, reply_to, session["user_id"])
        )
        remaining_chances = None
    else:
        # 질문 저장 (최대 3회 제한)
        cursor.execute(
            "SELECT COUNT(*) FROM messages WHERE sender_id = ? AND group_id = ?",
            (sender_id, group_id)
        )
        used = cursor.fetchone()[0]
        if used >= 3:
            conn.close()
            return jsonify({"success": False, "error": "No remaining chances to ask questions."})

        cursor.execute(
            "INSERT INTO messages (group_id, sender_id, receiver_id, message) VALUES (?, ?, ?, ?)",
            (group_id, sender_id, receiver_id, text)
        )
        remaining_chances = 3 - (used + 1)

    conn.commit()
    conn.close()

    
    return jsonify({"success": True, "remaining_chances": remaining_chances})

@app.route("/result/<int:group_id>/<name>", methods=["GET"])
def result(group_id, name):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    # 현재 사용자의 ID 가져오기
    cursor.execute("SELECT id FROM participants WHERE group_id = ? AND name = ?", (group_id, name))
    participant = cursor.fetchone()

    if not participant:
        flash("You are not part of this group!", "danger")
        conn.close()
        return redirect(url_for("home"))

    giver_id = participant[0]

    # 매칭 상대 가져오기
    cursor.execute("""
        SELECT receiver.id, receiver.name 
        FROM matches 
        JOIN participants AS receiver ON matches.receiver_id = receiver.id
        WHERE matches.group_id = ? AND matches.giver_id = ?
    """, (group_id, giver_id))
    match = cursor.fetchone()

    if not match:
        flash("매칭 정보가 없습니다. 모든 참가자가 등록되었는지 확인하세요.", "danger")
        conn.close()
        return redirect(url_for("home"))

    receiver_id, receiver_name = match

    # 남은 질문 횟수 확인
    cursor.execute("""
        SELECT COUNT(*) FROM messages WHERE sender_id = ? AND group_id = ?
    """, (giver_id, group_id))
    used_chances = cursor.fetchone()[0]
    remaining_chances = max(3 - used_chances, 0)

    # 📌 읽지 않은 메시지 개수 확인
    cursor.execute("""
        SELECT COUNT(*) FROM messages WHERE receiver_id = ? AND group_id = ? AND read = 0
    """, (giver_id, group_id))
    unread_count = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*) FROM messages
        WHERE sender_id = ? AND group_id = ? AND reply IS NOT NULL
    """, (giver_id, group_id))
    reply_count = cursor.fetchone()[0]


    conn.close()

    return render_template("result.html", 
                           name=name, 
                           match=receiver_name, 
                           group_id=group_id, 
                           giver_id=giver_id, 
                           receiver_id=receiver_id, 
                           remaining_chances=remaining_chances, 
                           unread_count=unread_count,  # ✅ unread_count 추가
                           reply_count=reply_count) 


def generate_random_matches(group_id):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    # 참가자 ID 가져오기
    cursor.execute("SELECT id FROM participants WHERE group_id = ?", (group_id,))
    participant_ids = [p[0] for p in cursor.fetchall()]
    
    if len(participant_ids) < 2:
        flash("매칭을 실행할 최소한의 참가자가 필요합니다!", "danger")
        conn.close()
        return
    
    # 랜덤으로 섞기
    random.shuffle(participant_ids)

    # 매칭 생성 (자신을 뽑지 않도록)
    for i in range(len(participant_ids)):
        giver_id = participant_ids[i]
        receiver_id = participant_ids[(i + 1) % len(participant_ids)]
        cursor.execute("INSERT INTO matches (group_id, giver_id, receiver_id) VALUES (?, ?, ?)",
                       (group_id, giver_id, receiver_id))

    conn.commit()
    conn.close()

@app.route("/inbox/<int:group_id>", methods=["GET", "POST"])
def inbox(group_id):
    if "user_id" not in session:
        flash("Please log in to check your inbox.", "danger")
        return redirect(url_for("login"))

    user_id = session["user_id"]
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    if request.method == "POST":
        # 메시지 읽음 처리
        cursor.execute("""
            UPDATE messages
            SET read = 1
            WHERE receiver_id = ? AND group_id = ?
        """, (user_id, group_id))
        conn.commit()

    # 받은 메시지 가져오기 (읽음 여부 포함)
    cursor.execute("""
        SELECT id, message, reply, read, sender_id
        FROM messages
        WHERE receiver_id = ? AND group_id = ?
        ORDER BY sent_at DESC
    """, (user_id, group_id))
    messages = cursor.fetchall()

    # 읽지 않은 메시지 개수 확인
    unread_count = sum(1 for msg in messages if msg[3] == 0)

    conn.close()
    return render_template("inbox.html", messages=messages, name=session.get("name"), group_id=group_id, unread_count=unread_count)


@app.route("/mark_messages_read/<int:group_id>", methods=["POST"])
def mark_messages_read(group_id):
    if "user_id" not in session:
        return jsonify({"success": False, "error": "Please log in."})

    user_id = session["user_id"]
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE messages
        SET read = 1
        WHERE receiver_id = ? AND group_id = ?
    """, (user_id, group_id))
    conn.commit()
    conn.close()

    return jsonify({"success": True})



@app.route("/sent_messages/<int:group_id>", methods=["GET"])
def sent_messages(group_id):
    if "user_id" not in session:
        flash("Please log in to view your sent messages.", "danger")
        return redirect(url_for("login"))

    user_id = session["user_id"]
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    # 보낸 메시지와 답장 가져오기
    cursor.execute("""
        SELECT message, reply
        FROM messages
        WHERE sender_id = ? AND group_id = ?
        ORDER BY sent_at DESC
    """, (user_id, group_id))
    sent_messages = cursor.fetchall()

    conn.close()

    return render_template("sent_messages.html", messages=sent_messages, name=session.get("name"), group_id=group_id)


if __name__ == "__main__":
    with app.app_context():
        init_db()
    app.run(debug=True)
