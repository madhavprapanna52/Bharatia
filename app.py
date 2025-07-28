from flask import Flask, request, redirect, render_template_string, session, send_from_directory
import psycopg2
from PIL import Image
import os
import uuid

app = Flask(__name__)
app.secret_key = 'your-secret-key'  # Replace with a secure key in production

# ----- PostgreSQL Config -----
DB_NAME = "social_media"
DB_USER = "madhav"
DB_PASSWORD = "1234"
DB_HOST = "localhost"
DB_PORT = "5432"

# ----- Uploads Config -----
UPLOAD_FOLDER = 'uploads'
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

# ----- HTML UI -----
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Mini Social</title>
    <!-- Google Fonts -->
    <link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@400;600;800&family=Space+Grotesk:wght@300;400;500;700&display=stylesheet">
    <!-- Tailwind CSS -->
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        :root {
            --clr-primary: #00d4ff;
            --clr-secondary: #ff6b35;
            --clr-bg-dark: #0a0a0a;
            --clr-bg-light: #f5f5f7;
            --clr-surface-dark: #1a1a1a;
            --clr-surface-light: #ffffff;
            --clr-text-dark: #111;
            --clr-text-light: #fff;
            --shadow-glow: 0 0 16px rgba(0,212,255,.25);
        }

        [data-theme="dark"] {
            --bg: var(--clr-bg-dark);
            --surface: var(--clr-surface-dark);
            --text: var(--clr-text-light);
            --text-muted: #a8a8a8;
        }

        [data-theme="light"] {
            --bg: var(--clr-bg-light);
            --surface: var(--clr-surface-light);
            --text: var(--clr-text-dark);
            --text-muted: #666;
        }

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        html {
            scroll-behavior: smooth;
        }

        body {
            font-family: "Space Grotesk", sans-serif;
            background: var(--bg);
            color: var(--text);
            line-height: 1.6;
            min-height: 100vh;
        }

        nav {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            backdrop-filter: blur(10px);
            background: rgba(0,0,0,.7);
            padding: 1rem 0;
            display: flex;
            justify-content: center;
            align-items: center;
            border-bottom: 1px solid rgba(0,212,255,.2);
            z-index: 1000;
        }

        nav a {
            font-family: "Orbitron", monospace;
            font-size: 0.9rem;
            letter-spacing: 1px;
            margin: 0 1.5rem;
            transition: color 0.2s;
        }

        nav a:hover {
            color: var(--clr-primary);
        }

        .theme-toggle, .login-btn {
            margin-left: 1rem;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 0.5rem;
            font-family: "Orbitron", monospace;
            font-size: 0.8rem;
            background: var(--surface);
            border: 1px solid var(--clr-primary);
            border-radius: 20px;
            padding: 0.4rem 0.8rem;
            transition: transform 0.2s;
        }

        .theme-toggle:hover, .login-btn:hover {
            transform: scale(1.05);
        }

        .post-container, .posts-container {
            max-width: 700px;
            width: 100%;
            margin: 0 auto;
            padding: 1rem;
        }

        .post-input, .comment-input {
            width: 100%;
            padding: 0.8rem 1.2rem;
            font-size: 1rem;
            font-family: "Space Grotesk", sans-serif;
            border: 1px solid var(--clr-primary);
            border-radius: 12px;
            background: var(--surface);
            color: var(--text);
            outline: none;
            transition: border-color 0.2s, box-shadow 0.2s;
            resize: none;
        }

        .post-input:focus, .comment-input:focus {
            border-color: var(--clr-secondary);
            box-shadow: var(--shadow-glow);
        }

        .post-btn, .comment-btn, .delete-btn {
            background: linear-gradient(45deg, var(--clr-primary), var(--clr-secondary));
            color: var(--clr-text-light);
            border: none;
            padding: 0.5rem 1.2rem;
            border-radius: 20px;
            font-family: "Orbitron", monospace;
            font-size: 0.9rem;
            cursor: pointer;
            transition: transform 0.2s;
        }

        .delete-btn {
            background: linear-gradient(45deg, #ff4444, #ff6b35);
        }

        .post-btn:hover, .comment-btn:hover, .delete-btn:hover {
            transform: scale(1.05);
        }

        .post-btn:disabled, .comment-btn:disabled, .delete-btn:disabled {
            opacity: 0.6;
            cursor: not-allowed;
            transform: none;
        }

        .post {
            background: var(--surface);
            border: 1px solid rgba(0,212,255,.2);
            border-radius: 12px;
            padding: 1.5rem;
            margin-bottom: 1.5rem;
            opacity: 0;
            transition: opacity 0.3s, transform 0.2s;
        }

        .post.visible {
            opacity: 1;
        }

        .post:hover {
            transform: translateY(-4px);
            border-color: var(--clr-primary);
        }

        .post-content {
            font-size: 1rem;
            color: var(--text);
            margin-bottom: 1rem;
        }

        .post-image {
            max-width: 100%;
            height: auto;
            border-radius: 8px;
            margin-bottom: 1rem;
        }

        .post-actions {
            display: flex;
            gap: 1rem;
            font-size: 0.9rem;
            color: var(--text-muted);
        }

        .post-actions button {
            font-family: "Orbitron", monospace;
            transition: color 0.2s;
        }

        .post-actions button:hover {
            color: var(--clr-primary);
        }

        .comment {
            background: rgba(0,212,255,.05);
            border: 1px solid rgba(0,212,255,.2);
            border-radius: 8px;
            padding: 0.8rem;
            margin-top: 0.5rem;
            font-size: 0.9rem;
            color: var(--text);
            opacity: 0;
            transition: opacity 0.3s;
        }

        .comment.visible {
            opacity: 1;
        }

        .section-title {
            font-family: "Orbitron", monospace;
            font-size: 1.8rem;
            font-weight: 600;
            text-align: center;
            margin-bottom: 2rem;
            background: linear-gradient(45deg, var(--clr-primary), var(--clr-secondary));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .login-container {
            max-width: 400px;
            margin: 2rem auto;
            padding: 1rem;
        }

        .login-input {
            width: 100%;
            padding: 0.8rem 1.2rem;
            margin-bottom: 1rem;
            font-size: 1rem;
            font-family: "Space Grotesk", sans-serif;
            border: 1px solid var(--clr-primary);
            border-radius: 12px;
            background: var(--surface);
            color: var(--text);
            outline: none;
            transition: border-color 0.2s, box-shadow 0.2s;
        }

        .login-input:focus {
            border-color: var(--clr-secondary);
            box-shadow: var(--shadow-glow);
        }

        @media (max-width: 768px) {
            nav a {
                margin: 0 0.8rem;
                font-size: 0.8rem;
            }

            .post-container, .posts-container, .login-container {
                max-width: 90%;
            }
        }
    </style>
</head>
<body data-theme="dark">
    <!-- Navbar -->
    <nav id="navbar">
        <a href="#home">Home</a>
        <a href="#about">About</a>
        {% if 'username' in session %}
            <span class="login-btn">Logged in as {{ session['username'] }}</span>
            <a href="/logout" class="login-btn">Logout</a>
        {% else %}
            <a href="/login" class="login-btn">Login</a>
        {% endif %}
        <div id="themeToggle" class="theme-toggle">
            <span class="theme-icon">+</span>
            <span>DARK</span>
        </div>
    </nav>

    <!-- Login Section -->
    {% if 'username' not in session %}
    <section id="login" class="login-container pt-24">
        <h2 class="section-title">Login or Register</h2>
        <div class="bg-[var(--surface)] rounded-lg shadow-lg p-6">
            <input id="username" class="login-input" placeholder="Enter username">
            <div class="flex justify-end">
                <button id="login-button" class="post-btn">Login/Register</button>
            </div>
        </div>
    </section>
    {% else %}
    <!-- Post Creation Section -->
    <section id="home" class="post-container pt-24">
        <h2 class="section-title">Mini Social</h2>
        <div class="bg-[var(--surface)] rounded-lg shadow-lg p-6 mb-8">
            <textarea id="post-content" class="post-input" rows="4" placeholder="What's on your mind?"></textarea>
            <input id="post-image" type="file" accept="image/*" class="mt-3">
            <div class="flex justify-end mt-3">
                <button id="post-button" class="post-btn">Post</button>
            </div>
        </div>
    </section>

    <!-- Posts Section -->
    <section class="posts-container">
        <h2 class="section-title">All Posts</h2>
        {% for post in posts %}
            <div class="post">
                <p class="post-content">{{ post[1] }}</p>
                {% if post[3] %}
                    <img src="/uploads/{{ post[3] }}" class="post-image" alt="Post image">
                {% endif %}
                <div class="post-actions">
                    <button onclick="toggleLike(this)">❤️ Like</button>
                    {% if 'user_id' in session and session['user_id'] == post[2] %}
                        <button class="delete-btn" onclick="deletePost('{{ post[0] }}')">🗑️ Delete</button>
                    {% endif %}
                </div>
                <div class="comment-box mt-4">
                    <div class="flex items-center space-x-2">
                        <input id="comment-{{ post[0] }}" class="comment-input" placeholder="Write a comment...">
                        <button class="comment-btn" onclick="submitComment('{{ post[0] }}')">Comment</button>
                    </div>
                </div>
                <div class="comments mt-4">
                    {% for comment in post[4] %}
                        <div class="comment">
                            <span class="text-[var(--clr-primary)]">💬</span>
                            {{ comment }}
                        </div>
                    {% endfor %}
                </div>
            </div>
        {% endfor %}
    </section>
    {% endif %}

    <script>
        // Theme Toggle
        const themeToggle = document.getElementById('themeToggle');
        const body = document.body;
        let dark = true;
        themeToggle.onclick = () => {
            dark = !dark;
            body.setAttribute('data-theme', dark ? 'dark' : 'light');
            themeToggle.querySelector('.theme-icon').textContent = dark ? '+' : '-';
            themeToggle.querySelector('span:last-child').textContent = dark ? 'DARK' : 'LIGHT';
            document.getElementById('navbar').style.background = dark
                ? 'rgba(0,0,0,.7)'
                : 'rgba(255,255,255,.8)';
        };

        // Navbar Scroll
        const nav = document.getElementById('navbar');
        window.addEventListener('scroll', () => {
            nav.style.background = dark
                ? (window.scrollY > 40 ? 'rgba(0,0,0,.8)' : 'rgba(0,0,0,.7)')
                : (window.scrollY > 40 ? 'rgba(255,255,255,.9)' : 'rgba(255,255,255,.8)');
        });

        // Intersection Observer for animations
        const io = new IntersectionObserver(entries => {
            entries.forEach(e => e.isIntersecting && e.target.classList.add('visible'));
        }, { threshold: 0.1 });
        document.querySelectorAll('.post, .comment').forEach(el => io.observe(el));

        // Escape HTML to prevent XSS
        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text || '';
            return div.innerHTML;
        }

        // Handle login/register
        document.getElementById('login-button')?.addEventListener('click', async () => {
            const username = document.getElementById('username').value.trim();
            if (!username) return alert('Please enter a username!');
            try {
                const response = await fetch('/login', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                    body: `username=${encodeURIComponent(username)}`
                });
                if (response.ok) {
                    location.reload();
                } else {
                    alert('Failed to login/register. Please try again.');
                }
            } catch (error) {
                console.error('Error logging in:', error);
                alert('An error occurred. Please try again.');
            }
        });

        // Handle post submission
        document.getElementById('post-button')?.addEventListener('click', async () => {
            const content = document.getElementById('post-content').value.trim();
            const imageInput = document.getElementById('post-image');
            if (!content) return alert('Please enter some content!');
            const formData = new FormData();
            formData.append('content', content);
            if (imageInput.files.length > 0) {
                formData.append('image', imageInput.files[0]);
            }
            try {
                const response = await fetch('/post', {
                    method: 'POST',
                    body: formData
                });
                if (response.ok) {
                    location.reload();
                } else {
                    alert('Failed to post. Please try again.');
                }
            } catch (error) {
                console.error('Error posting:', error);
                alert('An error occurred. Please try again.');
            }
        });

        // Handle comment submission
        async function submitComment(postId) {
            const commentInput = document.getElementById(`comment-${postId}`);
            const comment = commentInput.value.trim();
            if (!comment) return alert('Please enter a comment!');
            try {
                const response = await fetch(`/comment/${postId}`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                    body: `comment=${encodeURIComponent(comment)}`
                });
                if (response.ok) {
                    location.reload();
                } else {
                    alert('Failed to comment. Please try again.');
                }
            } catch (error) {
                console.error('Error commenting:', error);
                alert('An error occurred. Please try again.');
            }
        }

        // Handle post deletion
        async function deletePost(postId) {
            if (!confirm('Are you sure you want to delete this post?')) return;
            try {
                const response = await fetch(`/delete/${postId}`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
                });
                if (response.ok) {
                    location.reload();
                } else {
                    alert('Failed to delete post. Please try again.');
                }
            } catch (error) {
                console.error('Error deleting post:', error);
                alert('An error occurred. Please try again.');
            }
        }

        // Toggle like button (client-side only for demo)
        function toggleLike(button) {
            button.classList.toggle('text-[var(--clr-secondary)]');
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
        posts_with_comments.append((post[0], post[1], post[2], post[3], comments, post[4]))
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
            os.remove(filepath)  # Remove original image
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
    if post[1]:  # Delete image file if exists
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