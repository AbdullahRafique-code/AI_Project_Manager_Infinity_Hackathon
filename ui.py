"""Streamlit screens and workflow. Permissions and persistence stay in database.py."""

from datetime import date
import hashlib
import sqlite3
import uuid

from pydantic import ValidationError
import streamlit as st

import ai_service
import auth
import database


_ROLE_LABELS = {"ADMIN": "Administrator", "MANAGER": "Manager", "AGENT": "Developer"}


def _task_rows(tasks: list[dict], directory: list[dict], projects: dict | None = None) -> list[dict]:
    names = {person["id"]: person["name"] for person in directory}
    rows = []
    for task in tasks:
        row = {}
        if projects is not None:
            row["Project"] = projects[task["projectId"]]
        row.update({
            "Task": task["title"], "Description": task["description"],
            "Owner": names[task["assigneeId"]], "Deadline": task["deadline"],
            "Estimated hours": task["estimatedHours"],
        })
        rows.append(row)
    return rows


def render_login() -> None:
    st.title("NovaWorks Project Manager")
    st.write("Turn meeting decisions into assigned project work.")
    with st.form("login"):
        email = st.text_input("Email", placeholder="admin@novaworks.example")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Log in", type="primary")
    if submitted:
        user_id = database.authenticate(email, password)
        if user_id is None:
            st.error("Invalid email or password.")
        else:
            auth.start_session(user_id)
            st.rerun()
    st.caption("Demo: admin@novaworks.example · Password: Demo123!")
    st.caption("All ten demo accounts and role descriptions are listed in README.md.")


def render_team_directory() -> None:
    st.header("Team directory")
    st.caption("The same team directory is supplied to AI for project and task assignments.")
    rows = [{
        "Name": person["name"], "Role": _ROLE_LABELS[person["role"]],
        "Specialization": person["specialization"], "Skills": ", ".join(person["skills"]),
        "Email": person["email"],
    } for person in database.get_team_directory()]
    st.dataframe(rows, hide_index=True, width="stretch")


def render_project_detail(project_id: str) -> None:
    detail = database.get_project(project_id)
    project = detail["project"]
    directory = database.get_team_directory()
    names = {person["id"]: person["name"] for person in directory}
    st.divider()
    st.subheader(project["name"])
    st.caption(f"Client: {project['clientName']} · Manager: {names[project['managerId']]} · Deadline: {project['deadline']}")
    st.write(project["description"])
    st.write("Assigned tasks")
    if detail["tasks"]:
        st.dataframe(_task_rows(detail["tasks"], directory), hide_index=True, width="stretch")
    else:
        st.info("No tasks are visible for this account.")


def render_dashboard(user: dict) -> None:
    projects = database.list_projects()
    directory = database.get_team_directory()
    names = {person["id"]: person["name"] for person in directory}
    if user["role"] == "AGENT":
        st.header("My tasks")
        tasks = database.list_tasks()
        if tasks:
            project_names = {project["id"]: project["name"] for project in projects}
            st.dataframe(_task_rows(tasks, directory, project_names), hide_index=True, width="stretch")
        else:
            st.info("You have no assigned tasks yet.")
        st.subheader("Related projects")
    else:
        st.header("All projects" if user["role"] == "ADMIN" else "My projects")

    if not projects:
        st.info("No projects yet. An administrator can create them from a meeting transcript.")
        return
    columns = st.columns(min(3, len(projects)))
    for index, project in enumerate(projects):
        with columns[index % len(columns)], st.container(border=True):
            st.subheader(project["name"])
            st.write(project["clientName"])
            st.caption(f"Manager: {names[project['managerId']]}")
            st.caption(f"Deadline: {project['deadline']}")
            if st.button("Open project", key=f"project_{project['id']}"):
                st.session_state["selected_project"] = project["id"]
    selected = st.session_state.get("selected_project")
    if selected:
        render_project_detail(selected)


