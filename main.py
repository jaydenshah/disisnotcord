from flask import Flask, render_template, request, flash, redirect, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
from flask_login import LoginManager, login_required, login_user, logout_user, UserMixin, current_user
from flask_socketio import SocketIO
from datetime import date
import uuid
import os

app = Flask(__name__)
app.config["SECRET_KEY"] = "lmao"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"
app.config["UPLOAD_FOLDER"] = "attachments"
socketio = SocketIO(app)
db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.login_message = "Please log in to access this page"
login_manager.login_message_category = "error"
login_manager.login_view = "/login"
login_manager.init_app(app)

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(128), nullable=False)
    accountcreated = db.Column(db.String(16), nullable=False)
    pfp = db.Column(db.String(36), nullable=False)
    bio = db.Column(db.String(200), nullable=False)
    status = db.Column(db.String(128), nullable=False)
    dms = db.relationship("UserDM")
    messagessent = db.relationship("Message")

class UserDM(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    userid = db.Column(db.Integer, db.ForeignKey("user.id"))
    dmid = db.Column(db.Integer, db.ForeignKey("dm.id"))

class DM(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(36), nullable=False)
    users = db.relationship("UserDM")
    messages = db.relationship("Message")

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    dmid = db.Column(db.Integer, db.ForeignKey("dm.id"))
    senderid = db.Column(db.Integer, db.ForeignKey("user.id"))
    content = db.Column(db.Text, nullable=False)
    date = db.Column(db.String(64), nullable=False)

@login_manager.user_loader
def load_user(id):
    return User.query.get(int(id))

@app.errorhandler(404)
def page_not_found(e):
    return render_template("404.html")

@app.route("/")
def home():
    if current_user.is_authenticated:
        return redirect("/message")
    return render_template("home.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        user = User.query.filter_by(username=username).first()
        if user:
            if password == user.password:
                login_user(user, remember=True)
                flash("Login successful", category="success")
                return redirect("/")
            else:
                flash("Incorrect password!", category="error")
        else:
            flash("Account does not exist!", category="error")

    return render_template("login.html")

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form.get("username")
        password1 = request.form.get("password1")
        password2 = request.form.get("password2")

        user = User.query.filter(func.lower(User.username) == username.lower()).first()
        if user:
            flash("Account already exists!", category="error")
        elif password1 != password2:
            flash("Passwords do not match!", category="error")
        else:
            today = date.today().strftime("%d %b %Y")
            newuser = User(username=username, password=password1, accountcreated=today, pfp="404", bio="", status="")
            db.session.add(newuser)
            db.session.commit()
            login_user(newuser, remember=True)
            flash("Account created", category="success")
            return redirect("/")
    return render_template("signup.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect("/")

@app.route("/editprofile", methods=["GET", "POST"])
@login_required
def editprofile():
    if request.method == "POST":
        user = User.query.filter_by(id=current_user.id).first()
        pfp = request.files["pfp"]
        if pfp.filename != "":
            filename = str(uuid.uuid4())
            fileextension = pfp.filename.split(".")[1]
            file_path = os.path.join(app.config["UPLOAD_FOLDER"], f"{filename}.{fileextension}")
            pfp.save(file_path)
            user.pfp = f"{filename}.{fileextension}"
        bio = request.form.get("bio")
        user.bio = bio
        db.session.commit()
        flash("Updated profile", category="success")
        return redirect("/message")

    return render_template("editprofile.html")

@app.route("/profile/<string:username>")
def profile(username):
    user_profile = User.query.filter_by(username=username).first()
    if user_profile:
        return render_template("profile.html", user_profile=user_profile)
    return render_template("404.html")

@app.route("/attachments/<string:filename>")
def attachments(filename):
    path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    if os.path.isfile(path):
        return send_from_directory(app.config["UPLOAD_FOLDER"], filename)
    else:
        return send_from_directory(app.config["UPLOAD_FOLDER"], "404.jpg")

@app.route("/message", methods=["GET", "POST"])
@login_required
def message():
    if request.method == "POST":
        if request.form.get("createdm"):
            print(request.form.get("createdm"))
            username = request.form.get("createdm")
            user = User.query.filter_by(username=username).first()
            if user:
                if user != current_user:
                    uuidvar = str(uuid.uuid4())
                    dm = DM(uuid=uuidvar)
                    userdmids = [i.dmid for i in user.dms]
                    currentuserdmids = [i.dmid for i in current_user.dms]
                    for dmid in currentuserdmids:
                        if dmid in userdmids:
                            dm = DM.query.filter_by(id=dmid).first()
                            return redirect(f"/message/{dm.uuid}")
                    db.session.add(dm)
                    db.session.commit()
                    dmid = DM.query.filter_by(uuid=uuidvar).first().id
                    userdm = UserDM(userid=current_user.id, dmid=dmid)
                    userdm2 = UserDM(userid=user.id, dmid=dmid)
                    db.session.add(userdm)
                    db.session.add(userdm2)
                    db.session.commit()
                    return redirect(f"/message/{uuidvar}")
                else:
                    flash("Imagine having no friends and messaging yourself, only to fail at that...", category="error")
            else:
                flash("User does not exist!", category="error")
        else:
            status = request.form.get("status")
            current_user.status = status
            db.session.commit()
            flash("Custom status set!", category="success")
    dms = []
    for userdm in current_user.dms:
        dm = DM.query.filter_by(id=userdm.dmid).first()
        otheruser = User.query.filter_by(id=[i.userid for i in dm.users if i.userid != current_user.id][0]).first()
        dms.append([otheruser, dm])
    return render_template("message.html", dms=dms)

@app.route("/message/<string:uuid>")
@login_required
def messageroom(uuid):
    dm = DM.query.filter_by(uuid=uuid).first()
    if dm:
        if current_user.id in [userdm.userid for userdm in dm.users]:
            otheruser = User.query.filter_by(id=[i.userid for i in dm.users if i.userid != current_user.id][0]).first()
            messages = Message.query.filter_by(dmid=dm.id).all()
            authors = [User.query.filter_by(id=message.senderid).first() for message in messages]
            return render_template("messageroom.html", dm=dm, otheruser=otheruser, messages=messages, authors=authors)
    return render_template("404.html")

@socketio.on("connect")
def handle_connect():
    print("Client connected")

@socketio.on("message_sent")
def handle_message_sent(data):
    content = data["content"]
    author = User.query.filter_by(username=data["author"]).first()
    date = data["date"]
    dmid = data["dmid"]
    message = Message(dmid=int(dmid), senderid=author.id, content=content, date=date)
    db.session.add(message)
    db.session.commit()
    socketio.emit("update_chat", {"dmid": dmid, "author": author.username, "authorpfp": author.pfp, "content": content, "date": date})

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    socketio.run(app, debug=True, host="0.0.0.0", allow_unsafe_werkzeug=True, port=80)