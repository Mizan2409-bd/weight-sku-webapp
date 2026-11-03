import os
from datetime import datetime
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import func

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "change-this-before-deployment")
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///weight_sku.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default="user", nullable=False)
    active = db.Column(db.Boolean, default=True)

class Material(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    material_code = db.Column(db.String(40), unique=True, nullable=False, index=True)
    description = db.Column(db.String(300), nullable=False)
    sku_weight_kg = db.Column(db.Float, default=0)
    wrapper_weight_kg = db.Column(db.Float, default=0)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Delivery(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    delivery_date = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    truck_no = db.Column(db.String(80), nullable=False)
    party_name = db.Column(db.String(200), default="")
    material_code = db.Column(db.String(40), nullable=False, index=True)
    description = db.Column(db.String(300), default="")
    qty = db.Column(db.Float, default=0)
    mt = db.Column(db.Float, default=0)
    entered_by = db.Column(db.String(80), default="")

def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapper

def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if session.get("role") != "admin":
            flash("এই কাজের জন্য Admin access প্রয়োজন।", "error")
            return redirect(url_for("dashboard"))
        return fn(*args, **kwargs)
    return wrapper

@app.route("/")
def home():
    return redirect(url_for("dashboard") if "user_id" in session else url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = User.query.filter_by(username=request.form.get("username","").strip(), active=True).first()
        if user and check_password_hash(user.password_hash, request.form.get("password","")):
            session.update(user_id=user.id, username=user.username, role=user.role)
            return redirect(url_for("dashboard"))
        flash("Username অথবা Password সঠিক নয়।", "error")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html",
        material_count=Material.query.count(),
        delivery_count=Delivery.query.count(),
        total_qty=db.session.query(func.coalesce(func.sum(Delivery.qty),0)).scalar(),
        total_mt=db.session.query(func.coalesce(func.sum(Delivery.mt),0)).scalar())

@app.route("/materials")
@login_required
def materials():
    q=request.args.get("q","").strip()
    query=Material.query
    if q:
        query=query.filter(db.or_(Material.material_code.contains(q), Material.description.contains(q)))
    return render_template("materials.html", materials=query.order_by(Material.material_code).limit(1000).all(), q=q)

@app.route("/materials/add", methods=["POST"])
@login_required
@admin_required
def add_material():
    code=request.form.get("material_code","").strip()
    desc=request.form.get("description","").strip()
    if not code or not desc:
        flash("Material Code এবং Description দিতে হবে।","error")
    else:
        row=Material.query.filter_by(material_code=code).first()
        if row:
            row.description=desc
            row.sku_weight_kg=float(request.form.get("sku_weight_kg") or 0)
            row.wrapper_weight_kg=float(request.form.get("wrapper_weight_kg") or 0)
        else:
            db.session.add(Material(material_code=code, description=desc,
                sku_weight_kg=float(request.form.get("sku_weight_kg") or 0),
                wrapper_weight_kg=float(request.form.get("wrapper_weight_kg") or 0)))
        db.session.commit()
        flash("Material সংরক্ষণ হয়েছে।","success")
    return redirect(url_for("materials"))

@app.route("/deliveries")
@login_required
def deliveries():
    rows=Delivery.query.order_by(Delivery.delivery_date.desc(),Delivery.id.desc()).limit(500).all()
    return render_template("deliveries.html", rows=rows)

@app.route("/deliveries/add", methods=["POST"])
@login_required
def add_delivery():
    try:
        db.session.add(Delivery(
            delivery_date=datetime.strptime(request.form.get("delivery_date"),"%Y-%m-%d").date(),
            truck_no=request.form.get("truck_no","").strip(),
            party_name=request.form.get("party_name","").strip(),
            material_code=request.form.get("material_code","").strip(),
            description=request.form.get("description","").strip(),
            qty=float(request.form.get("qty") or 0), mt=float(request.form.get("mt") or 0),
            entered_by=session.get("username","")))
        db.session.commit()
        flash("Delivery entry সংরক্ষণ হয়েছে।","success")
    except Exception:
        db.session.rollback()
        flash("Entry সঠিকভাবে দেওয়া হয়নি। তারিখ, Material, Qty ও MT পরীক্ষা করুন।","error")
    return redirect(url_for("deliveries"))

@app.route("/admin/users", methods=["GET","POST"])
@login_required
@admin_required
def users():
    if request.method=="POST":
        username=request.form.get("username","").strip()
        password=request.form.get("password","")
        role=request.form.get("role","user")
        if username and password and role in ("admin","user") and not User.query.filter_by(username=username).first():
            db.session.add(User(username=username,password_hash=generate_password_hash(password),role=role))
            db.session.commit()
            flash("নতুন User তৈরি হয়েছে।","success")
        else:
            flash("তথ্য অসম্পূর্ণ অথবা Username আগে থেকেই আছে।","error")
    return render_template("users.html", users=User.query.order_by(User.username).all())

@app.cli.command("init-db")
def init_db():
    db.create_all()
    if not User.query.filter_by(username="admin").first():
        db.session.add(User(username="admin",password_hash=generate_password_hash(os.environ.get("ADMIN_PASSWORD","ChangeMe123!")),role="admin"))
        db.session.commit()
    print("Database ready. Default login: admin / ChangeMe123! (change immediately)")

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",5000)), debug=True)
