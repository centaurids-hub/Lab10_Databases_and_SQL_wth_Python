# Exercise 3: Profile Management with Image Upload

from flask import Flask, render_template, request, redirect, url_for, flash, session
import sqlite3
import os
from werkzeug.utils import secure_filename
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this-in-production'

# Configuration
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

# Create upload directory if it doesn't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_db():
    """Get database connection"""
    conn = sqlite3.connect('profiles.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize database tables"""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            display_name TEXT,
            email TEXT,
            image_filename TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Insert sample users if empty (K-pop idols edition)
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        sample_users = [
            ("chaeyoung", "Son Chaeyoung", "chaeyoung@tup.edu", None),
            ("ningning", "Ning Yizhuo", "ningning@tup.edu", None),
            ("karina", "Yu Ji-min", "karina@tup.edu", None),
            ("asa", "Enami Asa", "asa@tup.edu", None),
            ("giselle", "Aeri Uchinaga", "giselle@tup.edu", None)
        ]
        cursor.executemany("""
            INSERT INTO users (username, display_name, email, image_filename)
            VALUES (?, ?, ?, ?)
        """, sample_users)

    conn.commit()
    conn.close()
    print("✓ Database initialized!")

@app.route('/')
def index():
    """Home page - list all users"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users ORDER BY display_name")
    users = cursor.fetchall()
    conn.close()
    return render_template('index.html', users=users)

@app.route('/profile/<username>')
def profile(username):
    """View individual profile"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
    user = cursor.fetchone()
    conn.close()

    if user is None:
        flash('User not found!', 'error')
        return redirect(url_for('index'))

    return render_template('profile.html', user=user)

@app.route('/edit/<username>', methods=['GET', 'POST'])
def edit_profile(username):
    """Edit profile with image upload"""
    conn = get_db()
    cursor = conn.cursor()

    # Get current user data
    cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
    user = cursor.fetchone()

    if user is None:
        conn.close()
        flash('User not found!', 'error')
        return redirect(url_for('index'))

    if request.method == 'POST':
        # Get form data
        display_name = request.form.get('display_name', '').strip()
        email = request.form.get('email', '').strip()

        # Validate inputs
        if not display_name:
            flash('Display name is required!', 'error')
            return render_template('edit.html', user=user)

        # Handle file upload
        image_filename = user['image_filename']  # Keep existing by default

        if 'profile_image' in request.files:
            file = request.files['profile_image']
            if file and file.filename != '':
                # Validate file
                if not allowed_file(file.filename):
                    flash('Invalid file type! Allowed: PNG, JPG, JPEG, GIF', 'error')
                    return render_template('edit.html', user=user)

                # Secure the filename
                original_filename = secure_filename(file.filename)
                # Add timestamp to prevent overwriting
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                image_filename = f"{username}_{timestamp}_{original_filename}"

                # Save file
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], image_filename)
                file.save(filepath)

                # Remove old image if exists
                if user['image_filename']:
                    old_path = os.path.join(app.config['UPLOAD_FOLDER'], user['image_filename'])
                    if os.path.exists(old_path):
                        os.remove(old_path)

                flash('Profile image uploaded successfully!', 'success')

        # Update database with parameterized query
        cursor.execute("""
            UPDATE users 
            SET display_name = ?, email = ?, image_filename = ?, updated_at = ?
            WHERE username = ?
        """, (display_name, email, image_filename, datetime.now(), username))

        conn.commit()
        conn.close()

        flash('Profile updated successfully!', 'success')
        return redirect(url_for('profile', username=username))

    conn.close()
    return render_template('edit.html', user=user)

