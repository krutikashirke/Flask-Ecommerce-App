
from flask import Flask, render_template, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user, UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True)
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(200))

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    price = db.Column(db.Float)
    description = db.Column(db.String(255))
    image_url = db.Column(db.String(255))
    category = db.Column(db.String(100))

class CartItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'))
    quantity = db.Column(db.Integer, default=1)
    product = db.relationship('Product')

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    total = db.Column(db.Float)
    order_date = db.Column(db.DateTime, default=datetime.utcnow)


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


@app.route('/')
def home():
    category = request.args.get('category')
    sort = request.args.get('sort')
    min_price = request.args.get('min_price', type=float)
    max_price = request.args.get('max_price', type=float)

    query = Product.query
    if category:
        query = query.filter_by(category=category)
    if min_price is not None:
        query = query.filter(Product.price >= min_price)
    if max_price is not None:
        query = query.filter(Product.price <= max_price)

    if sort == "low":
        query = query.order_by(Product.price.asc())
    elif sort == "high":
        query = query.order_by(Product.price.desc())

    products = query.all()
    categories = db.session.query(Product.category).distinct().all()
    categories = [c[0] for c in categories if c[0]]

    return render_template('home.html', products=products, categories=categories)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = generate_password_hash(request.form['password'])
        user = User(username=username, email=email, password=password)
        db.session.add(user)
        db.session.commit()
        flash('Registered successfully!')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user and check_password_hash(user.password, request.form['password']):
            login_user(user)
            return redirect(url_for('home'))
        flash('Invalid credentials!')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

@app.route('/add-to-cart/<int:product_id>')
@login_required
def add_to_cart(product_id):
    item = CartItem.query.filter_by(user_id=current_user.id, product_id=product_id).first()
    if item:
        item.quantity += 1
    else:
        item = CartItem(user_id=current_user.id, product_id=product_id, quantity=1)
        db.session.add(item)
    db.session.commit()
    flash('Item added to cart!')
    return redirect(url_for('home'))

@app.route('/cart')
@login_required
def view_cart():
    items = CartItem.query.filter_by(user_id=current_user.id).all()
    total = sum(item.product.price * item.quantity for item in items)
    return render_template('cart.html', items=items, total=total)

@app.route('/checkout')
@login_required
def checkout():
    items = CartItem.query.filter_by(user_id=current_user.id).all()
    total = sum(item.product.price * item.quantity for item in items)
    order = Order(user_id=current_user.id, total=total)
    db.session.add(order)
    CartItem.query.filter_by(user_id=current_user.id).delete()
    db.session.commit()
    return render_template('checkout.html', total=total)

@app.route('/orders')
@login_required
def order_history():
    orders = Order.query.filter_by(user_id=current_user.id).all()
    return render_template('orders.html', orders=orders)


if __name__ == '__main__':
    with app.app_context():
        if os.path.exists("database.db"):
            os.remove("database.db")
        db.create_all()

        if not Product.query.first():
            sample_products = [
                # Men's Wear
                {"name": f"Men's Wear Product {i+1}", "price": 100+i*50, "category": "Men's Wear",
                 "description": f"Stylish and comfortable men's wear #{i+1}.",
                 "image_url": "https://cdn-icons-png.flaticon.com/512/892/892458.png"} for i in range(10)
            ] + [
                # Ladies' Wear
                {"name": f"Ladies' Wear Product {i+1}", "price": 100+i*50, "category": "Ladies' Wear",
                 "description": f"Elegant and modern ladies' wear #{i+1}.",
                 "image_url": "https://cdn-icons-png.flaticon.com/512/892/892432.png"} for i in range(10)
            ] + [
                # Makeup
                {"name": f"Makeup Product {i+1}", "price": 120+i*30, "category": "Makeup",
                 "description": f"Premium makeup product #{i+1}.",
                 "image_url": "/static/images/makeup.jpeg"} for i in range(10)
            ]

            for item in sample_products:
                product = Product(
                    name=item["name"],
                    price=item["price"],
                    category=item["category"],
                    description=item["description"],
                    image_url=item["image_url"]
                )
                db.session.add(product)

            db.session.commit()

    app.run(debug=True)
