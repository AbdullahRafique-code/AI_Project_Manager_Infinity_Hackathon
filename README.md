# Infinity PM — AI Meeting to Project CRM

A local Streamlit application for NovaWorks Technologies. An administrator pastes a meeting transcript; DeepSeek extracts the agreed projects and tasks, Pydantic validates the complete result, and SQLite saves the batch atomically.

## Team

Team leader: Abdullah Rafique

- M Jawad
- Huma Nisar
- Kaneez Fatima
- Amina
- Rana Mehran

Repository: https://github.com/AbdullahRafique-code/AI_Project_Manager_Infinity_Hackathon

## What Works

- Ten seeded demo accounts with salted password hashes, login, and logout.
- Read-only team directory with names, roles, specializations, and skills.
- Admin project cards, project details, and Create from Transcript.
- Managers see only their projects and their projects' tasks.
- Developers see only their own tasks and related projects. Related project details never expose coworkers' tasks.
- Real DeepSeek extraction using the supplied directory, meeting date, final decisions, and agreed scope.
- Full JSON/schema/ownership/deadline validation before insertion.
- Atomic saving of the entire project/task batch; failed inserts roll back.
- Persistent SQLite records, duplicate-click protection, clear errors, and admin-only demo reset.

There is no signup, user management, cost calculation, progress monitoring, or editing of created records.

## Technology Stack

- Python 3.14.4 tested; use Python 3.10 or newer with compatible installed dependencies.
- Frontend and application process: Streamlit 1.67.0.
- Persistence: Python's built-in SQLite driver (SQLite 3.50.4 tested), local `data/app.db`.
- AI: DeepSeek API, `deepseek-flash`, JSON output, thinking disabled.
- Validation: Pydantic 2.14.3.
- HTTP: requests 2.34.2. Environment loading: python-dotenv 1.2.4.
- Authentication: PBKDF2-HMAC-SHA256 password hashes with unique random salts and server-side Streamlit session state.

## Links

- Hosted application: not deployed.
- Local application: http://localhost:8501
- Demo recording: [demo.mp4](demo.mp4). This is a local browser recording, not a hosted application.
- Source repository: https://github.com/AbdullahRafique-code/AI_Project_Manager_Infinity_Hackathon

The source and video must be pushed to the repository or provided through the organizer's submission channel before judges can access them remotely.

## Requirements

- Python and pip.
- Internet access and a funded DeepSeek API key for transcript extraction.
- A writable local directory for SQLite.
- One terminal/process. No separate frontend or backend server.

## Run Locally — Windows PowerShell

If using the submission ZIP, extract it and open PowerShell in that folder; skip the first two clone/change-directory commands below.

```powershell
git clone https://github.com/AbdullahRafique-code/AI_Project_Manager_Infinity_Hackathon.git
cd AI_Project_Manager_Infinity_Hackathon
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
notepad .env
```

Set your private `DEEPSEEK_API_KEY` in `.env`. Keep `DEEPSEEK_MODEL=deepseek-flash` unless using another model available to your account. Do not overwrite an already configured `.env` when updating an existing checkout.

Initialize the schema and seed all ten accounts:

```powershell
.\.venv\Scripts\python.exe -c "from dotenv import load_dotenv; load_dotenv('.env'); import database; database.init_db(); database.seed_demo_users()"
```

