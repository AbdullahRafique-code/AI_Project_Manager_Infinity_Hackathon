"""SQLite storage. Public data requests resolve their user from the session."""

from contextlib import closing
import json
import os
from pathlib import Path
import sqlite3
import uuid

import auth
from validation import validate_extraction


# Only the supplied fictional accounts are seeded; never projects or tasks.
_DEMO_USERS = (
    ("ADMIN", "Admin", "admin", "ADMIN", "Administrator", ["Company overview", "Transcript creation"]),
    ("PM01", "Ayesha Khan", "ayesha", "MANAGER", "Web PM", ["Web projects", "Client coordination"]),
    ("PM02", "Bilal Ahmed", "bilal", "MANAGER", "Mobile PM", ["Mobile projects", "Delivery planning"]),
    ("PM03", "Hina Malik", "hina", "MANAGER", "AI PM", ["AI projects", "Requirement review"]),
    ("DEV01", "Ali Raza", "ali", "AGENT", "Full-Stack", ["React", "Frontend integration"]),
    ("DEV02", "Hamza Shah", "hamza", "AGENT", "Full-Stack", ["Node.js", "Databases", "APIs"]),
    ("DEV03", "Sara Noor", "sara", "AGENT", "App Developer", ["Flutter", "Mobile UI"]),
    ("DEV04", "Usman Tariq", "usman", "AGENT", "App Developer", ["Flutter", "Integration", "Testing"]),
    ("DEV05", "Zain Abbas", "zain", "AGENT", "AI Developer", ["LLMs", "Extraction", "Prompts"]),
    ("DEV06", "Maryam Asif", "maryam", "AGENT", "AI Developer", ["Retrieval", "Document processing"]),
)
_USER_COLUMNS = "id, name, email, role, specialization, skills"
_PROJECT_COLUMNS = "p.id, p.name, p.clientName, p.description, p.managerId, p.deadline"
_TASK_COLUMNS = "t.id, t.projectId, t.title, t.description, t.assigneeId, t.deadline, t.estimatedHours"
_DENIED = "Project not found or access denied."


