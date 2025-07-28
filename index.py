from flask import Flask, request, redirect, render_template_string, session, send_from_directory
import psycopg2
from PIL import Image
import os
import uuid
import io

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key')  # Use env var for production

# ----- PostgreSQL Config (Use Environment Variables for Portability) -----
DB_NAME = os.environ.get('DB_NAME', 'social_media')
DB_USER = os.environ.get('DB_USER', 'madhav')
DB_PASSWORD = os.environ.get('DB_PASSWORD', '1234')
DB_HOST = os.environ.get('DB_HOST', 'localhost')
DB_PORT = os.environ.get('DB_PORT', '5432')

# ----- Uploads Config -----
# For Vercel, use /tmp for temporary storage (non-persistent)
UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', '/tmp/uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# ----- Database Connection -----
def get_conn():
    return psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT
    )

# ----- Create Tables -----
def init_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(50) UNIQUE NOT NULL
        );
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS posts (
            id SERIAL PRIMARY KEY,
            content TEXT NOT NULL,
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            image_path TEXT
        );
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS comments (
            id SERIAL PRIMARY KEY,
            post_id INTEGER REFERENCES posts(id) ON DELETE CASCADE,
            content TEXT NOT NULL
        );
    """)
    conn.commit()
    cur.close()
    conn.close()

init_db()

# ----- Image Processing (Minecraft-style Pixelation) -----
def pixelate_image(input_path, output_path, pixel_size=16):
    try:
        img = Image.open(input_path)
        img = img.convert('RGB')
        # Resize to low resolution for pixelated effect
        small = img.resize(
            (img.width // pixel_size, img.height // pixel_size),
            resample=Image.NEAREST
        )
        # Scale back up to original size
        pixelated = small.resize(img.size, Image.NEAREST)
        pixelated.save(output_path, quality=95)
    except Exception as e:
        print(f"Error pixelating image: {e}")

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ----- HTML UI (Minimal and Awesome: Simplified Tailwind, Indian-inspired colors, Clean Design) -----
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Bharatiya</title>
    <!-- Google Fonts -->
    <link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@400;600;800&family=Devanagari:wght@400;700&display=swap" rel="stylesheet">
    <!-- Tailwind CSS -->
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        :root {
            --clr-primary: #ff9933; /* Saffron */
            --clr-secondary: #138808; /* Green */
            --clr-bg-dark: #2c3e50;
            --clr-bg-light: #f4f4f4;
            --clr-surface-dark: #34495e;
            --clr-surface-light: #ffffff;
            --clr-text-dark: #333;
            --clr-text-light: #fff;
            --shadow-glow: 0 0 12px rgba(255,153,51,0.3);
        }

        [data-theme="dark"] {
            --bg: var(--clr-bg-dark);
            --surface: var(--clr-surface-dark);
            --text: var(--clr-text-light);
            --text-muted: #bdc3c7;
        }

        [data-theme="light"] {
            --bg: var(--clr-bg-light);
            --surface: var(--clr-surface-light);
            --text: var(--clr-text-dark);
            --text-muted: #7f8c8d;
        }

        body {
            font-family: "Devanagari", serif;
            background: var(--bg);
            color: var(--text);
            line-height: 1.5;
            min-height: 100vh;
        }

        nav {
            background: rgba(44,62,80,0.8);
            padding: 1rem;
            display: flex;
            justify-content: center;
            align-items: center;
            position: fixed;
            width: 100%;
            top: 0;
            z-index: 10;
        }

        nav a, nav span {
            margin: 0 1rem;
            color: var(--clr-primary);
            font-family: "Orbitron", sans-serif;
        }

        .theme-toggle {
            cursor: pointer;
            background: var(--surface);
            padding: 0.5rem 1rem;
            border-radius: 9999px;
            border: 1px solid var(--clr-primary);
        }

        .container {
            max-width: 800px;
            margin: 5rem auto 2rem;
            padding: 1rem;
        }

        .post-input, .comment-input, .login-input {
            width: 100%;
            padding: 0.75rem;
            border: 1px solid var(--clr-primary);
            border-radius: 0.5rem;
            background: var(--surface);
            color: var(--text);
            margin-bottom: 1rem;
        }

        .btn {
            background: linear-gradient(to right, var(--clr-primary), var(--clr-secondary));
            color: white;
            padding: 0.5rem 1rem;
            border-radius: 0.5rem;
            cursor: pointer;
        }

        .delete-btn {
            background: linear-gradient(to right, #e74c3c, #c0392b);
        }

        .post {
            background: var(--surface);
            border: 1px solid var(--clr-primary);
            border-radius: 0.5rem;
            padding: 1rem;
            margin-bottom: 1.5rem;
            transition: transform 0.2s;
        }

        .post:hover {
            transform: translateY(-5px);
        }

        .post-image {
            max-width: 100%;
            border-radius: 0.5rem;
            margin: 1rem 0;
        }

        .comment {
            background: rgba(255,153,51,0.1);
            padding: 0.5rem;
            border-radius: 0.25rem;
            margin-top: 0.5rem;
        }

        .section-title {
            font-family: "Orbitron", sans-serif;
            font-size: 2rem;
            text-align: center;
            margin-bottom: 1.5rem;
            color: var(--clr-primary);
        }
    </style>
</head>
<body data-theme="dark">
    <nav>
        <a href="/">Home</a>
        {% if 'username' in session %}
            <span>नमस्ते, {{ session['username'] }}</span>
            <a href="/logout">Logout</a>
        {% else %}
            <a href="/login">Login</a>
        {% endif %}
        <div class="theme-toggle" onclick="toggleTheme()">🌙 Dark</div>
    </nav>

    <div class="container">
        {% if 'username' not in session %}
            <h2 class="section-title">Bharatiya Login</h2>
            <input id="username" class="login-input" placeholder="Username">
            <button class="btn" onclick="login()">Login/Register</button>
        {% else %}
            <h2 class="section-title">Bharatiya</h2>
            <textarea id="post-content" class="post-input" rows="3" placeholder="Share your thoughts..."></textarea>
            <input id="post-image" type="file" accept="image/*">
            <button class="btn" onclick="postContent()">Post</button>

            <h2 class="section-title mt-8">Posts</h2>
            {% for post in posts %}
                <div class="post">
                    <p>{{ post[1] }} - by {{ post[5] }}</p>
                    {% if post[3] %}
                        <img src="/uploads/{{ post[3] }}" class="post-image">
                    {% endif %}
                    <div>
                        <button onclick="toggleLike(this)">❤️ Like</button>
                        {% if 'user_id' in session and session['user_id'] == post[2] %}
                            <button class="btn delete-btn" onclick="deletePost('{{ post[0] }}')">Delete</button>
                        {% endif %}
                    </div>
                    <input id="comment-{{ post[0] }}" class="comment-input" placeholder="Comment...">
                    <button class="btn" onclick="submitComment('{{ post[0] }}')">Comment</button>
                    {% for comment in post[4] %}
                        <div class="comment">{{ comment }}</div>
                    {% endfor %}
                </div>
            {% endfor %}
        {% endif %}
    </div>

    <script>
        function toggleTheme() {
            const body = document.body;
            const isDark = body.getAttribute('data-theme') === 'dark';
            body.setAttribute('data-theme', isDark ? 'light' : 'dark');
            document.querySelector('.theme-toggle').textContent = isDark ? '☀️ Light' : '🌙 Dark';
        }

        async function login() {
            const username = document.getElementById('username').value;
            if (!username) return;
            await fetch('/login', { method: 'POST', body: `username=${username}`, headers: { 'Content-Type': 'application/x-www-form-urlencoded' } });
            location.reload();
        }

        async function postContent() {
            const content = document.getElementById('post-content').value;
            const image = document.getElementById('post-image').files[0];
            if (!content) return;
            const formData = new FormData();
            formData.append('content', content);
            if (image) formData.append('image', image);
            await fetch('/post', { method: 'POST', body: formData });
            location.reload();
        }

        async function submitComment(postId) {
            const comment = document.getElementById(`comment-${postId}`).value;
            if (!comment) return;
            await fetch(`/comment/${postId}`, { method: 'POST', body: `comment=${comment}`, headers: { 'Content-Type': 'application/x-www-form-urlencoded' } });
            location.reload();
        }

        async function deletePost(postId) {
            if (!confirm('Delete?')) return;
            await fetch(`/delete/${postId}`, { method: 'POST' });
            location.reload();
        }

        function toggleLike(btn) {
            btn.classList.toggle('text-red-500');
        }
    </script>
</body>
</html>
"""

