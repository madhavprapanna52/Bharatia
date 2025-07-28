// Firebase Config - Replace with your project's config
const firebaseConfig = {
    apiKey: "YOUR_API_KEY",
    authDomain: "YOUR_PROJECT_ID.firebaseapp.com",
    projectId: "YOUR_PROJECT_ID",
    storageBucket: "YOUR_PROJECT_ID.appspot.com",
    messagingSenderId: "YOUR_SENDER_ID",
    appId: "YOUR_APP_ID"
};

const app = firebase.initializeApp(firebaseConfig);
const auth = firebase.auth();
const db = firebase.firestore();
const storage = firebase.storage();

// Theme Toggle
function toggleTheme() {
    const body = document.body;
    const isDark = body.getAttribute('data-theme') === 'dark';
    body.setAttribute('data-theme', isDark ? 'light' : 'dark');
    document.querySelector('.theme-toggle').textContent = isDark ? '☀️ Light' : '🌙 Dark';
}

// Auth State Listener
auth.onAuthStateChanged(user => {
    if (user) {
        document.getElementById('login-section').style.display = 'none';
        document.getElementById('post-section').style.display = 'block';
        document.getElementById('user-greeting').textContent = `नमस्ते, ${user.email}`;
        document.getElementById('logout-btn').style.display = 'inline';
        document.getElementById('login-btn').style.display = 'none';
        loadPosts();
    } else {
        document.getElementById('login-section').style.display = 'block';
        document.getElementById('post-section').style.display = 'none';
        document.getElementById('user-greeting').textContent = '';
        document.getElementById('logout-btn').style.display = 'none';
        document.getElementById('login-btn').style.display = 'inline';
    }
});

// Login/Register with Email
async function login() {
    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;
    try {
        await auth.signInWithEmailAndPassword(email, password);
    } catch (error) {
        // If user doesn't exist, register
        await auth.createUserWithEmailAndPassword(email, password);
    }
}

// Google Login
function googleLogin() {
    const provider = new firebase.auth.GoogleAuthProvider();
    auth.signInWithPopup(provider);
}

// Logout
document.getElementById('logout-btn').onclick = () => auth.signOut();

// Suggest Sanskrit Quote (Using Quotable API - Customize for Sanskrit if needed)
async function suggestQuote() {
    const response = await fetch('https://api.quotable.io/random?tags=inspirational');
    const data = await response.json();
    document.getElementById('post-content').value = data.content + ' - ' + data.author;  // Adapt for Sanskrit APIs
}

// Client-Side Image Pixelation
function pixelateImage(file, pixelSize = 16) {
    return new Promise((resolve, reject) => {
        const img = new Image();
        img.src = URL.createObjectURL(file);
        img.onload = () => {
            const canvas = document.createElement('canvas');
            const ctx = canvas.getContext('2d');
            const width = img.width;
            const height = img.height;
            canvas.width = width;
            canvas.height = height;

            // Downscale
            const smallCanvas = document.createElement('canvas');
            smallCanvas.width = width / pixelSize;
            smallCanvas.height = height / pixelSize;
            const smallCtx = smallCanvas.getContext('2d');
            smallCtx.drawImage(img, 0, 0, smallCanvas.width, smallCanvas.height);

            // Upscale
            ctx.imageSmoothingEnabled = false;
            ctx.drawImage(smallCanvas, 0, 0, smallCanvas.width, smallCanvas.height, 0, 0, width, height);

            canvas.toBlob(resolve, 'image/jpeg');
        };
        img.onerror = reject;
    });
}

// Post Content
async function postContent() {
    const content = document.getElementById('post-content').value;
    const file = document.getElementById('post-image').files[0];
    if (!content) return;

    let imageUrl = null;
    if (file) {
        const pixelatedBlob = await pixelateImage(file);
        const ref = storage.ref().child(`images/${Date.now()}.jpg`);
        const snapshot = await ref.put(pixelatedBlob);
        imageUrl = await snapshot.ref.getDownloadURL();
    }

    await db.collection('posts').add({
        content,
        userId: auth.currentUser.uid,
        imageUrl,
        createdAt: firebase.firestore.FieldValue.serverTimestamp()
    });
    document.getElementById('post-content').value = '';
    document.getElementById('post-image').value = '';
    loadPosts();  // Refresh
}

// Load Posts (Real-Time)
function loadPosts() {
    const container = document.getElementById('posts-container');
    container.innerHTML = '';
    db.collection('posts').orderBy('createdAt', 'desc').onSnapshot(snapshot => {
        container.innerHTML = '';
        snapshot.forEach(doc => {
            const post = doc.data();
            const postDiv = document.createElement('div');
            postDiv.className = 'post';
            postDiv.innerHTML = `
                <p>${post.content} - by ${auth.currentUser.email}</p>
                ${post.imageUrl ? `<img src="${post.imageUrl}" class="post-image">` : ''}
                <button onclick="toggleLike(this)">❤️ Like</button>
                ${post.userId === auth.currentUser.uid ? `<button class="btn delete-btn" onclick="deletePost('${doc.id}')">Delete</button>` : ''}
                <input id="comment-${doc.id}" class="comment-input" placeholder="Comment...">
                <button class="btn" onclick="submitComment('${doc.id}')">Comment</button>
                <div id="comments-${doc.id}"></div>
            `;
            container.appendChild(postDiv);
            loadComments(doc.id);
        });
    });
}

// Submit Comment
async function submitComment(postId) {
    const comment = document.getElementById(`comment-${postId}`).value;
    if (!comment) return;
    await db.collection('posts').doc(postId).collection('comments').add({
        content: comment,
        createdAt: firebase.firestore.FieldValue.serverTimestamp()
    });
    document.getElementById(`comment-${postId}`).value = '';
}

// Load Comments (Real-Time)
function loadComments(postId) {
    const container = document.getElementById(`comments-${postId}`);
    db.collection('posts').doc(postId).collection('comments').orderBy('createdAt', 'desc').onSnapshot(snapshot => {
        container.innerHTML = '';
        snapshot.forEach(doc => {
            const commentDiv = document.createElement('div');
            commentDiv.className = 'comment';
            commentDiv.textContent = doc.data().content;
            container.appendChild(commentDiv);
        });
    });
}

// Delete Post
async function deletePost(postId) {
    if (!confirm('Delete?')) return;
    await db.collection('posts').doc(postId).delete();
}

// Toggle Like (Local for now)
function toggleLike(btn) {
    btn.classList.toggle('text-red-500');
}