def render_transcript_form() -> None:
    auth.require_role(database.current_user(), ("ADMIN",))
    st.header("Create from transcript")
    st.caption("Paste the complete meeting. AI resolves the final decisions against the team directory.")
    if "extraction_pending" not in st.session_state:
        with st.form("transcript_form"):
            meeting_date = st.date_input("Meeting date", value=date(2026, 10, 7))
            st.caption("Dates use Asia/Karachi. The supplied meeting is 7 October 2026.")
            transcript = st.text_area("Meeting transcript", height=300, key="transcript")
            create = st.form_submit_button("Create projects", type="primary")
        if create:
            if not transcript.strip():
                st.error("Paste a meeting transcript first.")
            else:
                fingerprint = hashlib.sha256((meeting_date.isoformat() + "\n" + transcript.strip()).encode()).hexdigest()
                if fingerprint == st.session_state.get("last_saved_transcript"):
                    st.info("This transcript was already saved in this session. Change it or reset demo projects before another test.")
                else:
                    st.session_state["extraction_pending"] = {
                        "transcript": transcript, "meeting_date": meeting_date.isoformat(),
                        "fingerprint": fingerprint, "request_id": str(uuid.uuid4()),
                    }
                    st.rerun()
    else:
        st.button("Creating projects…", disabled=True)
        pending = st.session_state["extraction_pending"]
        try:
            with st.spinner("DeepSeek is extracting projects and tasks…"):
                if "raw_json" not in pending:
                    pending["raw_json"] = ai_service.extract_projects(
                        pending["transcript"], database.get_team_directory(), pending["meeting_date"]
                    )
                project_ids = database.save_extraction(pending["raw_json"], pending["request_id"])
                task_count = sum(len(database.get_project(project_id)["tasks"]) for project_id in project_ids)
            st.session_state["last_saved_transcript"] = pending["fingerprint"]
            st.session_state["creation_success"] = f"Created {len(project_ids)} projects and {task_count} tasks. Open Projects to review them."
        except ValidationError as exc:
            st.session_state["creation_error"] = "Correct these transcript fields and try again:\n" + "\n".join(
                f"{'.'.join(str(part) for part in error['loc'])}: {error['msg']}"
                for error in exc.errors(include_input=False)
            )
        except (ValueError, RuntimeError, PermissionError) as exc:
            st.session_state["creation_error"] = str(exc)
        except (sqlite3.Error, OSError):
            st.session_state["creation_error"] = "Could not save the project batch. Check the database and retry."
        finally:
            st.session_state.pop("extraction_pending", None)
        st.rerun()
    if "creation_error" in st.session_state:
        st.error(st.session_state.pop("creation_error"))


def main() -> None:
    st.set_page_config(page_title="NovaWorks Project Manager", page_icon="📋", layout="wide")
    try:
        database.init_db()
        database.seed_demo_users()
        user = database.current_user()
        if user is None:
            if auth.current_user_id() is not None:
                auth.logout()
            render_login()
            return

        st.sidebar.title("NovaWorks")
        st.sidebar.write(user["name"])
        st.sidebar.caption(_ROLE_LABELS[user["role"]])
        options = ["My tasks" if user["role"] == "AGENT" else "Projects", "Team directory"]
        if user["role"] == "ADMIN":
            options.insert(1, "Create from transcript")
        page = st.sidebar.radio("Workspace", options, key="navigation", disabled="extraction_pending" in st.session_state)
        st.sidebar.button("Log out", on_click=auth.logout)

        if user["role"] == "ADMIN":
            with st.sidebar.expander("Demo reset"):
                confirmed = st.checkbox("Delete all generated projects and tasks")
                if st.button("Reset demo projects", disabled=not confirmed or "extraction_pending" in st.session_state):
                    database.reset_projects()
                    for key in ("selected_project", "last_saved_transcript", "extraction_pending", "creation_error"):
                        st.session_state.pop(key, None)
                    st.session_state["creation_success"] = "Demo projects cleared. All ten accounts are preserved."
                    st.rerun()

        if "creation_success" in st.session_state:
            st.success(st.session_state.pop("creation_success"))
        if page == "Create from transcript":
            render_transcript_form()
        elif page == "Team directory":
            render_team_directory()
        else:
            render_dashboard(user)
    except PermissionError as exc:
        st.error(str(exc))
    except (sqlite3.Error, OSError):
        st.error("Could not access the database. Check DATABASE_PATH and retry.")