# ----- Routes -----
@app.route("/", methods=["GET"])
def index():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT p.id, p.content, p.user_id, p.image_path, u.username FROM posts p JOIN users u ON p.user_id = u.id ORDER BY p.id DESC")
    posts = cur.fetchall()
    posts_with_comments = []
    for post in posts:
        cur.execute("SELECT content FROM comments WHERE post_id = %s", (post[0],))
        comments = [row[0] for row in cur.fetchall()]
        posts_with_comments.append((post[0], post[1], post[2], post[3], comments, post[4]))  # Added username as post[5] but index is 4
    cur.close()
    conn.close()
    return render_template_string(HTML_TEMPLATE, posts=posts_with_comments)

@app.route("/login", methods=["POST"])
def login():
    username = request.form.get("username")
    if not username:
        return "Username required", 400
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id FROM users WHERE username = %s", (username,))
    user = cur.fetchone()
    if not user:
        cur.execute("INSERT INTO users (username) VALUES (%s) RETURNING id", (username,))
        user_id = cur.fetchone()[0]
    else:
        user_id = user[0]
    conn.commit()
    cur.close()
    conn.close()
    session['user_id'] = user_id
    session['username'] = username
    return redirect("/")

@app.route("/logout")
def logout():
    session.pop('user_id', None)
    session.pop('username', None)
    return redirect("/")

