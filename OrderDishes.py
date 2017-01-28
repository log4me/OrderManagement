# coding=UTF-8
from flask import Flask, request, session, g, redirect, url_for, abort, render_template, flash, make_response
import sqlite3
import os
import json
from werkzeug.utils import secure_filename

app = Flask(__name__)
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'static', 'images').replace('/', '\\')
ALLOWED_EXTENSIONS = set(['jpg', 'png', 'JPG', 'PNG'],)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config.update(dict(
    DATABASE=os.path.join(app.root_path, 'OrderDishes.db'),
    DEBUG=True,
    SECRET_KEY='development key',
))


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS


#  -------------------数据库连接start-------------------
def connect_db():
    rv = sqlite3.connect(app.config['DATABASE'])
    rv.row_factory = sqlite3.Row
    return rv


def get_db():
    if not hasattr(g, 'sqlite_db'):  # 判断g对象是否有sqlite_db属性
        g.sqlite_db = connect_db()
    return g.sqlite_db


@app.teardown_appcontext
def close_db(error):
    if hasattr(g, 'sqlite_db'):
        g.sqlite_db.close()
#  ------------------数据库连接end----------------------------

# TODO table显示bug


#  ------------------用户部分start--------------------
@app.route('/')
def index():
    db = get_db()
    cur = db.execute("select * from dish where isSpecial = 1")
    dishes = cur.fetchall()
    data = dict()
    data['title'] = u'特色菜'
    data['dishes'] = dishes
    return render_template('show_dishes.html', data=data)


@app.route('/search')
def search():
    name = request.args.get('q', None)
    if name:
        db = get_db()
        cur = db.execute("select * from dish where name like ?", ('%'+name+'%',))
        dishes = cur.fetchall()
        data = dict()
        data['title'] = u'搜索结果'
        data['dishes'] = dishes
        return render_template('show_dishes.html', data=data)
    else:
        return redirect(url_for('index'))


@app.route('/subclass/<subclass>', methods=['GET'])
def subclass(subclass):
    if request.method == 'GET':
        db = get_db()
        data = dict()
        if subclass == 'all':
            cur = db.execute("select * from dish")
            data['title'] = u'查看全部'
        else:
            cur = db.execute("select * from dish where subclass = ?", (subclass,))
            data['title'] = subclass
        dishes = cur.fetchall()
        data['dishes'] = dishes
        return render_template('show_dishes.html', data=data)


@app.route('/shopping_cart', methods=['GET'])
def shopping_cart():
    if request.method == 'GET':
        data = dict()
        if 'ID' in request.cookies:
            dishes = list()
            IDs = json.loads(request.cookies['ID'])
            db = get_db()
            for ID in IDs:
                cur = db.execute("select * from dish where ID = ?", (ID,))
                dish = cur.fetchone()
                dishes.append(dish)
            data['dishes'] = dishes
        return render_template('shopping_cart.html', data=data)


@app.route('/place_order')
def place_order():
    if 'ID' in request.cookies:
        db = get_db()
        db.execute("insert into [order] values(random(), ?, 0, datetime('now', 'localtime'))", (request.cookies['ID'],))
        db.commit()
        resp = make_response(redirect(url_for('index')))
        resp.set_cookie('ID', json.dumps([]))
    return resp
#  --------------------用户部分end-----------------------


#  ------------------管理员部分start-------------------
@app.route('/login', methods=['POST'])
def login():
    error = None
    db = get_db()
    if request.method == 'POST':
        cur = db.execute("select * from user where username = ?" ,(request.form['username'],))
        res = cur.fetchone()
        if not res:
            error = '不存在该用户名'
        elif res[1] != request.form['password']:
            error = '密码错误'
        else:
            session['logged_in'] = True
            session['username'] = request.form['username']
            flash("登录成功！")
            return redirect(url_for('admin'))
    return render_template('show_dishes.html', error=error)


@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    session.pop('username', None)
    flash("退出成功！")
    return redirect(url_for('index'))


@app.route('/admin')
def admin():
    if not session.get('logged_in'):
        abort(401)
    db = get_db()
    cur = db.execute("select * from dish")
    dishes = cur.fetchall()
    data = dict()
    data['title'] = u'菜品管理'
    data['username'] = session.get('username')
    data['dishes'] = dishes
    return render_template('admin.html', data=data)


@app.route('/admin/search')
def admin_search():
    if not session.get('logged_in'):
        abort(401)
    name = request.args.get('q', None)
    if name:
        db = get_db()
        cur = db.execute("select * from dish where name like ?", ('%'+name+'%',))
        dishes = cur.fetchall()
        data = dict()
        data['title'] = u'搜索结果'
        data['username'] = session.get('username')
        data['dishes'] = dishes
        return render_template('admin.html', data=data)
    else:
        return redirect(url_for('admin'))


