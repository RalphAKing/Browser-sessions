import argparse
import os
import shutil
import sqlite3
import subprocess
import json  

from flask import Flask, request, redirect, url_for, render_template_string, jsonify

DB_FILE = "sessions.db"


def init_db():
    """Initializes the SQLite database and creates tables if they do not exist."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE
        )
        """
    )
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS pinned_tabs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER,
            url TEXT,
            FOREIGN KEY(session_id) REFERENCES sessions(id)
        )
        """
    )
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS credentials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER,
            website TEXT,
            username TEXT,
            password TEXT,
            FOREIGN KEY(session_id) REFERENCES sessions(id)
        )
        """
    )
    conn.commit()
    conn.close()


def get_session_id(session_name):
    """
    Retrieve the session ID for the given name.
    If the session does not exist, create it.
    """
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id FROM sessions WHERE name=?", (session_name,))
    row = c.fetchone()
    if row is None:
        c.execute("INSERT INTO sessions (name) VALUES (?)", (session_name,))
        conn.commit()
        session_id = c.lastrowid
    else:
        session_id = row[0]
    conn.close()
    return session_id


def create_autopin_extension(pinned_urls):
    """
    Automatically creates the auto-pin extension files in a folder
    named "auto_pin_extension" in the current working directory.
    This version uses Manifest V3.
    """
    ext_dir = os.path.join(os.getcwd(), "auto_pin_extension")
    if not os.path.exists(ext_dir):
        os.makedirs(ext_dir, exist_ok=True)

    manifest_content = {
        "manifest_version": 3,
        "name": "Auto Pin Tabs",
        "version": "1.0",
        "description": "Automatically pins tabs matching specific URL substrings.",
        "background": {"service_worker": "background.js"},
        "permissions": ["tabs"],
        "host_permissions": ["<all_urls>"],
    }

    background_content = f"""
// List of URL substrings that should be auto-pinned.
const pinnedUrls = {json.dumps(pinned_urls)};
"""
    background_content += """
function checkAndPinTab(tab) {
  if (!tab.url) return;
  for (const urlSubstring of pinnedUrls) {
    if (tab.url.includes(urlSubstring)) {
      chrome.tabs.update(tab.id, { pinned: true }, () => {
        console.log("Pinned tab: " + tab.url);
      });
      break;
    }
  }
}

// When a tab is created.
chrome.tabs.onCreated.addListener((tab) => {
  if (tab.url) {
    checkAndPinTab(tab);
  }
});

// When a tab is updated (e.g., when loading completes).
chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  if (changeInfo.status === "complete" && tab.url) {
    checkAndPinTab(tab);
  }
});

// On startup, check all current tabs.
chrome.tabs.query({}, (tabs) => {
  for (const tab of tabs) {
    checkAndPinTab(tab);
  }
});
"""

    with open(os.path.join(ext_dir, "manifest.json"), "w") as mf:
        json.dump(manifest_content, mf, indent=2)
    with open(os.path.join(ext_dir, "background.js"), "w") as bf:
        bf.write(background_content)

    return ext_dir


def create_autofill_extension(credentials):
    """Creates the auto-fill extension files in a folder named 'auto_fill_extension'"""
    ext_dir = os.path.join(os.getcwd(), "auto_fill_extension")
    os.makedirs(ext_dir, exist_ok=True)

    manifest_content = {
        "manifest_version": 3,
        "name": "Auto Fill Credentials",
        "version": "1.0",
        "description": "Automatically fills credentials for specified websites",
        "permissions": ["activeTab", "scripting"],
        "host_permissions": ["<all_urls>"],
        "background": {"service_worker": "background.js"},
        "content_scripts": [{
            "matches": ["<all_urls>"],
            "js": ["content.js"]
        }]
    }

    background_content = f"""
const credentials = {json.dumps(credentials)};

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {{
    if (request.action === "getCredentials") {{
        const url = request.url;
        const matchingCred = credentials.find(cred => url.includes(cred.website));
        sendResponse(matchingCred || null);
    }}
}});
"""

    content_script = """
function fillCredentials(credentials) {
    if (!credentials) return;
    
    const usernameFields = document.querySelectorAll('input[type="text"], input[type="email"]');
    const passwordFields = document.querySelectorAll('input[type="password"]');
    
    usernameFields.forEach(field => {
        if (credentials.username) {
            field.value = credentials.username;
        }
    });
    
    passwordFields.forEach(field => {
        field.value = credentials.password;
    });
}

chrome.runtime.sendMessage({
    action: "getCredentials",
    url: window.location.href
}, fillCredentials);
"""

    with open(os.path.join(ext_dir, "manifest.json"), "w") as mf:
        json.dump(manifest_content, mf, indent=2)
    with open(os.path.join(ext_dir, "background.js"), "w") as bf:
        bf.write(background_content)
    with open(os.path.join(ext_dir, "content.js"), "w") as cf:
        cf.write(content_script)

    return ext_dir