@app.route("/post", methods=["POST"])
def post():
    if 'user_id' not in session:
        return redirect("/login")
    content = request.form.get("content")
    image_path = None
    if 'image' in request.files:
        file = request.files['image']
        if file and allowed_file(file.filename):
            filename = str(uuid.uuid4()) + '.jpg'
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            pixelated_filepath = os.path.join(app.config['UPLOAD_FOLDER'], 'pixelated_' + filename)
            file.save(filepath)
            pixelate_image(filepath, pixelated_filepath)
            image_path = 'pixelated_' + filename
            os.remove(filepath)  # Remove original
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("INSERT INTO posts (content, user_id, image_path) VALUES (%s, %s, %s)", (content, session['user_id'], image_path))
    conn.commit()
    cur.close()
    conn.close()
    return redirect("/")

@app.route("/comment/<int:post_id>", methods=["POST"])
def comment(post_id):
    comment_text = request.form.get("comment")
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("INSERT INTO comments (post_id, content) VALUES (%s, %s)", (post_id, comment_text))
    conn.commit()
    cur.close()
    conn.close()
    return redirect("/")

@app.route("/delete/<int:post_id>", methods=["POST"])
def delete_post(post_id):
    if 'user_id' not in session:
        return redirect("/login")
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT user_id, image_path FROM posts WHERE id = %s", (post_id,))
    post = cur.fetchone()
    if not post or post[0] != session['user_id']:
        cur.close()
        conn.close()
        return "Unauthorized", 403
    if post[1]:
        try:
            os.remove(os.path.join(app.config['UPLOAD_FOLDER'], post[1]))
        except:
            pass
    cur.execute("DELETE FROM posts WHERE id = %s", (post_id,))
    conn.commit()
    cur.close()
    conn.close()
    return redirect("/")

@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == "__main__":
    app.run(debug=True)