@app.route('/admin/subclass/<subclass>', methods=['GET'])
def admin_subclass(subclass):
    if request.method == 'GET':
        db = get_db()
        cur = db.execute("select * from dish where subclass = ?", (subclass,))
        dishes = cur.fetchall()
        data = dict()
        data['title'] = subclass
        data['username'] = session.get('username')
        data['dishes'] = dishes
        return render_template('admin.html', data=data)


@app.route('/order')
def order():
    db = get_db()
    cur = db.execute("select * from [order]")
    orders = cur.fetchall()
    data = dict()
    data['title'] = u'查看订单'
    data['username'] = session.get('username')
    data['orders'] = orders
    return render_template("order.html", data=data)


@app.route('/order/<orderNo>')
def order_detail(orderNo):
    db = get_db()
    data = dict()
    data['title'] = u'订单号'+orderNo
    data['username'] = session.get('username')
    data['orderNo'] = orderNo
    cur = db.execute("select dishID from [order] where orderNo = ?", (orderNo,))
    dishIDs = cur.fetchone()
    if dishIDs:
        dishes = list()
        dishIDs = json.loads(dishIDs[0])
        for dishID in dishIDs:
            cur = db.execute("select * from dish where ID = ?", (dishID,))
            res = cur.fetchone()
            dishes.append(res)
        data['dishes'] = dishes
    return render_template("order_detail.html", data=data)


@app.route('/complete_order/<orderNo>')
def complete_order(orderNo):
    if not session.get('logged_in'):
        abort(401)
    db = get_db()
    db.execute("update [order] set isComplete = 1 where orderNo = ?", (orderNo,))
    db.commit()
    return redirect(url_for('order'))


@app.route('/add_dish', methods=['GET', 'POST'])
def add_dish():
    if request.method == 'GET':
        data = dict()
        data['username'] = session.get('username')
        data['title'] = u'添加新菜'
        data['dish'] = {}
        data['url'] = 'add_dish'
        return render_template('edit_dish.html', data=data)
    elif request.method == 'POST':
        if not session.get('logged_in'):
            abort(401)
        f = request.files['image']
        if f and allowed_file(f.filename):
            fname = secure_filename(f.filename)
            f.save(os.path.join(app.config['UPLOAD_FOLDER'], fname))
        db = get_db()
        db.execute("insert into dish(name, price, subclass, image, isSpecial, createTime) values (?, ?, ?, ?, ?, datetime('now', 'localtime'))",
                   (request.form['name'], request.form['price'], request.form['subclass'], 'images/'+secure_filename(f.filename), request.form['isSpecial']))
        db.commit()
        flash("新的菜品添加成功！")
        return redirect(url_for('admin'))


@app.route('/delete/<ID>', methods=['POST'])
def delete_dish(ID):
    if not session.get('logged_in'):
        abort(401)
    db = get_db()
    db.execute("delete from dish where ID = ?", (ID,))
    db.commit()
    flash("删除成功！")
    return redirect(url_for('admin'))


@app.route('/update/<ID>', methods=['GET', 'POST'])
def update_dish(ID):
    if request.method == 'GET':
        if not session.get('logged_in'):
            abort(401)
        data = dict()
        data['username'] = session.get('username')
        data['title'] = u'修改菜品'
        db = get_db()
        cur = db.execute("select * from dish where ID=?", (ID,))
        dish = cur.fetchone()
        data['dish'] = dish
        data['url'] = ID
        return render_template('edit_dish.html', data=data)
    elif request.method == 'POST':
        if not session.get('logged_in'):
            abort(401)
        db = get_db()
        f = request.files['image']
        if f and allowed_file(f.filename):
            fname = secure_filename(f.filename)
            f.save(os.path.join(app.config['UPLOAD_FOLDER'], fname))
            db.execute("update dish set name = ?, price = ?, subclass = ?, isSpecial = ?, image = ? where ID = ?",
                       (request.form['name'], request.form['price'], request.form['subclass'], request.form['isSpecial'], 'images/'+secure_filename(f.filename), ID))
        else:
            db.execute("update dish set name = ?, price = ?, subclass = ?, isSpecial = ? where ID = ?", (request.form['name'], request.form['price'], request.form['subclass'], request.form['isSpecial'], ID))
        db.commit()
        flash("更新成功！")
        return redirect(url_for('admin'))
#  ------------------管理员部分end-------------------

if __name__ == '__main__':
    app.run()