def launch_chromium(session_name, fresh=False, use_autopin=True):
    session_id = get_session_id(session_name)
    
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # Get pinned URLs
    c.execute("SELECT url FROM pinned_tabs WHERE session_id=?", (session_id,))
    urls = [row[0] for row in c.fetchall()]
    
    # Get credentials
    c.execute("SELECT website, username, password FROM credentials WHERE session_id=?", (session_id,))
    credentials = [{"website": row[0], "username": row[1], "password": row[2]} for row in c.fetchall()]
    
    conn.close()

    profile_dir = os.path.join(os.getcwd(), "profiles", session_name)
    if fresh and os.path.exists(profile_dir):
        shutil.rmtree(profile_dir)
    os.makedirs(profile_dir, exist_ok=True)

    chromium_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    
    command = [
        chromium_path,
        f"--user-data-dir={profile_dir}",
        "--new-window",
    ]

    extensions = []
    if use_autopin:
        pin_ext_dir = create_autopin_extension(urls)
        extensions.append(pin_ext_dir)
    
    if credentials:
        fill_ext_dir = create_autofill_extension(credentials)
        extensions.append(fill_ext_dir)
    
    if extensions:
        command.append(f"--load-extension={','.join(extensions)}")

    command.extend(urls)

    try:
        subprocess.Popen(command)
        print(f"Launched Chromium session '{session_name}' with profile '{profile_dir}'")
        print(f"Loaded URLs: {urls}")
        print(f"Loaded credentials for: {[cred['website'] for cred in credentials]}")
    except Exception as e:
        print(f"Failed to launch Chromium: {e}")



# -----------------------------------------------
# Flask Web Interface for Managing Sessions.
# -----------------------------------------------
app = Flask(__name__)

index_template = """
<!doctype html>
<html>
  <head>
    <title>Browser Sessions</title>
  </head>
  <body>
    <h1>Browser Sessions</h1>
    <ul>
      {% for session in sessions %}
      <li>
        <a href="{{ url_for('session_view', session_name=session[1]) }}">
          {{ session[1] }}
        </a>
        -
        <a href="{{ url_for('run_session', session_name=session[1]) }}">
          Launch Session
        </a>
      </li>
      {% endfor %}
    </ul>
    <h2>Create a New Session</h2>
    <form action="{{ url_for('create_session') }}" method="post">
      <input type="text" name="session_name" placeholder="Session name" required>
      <input type="submit" value="Create Session">
    </form>
  </body>
</html>
"""

session_view_template = """
<!doctype html>
<html>
  <head>
    <title>Session: {{ session_name }}</title>
  </head>
  <body>
    <h1>Session: {{ session_name }}</h1>
    <h2>Pinned Tabs</h2>
    <ul>
      {% for tab in pinned_tabs %}
      <li>{{ tab[1] }}</li>
      {% endfor %}
    </ul>
    <form action="{{ url_for('add_pinned_tab', session_name=session_name) }}"
          method="post">
      <input type="url" name="url" placeholder="Enter URL to pin" required>
      <input type="submit" value="Add Pinned Tab">
    </form>

    <h2>Credentials</h2>
    <ul>
      {% for cred in credentials %}
      <li>
        {{ cred[1] }} - Username: {{ cred[2] }}, Password: {{ cred[3] }}
      </li>
      {% endfor %}
    </ul>
    <form action="{{ url_for('add_credential', session_name=session_name) }}"
          method="post">
      <input type="text" name="website" placeholder="Website" required>
      <input type="text" name="username" placeholder="Username">
      <input type="text" name="password" placeholder="Password" required>
      <input type="submit" value="Add Credential">
    </form>

    <p><a href="{{ url_for('index') }}">Back to Sessions List</a></p>
  </body>
</html>
"""


@app.route("/")
def index():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id, name FROM sessions")
    sessions = c.fetchall()
    conn.close()
    return render_template_string(index_template, sessions=sessions)


@app.route("/create_session", methods=["POST"])
def create_session():
    session_name = request.form.get("session_name")
    if session_name:
        get_session_id(session_name)
    return redirect(url_for("index"))


@app.route("/session/<session_name>")
def session_view(session_name):
    session_id = get_session_id(session_name)
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id, url FROM pinned_tabs WHERE session_id=?", (session_id,))
    pinned_tabs = c.fetchall()
    c.execute(
        "SELECT id, website, username, password FROM credentials WHERE session_id=?",
        (session_id,),
    )
    credentials = c.fetchall()
    conn.close()
    return render_template_string(
        session_view_template,
        session_name=session_name,
        pinned_tabs=pinned_tabs,
        credentials=credentials,
    )


@app.route("/session/<session_name>/add_pinned_tab", methods=["POST"])
def add_pinned_tab(session_name):
    session_id = get_session_id(session_name)
    url_value = request.form.get("url")
    if url_value:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute(
            "INSERT INTO pinned_tabs (session_id, url) VALUES (?, ?)",
            (session_id, url_value),
        )
        conn.commit()
        conn.close()
    return redirect(url_for("session_view", session_name=session_name))


@app.route("/session/<session_name>/add_credential", methods=["POST"])
def add_credential(session_name):
    session_id = get_session_id(session_name)
    website = request.form.get("website")
    username = request.form.get("username")
    password = request.form.get("password")
    if website and password:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute(
            "INSERT INTO credentials (session_id, website, username, password) "
            "VALUES (?, ?, ?, ?)",
            (session_id, website, username, password),
        )
        conn.commit()
        conn.close()
    return redirect(url_for("session_view", session_name=session_name))


@app.route("/run_session/<session_name>")
def run_session(session_name):
    launch_chromium(session_name, fresh=True)
    return redirect(url_for("session_view", session_name=session_name))





if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Manage browser sessions.")
    parser.add_argument(
        "--session",
        type=str,
        help="Name of the browser session to launch (e.g., --session home)",
    )
    parser.add_argument(
        "--fresh",
        action="store_true",
        help="Launch the session with a fresh profile (clears existing profile data)",
    )
    parser.add_argument(
        "--webui", action="store_true", help="Launch the GUI web interface"
    )
    args = parser.parse_args()

    init_db()

    if args.session:
        launch_chromium(args.session, fresh=args.fresh)
    elif args.webui:
        app.run(debug=True, host="0.0.0.0", port=5000)
    else:
        parser.print_help()