@app.route('/delete_image/<username>', methods=['POST'])
def delete_image(username):
    """Remove profile image"""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT image_filename FROM users WHERE username = ?", (username,))
    user = cursor.fetchone()

    if user and user['image_filename']:
        # Remove file
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], user['image_filename'])
        if os.path.exists(filepath):
            os.remove(filepath)

        # Update database
        cursor.execute("""
            UPDATE users SET image_filename = NULL, updated_at = ?
            WHERE username = ?
        """, (datetime.now(), username))

        conn.commit()
        flash('Profile image removed!', 'success')

    conn.close()
    return redirect(url_for('edit_profile', username=username))

# HTML Templates (normally in templates/ folder, but included here for single-file setup)
INDEX_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Profile Management System</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
        h1 { color: #333; }
        .user-card { border: 1px solid #ddd; padding: 15px; margin: 10px 0; border-radius: 8px; display: flex; align-items: center; }
        .user-avatar { width: 60px; height: 60px; border-radius: 50%; margin-right: 15px; background: #f0f0f0; display: flex; align-items: center; justify-content: center; font-size: 24px; }
        .user-avatar img { width: 60px; height: 60px; border-radius: 50%; object-fit: cover; }
        .user-info { flex: 1; }
        .btn { display: inline-block; padding: 8px 16px; background: #007bff; color: white; text-decoration: none; border-radius: 4px; }
        .btn:hover { background: #0056b3; }
        .flash { padding: 10px; margin: 10px 0; border-radius: 4px; }
        .flash.success { background: #d4edda; color: #155724; }
        .flash.error { background: #f8d7da; color: #721c24; }
    </style>
</head>
<body>
    <h1> Profile Management System</h1>

    {% with messages = get_flashed_messages(with_categories=true) %}
        {% if messages %}
            {% for category, message in messages %}
                <div class="flash {{ category }}">{{ message }}</div>
            {% endfor %}
        {% endif %}
    {% endwith %}

    <h2>All Users</h2>
    {% for user in users %}
    <div class="user-card">
        <div class="user-avatar">
            {% if user.image_filename %}
                <img src="{{ url_for('static', filename='uploads/' + user.image_filename) }}" alt="Profile">
            {% else %}

            {% endif %}
        </div>
        <div class="user-info">
            <h3>{{ user.display_name or user.username }}</h3>
            <p>Username: {{ user.username }} | Email: {{ user.email or 'Not set' }}</p>
        </div>
        <a href="{{ url_for('profile', username=user.username) }}" class="btn">View Profile</a>
    </div>
    {% endfor %}
</body>
</html>
"""

PROFILE_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>{{ user.display_name or user.username }} - Profile</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; }
        .profile-card { text-align: center; padding: 30px; border: 1px solid #ddd; border-radius: 12px; }
        .profile-image { width: 150px; height: 150px; border-radius: 50%; margin: 0 auto 20px; background: #f0f0f0; display: flex; align-items: center; justify-content: center; font-size: 60px; }
        .profile-image img { width: 150px; height: 150px; border-radius: 50%; object-fit: cover; }
        h1 { color: #333; margin-bottom: 5px; }
        .username { color: #666; margin-bottom: 20px; }
        .info { text-align: left; margin: 20px 0; }
        .info-row { padding: 10px; border-bottom: 1px solid #eee; }
        .btn { display: inline-block; padding: 10px 20px; background: #007bff; color: white; text-decoration: none; border-radius: 4px; margin: 5px; }
        .btn:hover { background: #0056b3; }
        .flash { padding: 10px; margin: 10px 0; border-radius: 4px; }
        .flash.success { background: #d4edda; color: #155724; }
    </style>
</head>
<body>
    {% with messages = get_flashed_messages(with_categories=true) %}
        {% if messages %}
            {% for category, message in messages %}
                <div class="flash {{ category }}">{{ message }}</div>
            {% endfor %}
        {% endif %}
    {% endwith %}

    <div class="profile-card">
        <div class="profile-image">
            {% if user.image_filename %}
                <img src="{{ url_for('static', filename='uploads/' + user.image_filename) }}" alt="Profile Picture">
            {% else %}
                
            {% endif %}
        </div>
        <h1>{{ user.display_name or user.username }}</h1>
        <p class="username">@{{ user.username }}</p>

        <div class="info">
            <div class="info-row"><strong>Email:</strong> {{ user.email or 'Not set' }}</div>
            <div class="info-row"><strong>Member since:</strong> {{ user.created_at }}</div>
            <div class="info-row"><strong>Last updated:</strong> {{ user.updated_at }}</div>
        </div>

        <a href="{{ url_for('edit_profile', username=user.username) }}" class="btn">✏️ Edit Profile</a>
        <a href="{{ url_for('index') }}" class="btn">← Back to List</a>
    </div>
</body>
</html>
"""

EDIT_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Edit Profile - {{ user.username }}</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; }
        h1 { color: #333; }
        .form-group { margin: 15px 0; }
        label { display: block; margin-bottom: 5px; font-weight: bold; }
        input[type="text"], input[type="email"] { width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px; }
        input[type="file"] { padding: 8px; }
        .current-image { width: 100px; height: 100px; border-radius: 50%; margin: 10px 0; }
        .btn { padding: 10px 20px; background: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer; }
        .btn:hover { background: #0056b3; }
        .btn-danger { background: #dc3545; }
        .btn-danger:hover { background: #c82333; }
        .flash { padding: 10px; margin: 10px 0; border-radius: 4px; }
        .flash.success { background: #d4edda; color: #155724; }
        .flash.error { background: #f8d7da; color: #721c24; }
        .help-text { color: #666; font-size: 0.9em; margin-top: 5px; }
    </style>
</head>
<body>
    <h1>✏️ Edit Profile</h1>

    {% with messages = get_flashed_messages(with_categories=true) %}
        {% if messages %}
            {% for category, message in messages %}
                <div class="flash {{ category }}">{{ message }}</div>
            {% endfor %}
        {% endif %}
    {% endwith %}

    <form method="POST" enctype="multipart/form-data">
        <div class="form-group">
            <label>Current Profile Picture:</label>
            {% if user.image_filename %}
                <img src="{{ url_for('static', filename='uploads/' + user.image_filename) }}" class="current-image" alt="Current">
                <form action="{{ url_for('delete_image', username=user.username) }}" method="POST" style="display:inline;">
                    <button type="submit" class="btn btn-danger" onclick="return confirm('Remove image?')">🗑️ Remove Image</button>
                </form>
            {% else %}
                <p>No profile picture set.</p>
            {% endif %}
        </div>

        <div class="form-group">
            <label for="profile_image">Upload New Picture:</label>
            <input type="file" name="profile_image" id="profile_image" accept=".jpg,.jpeg,.png,.gif">
            <p class="help-text">Allowed formats: JPG, PNG, GIF (Max 16MB)</p>
        </div>

        <div class="form-group">
            <label for="display_name">Display Name:</label>
            <input type="text" name="display_name" id="display_name" value="{{ user.display_name or '' }}" required>
        </div>

        <div class="form-group">
            <label for="email">Email:</label>
            <input type="email" name="email" id="email" value="{{ user.email or '' }}">
        </div>

        <button type="submit" class="btn">💾 Save Changes</button>
        <a href="{{ url_for('profile', username=user.username) }}" class="btn">← Cancel</a>
    </form>
</body>
</html>
"""

def create_templates():
    """Create template files"""
    os.makedirs('templates', exist_ok=True)

    with open('templates/index.html', 'w') as f:
        f.write(INDEX_HTML)
    with open('templates/profile.html', 'w') as f:
        f.write(PROFILE_HTML)
    with open('templates/edit.html', 'w') as f:
        f.write(EDIT_HTML)

    print("✓ Templates created!")

if __name__ == '__main__':
    init_db()
    create_templates()
    print("\n Starting Flask server...")
    print("Open http://127.0.0.1:5000 in your browser")
    app.run(debug=True, port=5000)