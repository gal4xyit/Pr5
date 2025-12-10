from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask import jsonify
from flask_socketio import SocketIO, emit, send

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secretkey123'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///todo.db'
socketio = SocketIO(app)

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)


class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.String(500))


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.route('/')
def home():
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/form', methods=['GET', 'POST'])
def simple_form():
    greeting = None
    if request.method == 'POST':
        name = request.form.get('name')
        greeting = f"Привіт, {name}!"
    return render_template('form.html', greeting=greeting)


@app.route('/tasks', methods=['GET', 'POST'])
def tasks():
    if request.method == 'POST':
        if not current_user.is_authenticated:
            flash('Тільки авторизовані користувачі можуть додавати завдання!')
            return redirect(url_for('login'))

        title = request.form.get('title')
        description = request.form.get('description')

        new_task = Task(title=title, description=description)
        db.session.add(new_task)
        db.session.commit()

        socketio.emit('new_task_notification', {'title': title})

        return redirect(url_for('tasks'))

    all_tasks = Task.query.all()
    return render_template('tasks.html', tasks=all_tasks)

@app.route('/tasks/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_task(id):
    task = Task.query.get_or_404(id)
    if request.method == 'POST':
        task.title = request.form.get('title')
        task.description = request.form.get('description')
        db.session.commit()
        return redirect(url_for('tasks'))
    return render_template('edit_task.html', task=task)


@app.route('/tasks/delete/<int:id>')
@login_required
def delete_task(id):
    task = Task.query.get_or_404(id)
    db.session.delete(task)
    db.session.commit()
    return redirect(url_for('tasks'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        hashed_pw = generate_password_hash(password, method='scrypt')
        new_user = User(username=username, password=hashed_pw)
        try:
            db.session.add(new_user)
            db.session.commit()
            return redirect(url_for('login'))
        except:
            flash("Такий користувач вже існує")
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('tasks'))
        else:
            flash('Невірний логін або пароль')
    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))


@app.route('/api/tasks', methods=['GET'])
def get_tasks_api():
    tasks = Task.query.all()
    output = [{'id': t.id, 'title': t.title, 'description': t.description} for t in tasks]
    return jsonify({'tasks': output})


@app.route('/api/tasks', methods=['POST'])
def create_task_api():
    data = request.get_json()
    if not data or not 'title' in data:
        return jsonify({'message': 'No title provided'}), 400

    new_task = Task(title=data['title'], description=data.get('description', ''))
    db.session.add(new_task)
    db.session.commit()
    return jsonify({'message': 'Task created', 'id': new_task.id}), 201


@app.route('/api/tasks/<int:id>', methods=['DELETE'])
def delete_task_api(id):
    task = Task.query.get_or_404(id)
    db.session.delete(task)
    db.session.commit()
    return jsonify({'message': 'Task deleted'})


@app.route('/api/tasks/<int:id>', methods=['PUT'])
def update_task_api(id):
    task = Task.query.get_or_404(id)
    data = request.get_json()
    task.title = data.get('title', task.title)
    task.description = data.get('description', task.description)
    db.session.commit()
    return jsonify({'message': 'Task updated'})


@app.route('/chat')
@login_required
def chat():
    return render_template('chat.html')


@socketio.on('message')
def handle_message(msg):
    print('Message: ' + msg)
    send(msg, broadcast=True)


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    socketio.run(app, debug=True)