Start the app:

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py --server.address 127.0.0.1 --server.port 8501 --browser.gatherUsageStats false
```

Open http://localhost:8501 and keep this terminal running. Press Ctrl+C to stop it. Schema initialization and seeding also run automatically at startup; rerunning them preserves existing accounts and projects. No separate migration command is needed for this initial MVP.

For macOS/Linux, use `.venv/bin/python` instead of `.\.venv\Scripts\python.exe` and `cp .env.example .env` instead of `Copy-Item`.

## Environment Variables

| Variable | Purpose | Where configured |
| --- | --- | --- |
| `DEEPSEEK_API_KEY` | Your private DeepSeek API key | Local `.env`, server only |
| `DEEPSEEK_MODEL` | Model ID; tested with `deepseek-flash` | Local `.env`, server only |
| `DATABASE_PATH` | SQLite file; defaults to `data/app.db` relative to the application directory | Local `.env`, server only |

`.env`, the local database, and `.venv` are ignored by Git. `.env.example` contains placeholders only. Passwords and password hashes are never included in AI requests. The model receives only directory IDs, names, roles, specializations, and skills.

## Demo Login Accounts

These emails are fictional login identifiers. All accounts are seeded automatically. Every demo password is `Demo123!`.

| Role | Name | Email | Password |
| --- | --- | --- | --- |
| Admin | Admin | admin@novaworks.example | Demo123! |
| Manager | Ayesha Khan | ayesha@novaworks.example | Demo123! |
| Manager | Bilal Ahmed | bilal@novaworks.example | Demo123! |
| Manager | Hina Malik | hina@novaworks.example | Demo123! |
| Developer / Agent | Ali Raza | ali@novaworks.example | Demo123! |
| Developer / Agent | Hamza Shah | hamza@novaworks.example | Demo123! |
| Developer / Agent | Sara Noor | sara@novaworks.example | Demo123! |
| Developer / Agent | Usman Tariq | usman@novaworks.example | Demo123! |
| Developer / Agent | Zain Abbas | zain@novaworks.example | Demo123! |
| Developer / Agent | Maryam Asif | maryam@novaworks.example | Demo123! |

Internal role `AGENT` is displayed as Developer. Seeded users keep the organizer IDs `ADMIN`, `PM01`–`PM03`, and `DEV01`–`DEV06`.

## Architecture

Exactly five modules plus the entry point:

| File | Responsibility |
| --- | --- |
| `app.py` | Load `.env`, call `ui.main()` |
| `ui.py` | Login screen, dashboards, directory, project details, transcript workflow, and readable errors |
| `auth.py` | Password hashing/checking, session identity, logout, and role checks |
| `database.py` | SQLite schema, seeded accounts, session-authorized queries, transactions, reset |
| `ai_service.py` | Official DeepSeek API request; returns raw JSON, writes nothing |
| `validation.py` | Three Pydantic schemas and deterministic ownership/date validation |

Dependency direction: `app → ui → database → auth/validation`; `ui → ai_service → validation`. There are no circular imports.

Public database queries take no caller-supplied identity or role. They resolve the session ID against the users table and apply ownership restrictions in SQL. Project-detail queries apply the same restrictions as lists. Only the admin may save an extraction or reset demo projects.

The AI returns nested project/task data referencing existing user IDs. The database validates every project and task before inserting anything, creates UUIDs, and saves all records inside one transaction. A request ID makes repeated delivery of the same submission idempotent. Valid extracted project/task counts are not hardcoded.

## How Judges Can Test

1. Start with an empty demo database; if needed use the admin reset described below.
2. Log in as `admin@novaworks.example` with `Demo123!`.
3. Open **Team directory** and verify all ten seeded accounts.
4. Open **Create from transcript**. Use meeting date **7 October 2026**; timezone is Asia/Karachi.
5. Copy the complete transcript from the final section of this README into the text area and click **Create projects**.
6. Expect a success message: **3 projects and 12 tasks**. Open **Projects** and review the three cards and details.
7. Open UrbanCart: client UrbanCart Clothing, manager Ayesha Khan, deadline **20 October 2026**, four tasks.
8. Log out and log in as Ayesha: only UrbanCart is visible.
9. Log out and log in as Ali: only his three UrbanCart tasks and the related project are visible. Its details must not show Hamza's task.
10. Log in as Hamza: exactly two API tasks spanning UrbanCart and QuickServe.
11. Refresh the browser. A full refresh may require login again; saved projects/tasks remain in SQLite. Restarting the app also preserves records.
12. Run the changed-input test below.

### Expected Project Results

| Project | Manager | Deadline | Tasks | Hours |
| --- | --- | --- | --- | --- |
| UrbanCart Website | Ayesha Khan | 2026-10-20 | 4 | 40 |
| QuickServe Mobile App | Bilal Ahmed | 2026-10-24 | 4 | 46 |
| HelpDeskPro AI Assistant | Hina Malik | 2026-10-22 | 4 | 38 |

### Expected Task Results

| Project | Task | Owner | Deadline | Hours |
| --- | --- | --- | --- | --- |
| UrbanCart | Product catalog UI | Ali | 2026-10-12 | 12 |
| UrbanCart | Demo cart UI | Ali | 2026-10-15 | 8 |
| UrbanCart | Product and cart APIs | Hamza | 2026-10-14 | 14 |
| UrbanCart | Website integration and testing | Ali | 2026-10-19 | 6 |
| QuickServe | Login and profile screens | Sara | 2026-10-12 | 8 |
| QuickServe | Service booking screens | Sara | 2026-10-17 | 12 |
| QuickServe | Booking and account APIs | Hamza | 2026-10-16 | 16 |
| QuickServe | Mobile integration and testing | Usman | 2026-10-22 | 10 |
| HelpDeskPro | FAQ document processing | Maryam | 2026-10-13 | 10 |
| HelpDeskPro | Assistant answer generation | Zain | 2026-10-17 | 14 |
| HelpDeskPro | Human escalation flow | Zain | 2026-10-18 | 6 |
| HelpDeskPro | Assistant evaluation and testing | Maryam | 2026-10-21 | 8 |

These tables are verification references only. Application code never reads them or uses them to generate results.

### Changed-Input Test

Reset generated projects first. In the supplied transcript, change all three final-agreement mentions of **Mobile integration and testing** to **12 hours, due 23 October**:

- Usman's accepted correction: make the final estimate 12 hours and deadline 23 October.
- Bilal's final agreement: Usman, 12 hours, 23 October.
- Bilal's final recap: Mobile integration and testing, 12 hours, 23 October.

Leave the earlier eight-hour proposal as historical discussion. Run creation again. Expect the same three projects and twelve tasks, with QuickServe integration at **12 hours / 2026-10-23** and QuickServe's total at **48 hours**. Other task owners, dates, and hours remain unchanged.

### Error and Authorization Checks

- Incorrect credentials show a generic error.
- An empty transcript is rejected without an API call.
- A missing/invalid API key, insufficient balance, network failure, rate limit, or incomplete response produces an understandable error.
- Missing/unknown owners, invalid dates, nonpositive hours, and task deadlines after the project deadline prevent all insertion. Correct the transcript and retry.
- API/validation failure preserves the pasted transcript.
- Repeated submit is disabled while processing. A repeated successful transcript is blocked within the same session.
- Backend tests confirmed direct project-ID access rejection, developers never receiving coworkers' tasks, and forged session role values having no effect.
- An injected database failure after earlier inserts verified rollback of the entire batch.

### Reset Demo Projects

Log in as admin. Expand **Demo reset** in the sidebar, check **Delete all generated projects and tasks**, and click **Reset demo projects**. This removes generated projects/tasks and preserves all ten accounts. Managers and developers cannot access or invoke reset.

## Verification Performed

- 30 validation/schema checks.
- 44 password, session, role, and Streamlit authentication checks.
- 173 database, ownership, transaction-rollback, and intermediate UI checks.
- Two real DeepSeek extraction runs: original and modified organizer transcripts, compared field by field and saved to a temporary SQLite database.
- 41 AI transport/privacy/integration checks, including transcript preservation on failure.
- 38 final UI checks, including role-specific project cards, task privacy, a fresh browser session, and confirmed demo reset.

Temporary verification scripts and test databases are development artifacts, not additional application modules. The README's test procedure is the reproducible judging path.

## Deployment Details

- Status: local only; no hosted deployment claimed.
- Frontend and backend: one Streamlit process on the laptop.
- Database: local SQLite. No external database provider.
- Build command: none; install `requirements.txt`.
- Start command: the Streamlit command above.
- Schema and seeding: the initialization command above, also automatic at startup.
- No CORS configuration, frontend API URL, Docker, Redis, or secondary server.
- The GitHub repository stores source; it is not a running deployment.
- Submission revision: use `git rev-parse HEAD` after committing the final files.

## Known Limitations

- Requires internet access and available DeepSeek API credits for each new extraction.
- AI output may be semantically wrong even when structurally valid. Review the saved result; deterministic validation checks required fields, identities, roles, dates, and hours, not all meeting semantics.
- No persistent browser-login cookies. Refresh may require logging in again, but records persist.
- Local SQLite is suitable for this single-laptop demo. No production authentication framework or account management is included.
- Transcript input is limited to 60,000 characters; API connect/read timeouts are 10/60 seconds.
- Duplicate-transcript detection is session-local; signing out or using another browser can create another batch. Use reset between judging tests. Database request-ID protection still prevents repeat delivery of the same submission.
- There is no editor for saved projects/tasks. Correct the source transcript, reset demo data if appropriate, and run extraction again.

## Submission Summary and Demo Checklist

- Source: this repository, with `.env.example`, requirements, and the five modules.
- Recording: `demo.mp4`; provide it or an accessible video link with the local-database submission.
- Credentials: all ten listed above, password `Demo123!`.
- Before judging: keep the app terminal open, confirm internet/API access, and reset demo projects if starting from an empty state.
- Show: admin login → directory → complete transcript → real AI creation → project details → Ayesha → Ali → Hamza → refresh.
- Explain: AI extraction, deterministic validation, session-derived SQL permissions, and all-or-nothing transaction saving.
- Provide the final repository/video through the organizer's announced submission channel before the deadline.

## Complete Organizer Transcript

Copy only the contents of this block into **Meeting transcript**. The transcript is source input; the verification tables above are not part of the AI prompt.

```text
Meeting: NovaWorks Client Delivery Planning
Date: 7 October 2026 | Scheduled duration: 60 minutes
Participants: Ayesha, Bilal, Hina, Ali, Hamza, Sara, Usman, Zain, Maryam
This is a simulated, condensed transcript of a 60-minute meeting. Timestamps represent discussion
segments; pauses, repeated explanations, and screen-sharing time are omitted. It is not an hour of
continuous verbatim speech. Use the entire transcript as the AI input.
09:00-09:04 | Opening and company workflow
Ayesha: Good morning. We have three client engagements to plan today: UrbanCart Clothing's website,
QuickServe's customer mobile app, and HelpDeskPro's AI support assistant. Please keep these as three
separate projects. A combined project would make client reporting confusing.
Bilal: We should finish with a project manager, deadline, task owner, and estimated hours for every piece
of work. The estimate is effort, not the number of days between today and the delivery date.
Hina: Agreed. Please use our supplied team directory. Accounts can already be created with a setup script.
We are not hiring anyone for this delivery cycle. Record developer work only in the estimated hours. We do
not need management-hour estimates.
Ayesha: Keep this version simple. We need project details, assigned people, deadlines, and estimated
hours. Cost calculation and progress monitoring are outside this challenge.
09:04-09:08 | UrbanCart project scope
Ayesha: First project is UrbanCart Website, for client UrbanCart Clothing. I'll manage it. They need a
responsive website where customers can browse products, view product details, and add items to a demo
cart. We initially discussed 18 October as the delivery date.
Ali: Do they need a real checkout, payment gateway, and stock integration?
Ayesha: No. For this phase the cart is a demo. Real payments and inventory integration are not included.
The client wants to review the buying experience before funding those integrations.
Hamza: So the API scope is product data and a basic cart endpoint, without payment processing?
Ayesha: Correct. Don't add a payment task or an inventory task. The description should make the demo
scope clear.
09:08-09:12 | UrbanCart frontend assignment
Ali: I can own the product catalog interface: product listing, a product detail screen, and responsive layout.
Put that down as 12 estimated hours, due on 12 October.
Ayesha: Please call that task Product catalog UI. We also need the demo cart interface as a separate task
so we can track it separately.
Ali: Yes. Demo cart UI will take 8 hours, due 15 October. That covers adding and removing items,
quantities, and a visible total. I am the owner of both frontend tasks.
Bilal: Are these two separate tasks rather than a single 20-hour frontend task?
Ayesha: Exactly. Two tasks, same owner, with the deadlines we just agreed. We need that separation in
the task list.
09:12-09:16 | UrbanCart backend and delivery correction
Hamza: For Product and cart APIs, I estimate 14 hours. I own it, and the deadline is 14 October. I will
provide product responses and the demo cart endpoints Ali needs.
Ayesha: Good. After that, Ali owns Website integration and testing. Let's start with a six-hour estimate and
a 17 October deadline.
Ali: Six hours is reasonable for connecting the screens and checking the demo flow. But please move that
task to 19 October. I need a little more calendar space after the API work.
Ayesha: Accepted. Website integration and testing is 6 hours, due 19 October. Also, the client has just
confirmed that final project delivery can be 20 October. That replaces the earlier 18 October date. The final
UrbanCart project deadline is 20 October.
Hamza: So the final website plan has four tasks, and the new deadline is 20 October. No payment gateway
in this phase.
Ayesha: Correct.
09:16-09:20 | QuickServe scope and manager
Bilal: The second project is QuickServe Mobile App, for client QuickServe Services. I am the project
manager. The client needs a customer app for signing in, requesting a service, and seeing the request's
current status.
Sara: Android only for the demonstration, or do we need separate native apps?
Bilal: A Flutter app demo is enough. We don't need separate Android and iOS development tasks. The
project deadline is 24 October.
Usman: What about live maps, driver tracking, and payments?
Bilal: Exclude them. This version is customer login, service booking, and booking status. Those other
features may be future work, but they must not appear as tasks in the current project.
09:20-09:24 | QuickServe screen work
Sara: I'll own Login and profile screens. That is 8 hours, due 12 October. It includes the customer login
interface and a basic profile screen.
Bilal: Please keep that as one task. We don't need to split every field into its own task.
Sara: The second task is Service booking screens. I'll own that too. I estimate 12 hours, due 17 October.
The customer selects a service, enters the request details, and sees a confirmation screen.
Hina: So Sara has two tasks, and both are mobile UI work. The API work is separate.
Bilal: Right. The transcript shouldn't turn these into generic web frontend tasks. This project is the mobile
app.
09:24-09:28 | QuickServe API assignment
Hamza: I can build Booking and account APIs for the app. The endpoint scope is basic customer account
handling, service requests, and request status. Put me as the owner.
Bilal: What's the effort estimate and delivery date?
Hamza: 16 hours, due 16 October. That's separate from the 14-hour UrbanCart API task. Please don't
merge those just because I own both.
Usman: I need those responses for mobile integration, but we can use sample responses while Hamza
works.
Bilal: Good. This is still one API task under QuickServe. There is no new shared platform project.
09:28-09:32 | QuickServe integration estimate correction
Usman: I will own Mobile integration and testing. Initially I would put it at 8 hours, due 22 October.
Sara: Can that cover the booking status screen, error states, and testing login through booking? Eight
sounds a little tight.
Usman: You're right. Make the final estimate 10 hours. Keep the task deadline at 22 October. I will connect
the mobile UI to the API, display request status, and test the whole customer flow.
Bilal: Final agreement: Mobile integration and testing, Usman, 10 hours, 22 October. QuickServe still
delivers on 24 October. Don't keep the earlier eight-hour estimate.
Ayesha: That's four tasks for QuickServe as well. We are not adding maps or payment tasks.
09:32-09:36 | HelpDeskPro scope and manager
Hina: Third project is HelpDeskPro AI Assistant, for client HelpDeskPro Solutions. I am managing it. They
want a support assistant that answers questions from a supplied FAQ document and passes unresolved
questions to a human team.
Zain: Does the assistant need to send emails or connect to a real ticketing service?
Hina: No external message sending is required. Human escalation can be a saved record in the demo. We
are building a support proof of concept, not integrating their full support system.
Maryam: We should keep an explicit boundary that the assistant uses the FAQ content instead of guessing
unsupported answers.
Hina: Agreed. The project deadline is 22 October. We will test it with some questions that aren't in the
document too.
09:36-09:40 | HelpDeskPro document work
Maryam: I'll own FAQ document processing. It should prepare the supplied FAQ so the assistant can
retrieve relevant content. I estimate 10 hours, due 13 October.
Hina: Please make the task description clear: prepare and retrieve from the FAQ. Don't make a separate
task for every FAQ topic.
Zain: I can then own Assistant answer generation. I'll use the prepared content, connect the model, and
handle the response structure.
Hina: Give us the estimate and date for that task.
Zain: 14 hours, due 17 October. If the FAQ doesn't support an answer, the assistant should say it cannot
resolve the question rather than inventing a response.
09:40-09:44 | HelpDeskPro escalation
Zain: The next task is Human escalation flow. I can own it as well: save unresolved questions so they can
be reviewed by a person. The estimate is 6 hours, due 18 October.
Bilal: Are you assigning those escalated questions to another employee now?
Hina: No, not as new project tasks from this planning meeting. The feature is a saved escalation record in
the client's demo. Keep our development task assigned to Zain.
Ayesha: The distinction matters. Discussion of end users should not create employees in our own company
directory.
Hina: Exactly. Also, the client mentioned someone called Kamran who may supply a document later.
Kamran is not a NovaWorks employee. Do not add him to our team or assign development work to him.
09:44-09:48 | HelpDeskPro testing owner correction
Hina: For Assistant evaluation and testing, I was initially considering Zain as the owner. We need to test
FAQ answers, unsupported questions, and the escalation path.
Maryam: I can own that instead. It would be better if someone other than the answer-generation developer
checks the results.
Hina: Agreed. Replace the earlier suggestion: Maryam is the final owner of Assistant evaluation and
testing.
Maryam: Put the estimate at 8 hours, due 21 October. I'll include normal questions and missing-answer
cases. That is separate from my ten-hour FAQ document task.
Hina: Confirmed: Maryam, 8 hours, 21 October. Final HelpDeskPro deadline stays 22 October.
09:48-09:52 | Simple accounts and team setup
Bilal: Please don't spend time building a registration flow. We can use one administrator account, our three
manager accounts, and the six developer accounts.
Ayesha: The team names and specializations can be hardcoded or loaded from a setup script. The script
may create those users with demo passwords. People should be able to log in using the supplied
credentials.
Hina: Agreed. We do not need signup, forgot password, email verification, or a screen for creating and
editing users. This is a hackathon demonstration with fictional accounts.
Sara: We still need the existing people available to the AI so it assigns the right names.
Bilal: Exactly. The directory is input to the AI. Projects and tasks should come from the meeting rather than
requiring someone to enter all twelve tasks manually.
09:52-09:56 | CRM creation flow
Ayesha: The administrator pastes this transcript inside the CRM and clicks Create from Transcript. A valid
result should automatically save all three projects and their tasks.
Hina: If a required person or date cannot be resolved, show a clear message and let the administrator
correct it. Do not invent an employee. For this meeting, the final recap supplies all the required
information.
Bilal: After creation, show project cards and a project detail screen. Each task needs its owner, deadline,
description, and estimated hours. A manager can open their projects; a developer can open their assigned
task list.
Usman: Do we need charts, completion percentages, timesheets, or budgets?
Ayesha: No. No cost calculation or progress monitoring. Simple login, project lists, task lists, and transcript
automation are enough. Saved projects and tasks should remain after a refresh.
09:56-10:00 | Final recap
Ayesha: Final recap: UrbanCart Website, client UrbanCart Clothing, manager Ayesha, deadline 20 October.
Ali owns Product catalog UI: 12 hours, 12 October. Ali owns Demo cart UI: 8 hours, 15 October. Hamza
owns Product and cart APIs: 14 hours, 14 October. Ali owns Website integration and testing: 6 hours, 19
October.
Bilal: QuickServe Mobile App, client QuickServe Services, manager Bilal, deadline 24 October. Sara owns
Login and profile screens: 8 hours, 12 October. Sara owns Service booking screens: 12 hours, 17 October.
Hamza owns Booking and account APIs: 16 hours, 16 October. Usman owns Mobile integration and testing:
10 hours, 22 October.
Hina: HelpDeskPro AI Assistant, client HelpDeskPro Solutions, manager Hina, deadline 22 October. Maryam
owns FAQ document processing: 10 hours, 13 October. Zain owns Assistant answer generation: 14 hours,
17 October. Zain owns Human escalation flow: 6 hours, 18 October. Maryam owns Assistant evaluation and
testing: 8 hours, 21 October.
Ayesha: Those are the final decisions. Keep the rejected features out. The company already has its nine
employees. Create three projects with twelve tasks, then show them in the CRM. That's all for this meeting.
```