def _connect() -> sqlite3.Connection:
    path = Path(os.getenv("DATABASE_PATH", "data/app.db"))
    if not path.is_absolute():
        path = Path(__file__).resolve().parent / path
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=5)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def init_db() -> None:
    """Create the schema without changing existing records."""
    with closing(_connect()) as connection:
        connection.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY, name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE COLLATE NOCASE,
                passwordHash TEXT NOT NULL,
                role TEXT NOT NULL CHECK (role IN ('ADMIN', 'MANAGER', 'AGENT')),
                specialization TEXT NOT NULL, skills TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS projects (
                id TEXT PRIMARY KEY, name TEXT NOT NULL, clientName TEXT NOT NULL,
                description TEXT NOT NULL,
                managerId TEXT NOT NULL REFERENCES users(id),
                deadline TEXT NOT NULL, requestId TEXT NOT NULL,
                batchIndex INTEGER NOT NULL, UNIQUE (requestId, batchIndex)
            );
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                projectId TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                title TEXT NOT NULL, description TEXT NOT NULL,
                assigneeId TEXT NOT NULL REFERENCES users(id),
                deadline TEXT NOT NULL,
                estimatedHours REAL NOT NULL CHECK (estimatedHours > 0)
            );
            CREATE INDEX IF NOT EXISTS projects_manager ON projects(managerId);
            CREATE INDEX IF NOT EXISTS tasks_project ON tasks(projectId);
            CREATE INDEX IF NOT EXISTS tasks_assignee ON tasks(assigneeId);
        """)


def seed_demo_users() -> None:
    """Insert supplied accounts once, preserving existing users and passwords."""
    with closing(_connect()) as connection, connection:
        connection.execute("BEGIN IMMEDIATE")
        existing = {row[0].lower() for row in connection.execute("SELECT email FROM users")}
        for user_id, name, email_name, role, specialization, skills in _DEMO_USERS:
            email = f"{email_name}@novaworks.example"
            if email in existing:
                continue
            connection.execute(
                "INSERT INTO users (id, name, email, passwordHash, role, specialization, skills) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (user_id, name, email, auth.hash_password("Demo123!"), role, specialization, json.dumps(skills)),
            )


def authenticate(email: str, password: str) -> str | None:
    """Verify credentials without exposing their stored hashes to the UI."""
    if not isinstance(email, str):
        return None
    with closing(_connect()) as connection:
        row = connection.execute(
            "SELECT id, passwordHash FROM users WHERE email = ?", (email.strip(),)
        ).fetchone()
    if row is not None and auth.verify_password(password, row["passwordHash"]):
        return row["id"]
    return None


def _user_dict(row: sqlite3.Row) -> dict:
    user = dict(row)
    user["skills"] = json.loads(user["skills"])
    return user


def _session_user(connection: sqlite3.Connection) -> dict | None:
    user_id = auth.current_user_id()
    if user_id is None:
        return None
    row = connection.execute(f"SELECT {_USER_COLUMNS} FROM users WHERE id = ?", (user_id,)).fetchone()
    return _user_dict(row) if row else None


def _require_user(connection: sqlite3.Connection) -> dict:
    user = _session_user(connection)
    auth.require_role(user, ("ADMIN", "MANAGER", "AGENT"))
    return user


def current_user() -> dict | None:
    with closing(_connect()) as connection:
        return _session_user(connection)


def _directory(connection: sqlite3.Connection) -> list[dict]:
    return [_user_dict(row) for row in connection.execute(f"SELECT {_USER_COLUMNS} FROM users ORDER BY id")]


def get_team_directory() -> list[dict]:
    with closing(_connect()) as connection:
        _require_user(connection)
        return _directory(connection)


def _project_scope(user: dict) -> tuple[str, tuple]:
    """Fixed SQL predicates and bound values; never caller-provided SQL."""
    if user["role"] == "ADMIN":
        return "1 = 1", ()
    if user["role"] == "MANAGER":
        return "p.managerId = ?", (user["id"],)
    return (
        "EXISTS (SELECT 1 FROM tasks own WHERE own.projectId = p.id AND own.assigneeId = ?)",
        (user["id"],),
    )


def list_projects() -> list[dict]:
    with closing(_connect()) as connection:
        user = _require_user(connection)
        scope, params = _project_scope(user)
        rows = connection.execute(f"SELECT {_PROJECT_COLUMNS} FROM projects p WHERE {scope} ORDER BY p.name", params)
        return [dict(row) for row in rows]


def _project(connection: sqlite3.Connection, user: dict, project_id: str) -> dict:
    scope, params = _project_scope(user)
    row = connection.execute(
        f"SELECT {_PROJECT_COLUMNS} FROM projects p WHERE ({scope}) AND p.id = ?",
        (*params, project_id),
    ).fetchone()
    if row is None:
        raise PermissionError(_DENIED)
    return dict(row)


def _tasks(connection: sqlite3.Connection, user: dict, project_id: str | None) -> list[dict]:
    scope, params = _project_scope(user)
    if project_id is not None:
        scope += " AND p.id = ?"
        params += (project_id,)
    if user["role"] == "AGENT":
        scope += " AND t.assigneeId = ?"
        params += (user["id"],)
    rows = connection.execute(
        f"SELECT {_TASK_COLUMNS} FROM tasks t JOIN projects p ON p.id = t.projectId "
        f"WHERE {scope} ORDER BY t.deadline, t.title", params,
    )
    return [dict(row) for row in rows]


def get_project(project_id: str) -> dict:
    with closing(_connect()) as connection:
        user = _require_user(connection)
        project = _project(connection, user, project_id)
        return {"project": project, "tasks": _tasks(connection, user, project_id)}


def list_tasks(project_id: str | None = None) -> list[dict]:
    with closing(_connect()) as connection:
        user = _require_user(connection)
        if project_id is not None:
            _project(connection, user, project_id)
        return _tasks(connection, user, project_id)


def save_extraction(raw_json: str, request_id: str) -> list[str]:
    """Validate everything, then atomically save the complete batch as admin.

    Repeated delivery of a request ID returns its previously saved project IDs.
    New or corrected transcript submissions must receive a new request ID.
    """
    with closing(_connect()) as connection, connection:
        connection.execute("BEGIN IMMEDIATE")
        auth.require_role(_require_user(connection), ("ADMIN",))
        if not isinstance(request_id, str) or not request_id.strip():
            raise ValueError("A submission request ID is required.")
        existing = connection.execute(
            "SELECT id FROM projects WHERE requestId = ? ORDER BY batchIndex", (request_id,)
        ).fetchall()
        if existing:
            return [row["id"] for row in existing]
        draft = validate_extraction(raw_json, _directory(connection))
        project_ids = []
        for index, project in enumerate(draft.projects):
            project_id = str(uuid.uuid4())
            connection.execute(
                "INSERT INTO projects (id, name, clientName, description, managerId, deadline, requestId, batchIndex) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (project_id, project.name, project.clientName, project.description, project.managerId,
                 project.deadline.isoformat(), request_id, index),
            )
            for task in project.tasks:
                connection.execute(
                    "INSERT INTO tasks (id, projectId, title, description, assigneeId, deadline, estimatedHours) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (str(uuid.uuid4()), project_id, task.title, task.description, task.assigneeId,
                     task.deadline.isoformat(), task.estimatedHours),
                )
            project_ids.append(project_id)
        return project_ids


def reset_projects() -> None:
    """Admin-only demo reset. Preserve all ten accounts."""
    with closing(_connect()) as connection, connection:
        connection.execute("BEGIN IMMEDIATE")
        auth.require_role(_require_user(connection), ("ADMIN",))
        connection.execute("DELETE FROM projects")
