from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///task_manager.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    task_lists = db.relationship('TaskList', backref='owner', lazy=True)

class TaskList(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    tasks = db.relationship('Task', backref='task_list', lazy=True)

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    done = db.Column(db.Boolean, default=False)
    task_list_id = db.Column(db.Integer, db.ForeignKey('task_list.id'), nullable=False)

with app.app_context():
    db.create_all()

def is_logged_in():
    return 'user_id' in session

@app.context_processor
def inject_user():
    return dict(is_logged_in=is_logged_in)

@app.route('/')
def index():
    if not is_logged_in():
        return redirect(url_for('login'))
    
    user = User.query.get(session['user_id'])
    
    task_lists = TaskList.query.filter_by(user_id=user.id).all()
    
    task_lists_dict = {user.username: task_lists}
    
    return render_template('index.html', task_lists=task_lists_dict)

@app.route('/list/<int:list_id>')
def view_list(list_id):
    if not is_logged_in():
        return redirect(url_for('login'))
    
    task_list = TaskList.query.get_or_404(list_id)
    tasks = Task.query.filter_by(task_list_id=task_list.id).all()
    return render_template('list.html', task_list=task_list, tasks=tasks)

@app.route('/add_task/<int:list_id>', methods=['POST'])
def add_task(list_id):
    if not is_logged_in():
        return redirect(url_for('login'))
    
    title = request.form['title']
    if title:
        task_list = TaskList.query.get_or_404(list_id)
        new_task = Task(title=title, task_list_id=task_list.id)
        db.session.add(new_task)
        db.session.commit()
    return redirect(url_for('view_list', list_id=list_id))


@app.route('/remove_task/<int:task_id>')
def remove_task(task_id):
    if not is_logged_in():
        return redirect(url_for('login'))
    
    task = Task.query.get_or_404(task_id)
    task_list_id = task.task_list_id
    db.session.delete(task)
    db.session.commit()
    return redirect(url_for('view_list', list_id=task_list_id))

@app.route('/create_list', methods=['POST'])
def create_list():
    if not is_logged_in():
        return redirect(url_for('login'))
    
    list_name = request.form['list_name']
    if list_name:
        user = User.query.get(session['user_id'])
        new_list = TaskList(name=list_name, user_id=user.id)
        db.session.add(new_list)
        db.session.commit()
    return redirect(url_for('index'))

@app.route('/delete_list/<int:list_id>')
def delete_list(list_id):
    if not is_logged_in():
        return redirect(url_for('login'))
    
    task_list = TaskList.query.get_or_404(list_id)
    db.session.delete(task_list)
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed_password = generate_password_hash(password)
        
        if User.query.filter_by(username=username).first():
            return "Username already exists."
        
        new_user = User(username=username, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            return redirect(url_for('index'))
        else:
            return "Invalid username or password"
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500

if __name__ == '__main__':
    app.run(debug=True, port=3000)