
PROPOSED SYSTEM ARCHITECTURE
Student Grade Monitoring Application
Sagay National High School – Grade 12 STEM (Lovelace)
(Suggested for Chapter III: Methodology – System Design)
1. Purpose and Overview
This document describes how the Student Grade Monitoring Application is structured, how its parts communicate, how grades are computed and stored, and how the system is secured, deployed, and tested. It supports the three objectives of the study: developing the application, evaluating its usability, and verifying its functional performance and computational accuracy.
The system has two clients and one server. Students use a mobile application to view their grades. Teachers and authorized administrators use a web portal to encode scores and manage records. Both clients talk to a single REST API, which performs every computation and is the only component allowed to read or write the database.
2. Requirements Summary
2.1 Functional requirements
ID
Requirement
User
FR1
Log in with a username (the LRN for students) and password; forced password change at first login.
All
FR2
View subject grades per quarter.
Student
FR3
View the semester final grade of each subject and the general average per semester.
Student
FR4
See when grades were last updated.
Student
FR5
Create assessments (component, quarter, highest possible score) for an assigned class.
Teacher
FR6
Encode, edit, and save learners’ scores for an assessment.
Teacher
FR7
Have quarterly grades, semester final grades, and general averages computed automatically.
System
FR8
Review computed grades of an assigned class.
Teacher
FR9
Manage students (including CSV import), sections, subjects, and teacher assignments.
Administrator
FR10
Reset passwords and activate or deactivate accounts.
Administrator
FR11
Edit grading configuration (component weights, transmutation table).
Administrator
FR12
View the audit log of grade-related changes; lock a quarter after grades are finalized.
Administrator

2.2 Non-functional requirements
Quality
Requirement (proposed target)
How the architecture addresses it
Accuracy
App-computed grades match the manual computation for every learner in the test section.
One server-side engine, exact decimal arithmetic, unit tests from real class records.
Security
A user can reach only the data the role allows.
JWT authentication, role and object-level checks, HTTPS, audit log.
Privacy
Only necessary learner data is collected and only authorized staff can see it.
Data minimization, role-based access, consent, retention rules (Section 9).
Performance
Grades screen loads within about 3 seconds on a typical mobile connection; saving a class’s scores within about 5 seconds.
Small JSON payloads, indexed queries, recomputation limited to affected learners.
Usability
Learners and teachers can complete main tasks without training.
Few screens, spreadsheet-style encoding, CSUQ evaluation.
Availability
Available during school days; recoverable after failure.
Container restart policy, daily backups, tested restore.
Maintainability
Grading rules can change without a code release.
Weights and transmutation stored as data; layered code; automated tests.
Portability
Works on common Android devices and modern browsers.
Flutter and standard web technologies; tested on a device matrix.

3. Architectural Decisions
Decision
Rationale
Alternative considered
Three-tier client–server
Separates display, business logic, and data; each part can change independently.
Single desktop app (no remote access for students).
All grade computation on the server
One source of truth; identical results on every device; easy to test and audit.
Computing on the phone (risk of inconsistent results).
Separate web portal for teachers
Score entry is data-heavy and suits a keyboard and a large screen.
Teacher features inside the mobile app.
REST over HTTPS with JSON
Simple, widely supported, easy to test with standard tools.
GraphQL (more than this small system needs).
JWT access and refresh tokens
Stateless for the mobile client; short-lived access limits damage if leaked.
Server sessions with cookies.
PostgreSQL
Strong integrity constraints, transactions, and exact numeric types for grades.
SQLite (weak concurrency and backup tooling for a shared server).
Grading rules as data
Weights and the transmutation table can be corrected or updated by an administrator.
Hard-coded constants.
Audit log for grade changes
Accountability and a way to explain any grade.
No history (cannot trace disputes).
Docker Compose deployment
Repeatable setup on a small server; simple upgrades and rollbacks.
Manual installation on the host.

4. System Architecture
Figure 1 shows the three layers. The presentation layer holds the two clients. The application layer holds the reverse proxy and the Django REST Framework API, which contains four modules: authentication and access control, records management, the grade engine, and audit logging. The data layer holds PostgreSQL, the editable grading configuration, and the backups.

Figure 1. Layered architecture of the Student Grade Monitoring Application
5. Component Design
5.1 Student mobile application (Flutter)
The app is read-only and has five screens (Figure 2). It uses four internal layers so that screens never talk to the network directly.
Layer
Responsibility
Presentation
Screens and widgets: login, change password, dashboard, subject grades, profile. Shows loading, empty, and error states.
State
Holds the current session and the loaded grades; reacts to events such as “refresh” or “session expired” (for example with Riverpod or Bloc).
Domain
Plain models (Student, SubjectGrade, SemesterSummary). No computation: it displays what the API returns.
Data
API client, token handling, and secure storage. Access token kept in memory; refresh token in the device’s secure storage.

Pull-to-refresh and an automatic refresh on app start; each screen shows the “last updated” time from the server.
If the access token expires, the app silently requests a new one; if the refresh token is also invalid, it returns to the login screen.
Network failures show a clear message and a retry button. An optional read-only cache of the last downloaded grades may be shown with a “may be outdated” notice.

Figure 2. Screen map of the student mobile application
5.2 Teacher and administrator web portal (React)
The portal is a single-page application. Routes are guarded by role, so the administrator pages are hidden from teachers (the API enforces the same rules, so hiding a page is only a convenience).

Figure 3. Page map of the teacher and administrator web portal
The score entry grid is the most important screen. It should support:
keyboard navigation between cells and pasting a column of scores from a spreadsheet;
instant validation (blank allowed, otherwise 0 to the highest possible score) with the invalid cell highlighted;
a warning when the teacher leaves with unsaved changes, and one “Save” action that sends all scores in a single request;
class totals and a preview of the resulting quarterly grades after saving.
5.3 Backend API (Django REST Framework)
Django app
Contains
Notes
accounts
User model, login, token refresh, change and reset password, roles
Custom user model with a role field; login throttling.
academics
StudentProfile, Section, Subject, ClassAssignment, CSV import
Admin-only writes; teachers and students read what they are allowed to.
grading
Assessment, Score, QuarterGrade, SemesterGrade, GeneralAverage, GradingConfig, engine
The engine lives in a plain Python module with no database calls.
audit
AuditLog and the helper that records changes
Written in the same transaction as the change.
common
Permissions, pagination, error format, health check
Shared by all apps.

Each request passes through the same chain: authentication, role permission, object-level permission (for example, “is this teacher assigned to this class?”), serializer validation, a service function that performs the work inside a database transaction, and finally the response. Views stay thin; business rules live in service functions so they can be tested without HTTP.
5.4 Grade engine
The engine receives the learner’s scores, the highest possible scores, and the active grading configuration, and returns the quarterly grade, semester final grade, and general average. Keeping it free of database access makes it easy to unit-test with worked examples from real class records.
Computation steps (following the grading policy of DepEd Order No. 8, s. 2015 as implemented by the school; weights and the transmutation table must be verified against current issuances):
Percentage Score (PS) of each component = (sum of raw scores ÷ sum of highest possible scores) × 100.
Weighted Score (WS) = PS × the component weight for the subject type.
Initial Grade = WS(Written Work) + WS(Performance Tasks) + WS(Quarterly Assessment).
Quarterly Grade = Initial Grade converted with the transmutation table.
Semester Final Grade = average of the semester’s two quarterly grades.
General Average = average of the Semester Final Grades of all subjects.
Worked example (illustrative values only): a core subject with weights of 25% Written Work, 45% Performance Tasks, and 30% Quarterly Assessment.
Component
Raw / highest possible
Percentage Score
Weight
Weighted Score
Written Work
78 / 100
78.00
25%
19.50
Performance Tasks
85 / 100
85.00
45%
38.25
Quarterly Assessment
42 / 50
84.00
30%
25.20
Initial Grade



82.95

An Initial Grade of 82.95 falls in the transmutation band that gives a Quarterly Grade of 89. If the second quarter is 91, the Semester Final Grade is (89 + 91) ÷ 2 = 90. For a student with semester final grades of 90, 88, 92, 89, and 91 in five subjects, the General Average is 450 ÷ 5 = 90.
Recomputation rules
Triggers: scores saved, an assessment’s highest possible score changed, an assessment deleted, or the grading configuration changed.
Scope: only the affected learners, subject, and quarter, followed by their semester grade and general average. A configuration change recomputes everything and is logged.
Safety: recomputation runs in the same database transaction as the save, so a failure never leaves new scores with old grades. Running it twice gives the same result.
Edge cases
Situation
Handling
Blank score vs. zero
Blank means “not yet encoded” and is excluded from the total; zero is a real score. The class view flags learners with blanks.
Component has no assessments yet
No quarterly grade is produced; the app shows “not yet available” instead of a misleading number.
Only one quarter available
The semester final grade and general average are shown as incomplete until both quarters exist.
Score above the highest possible score
Rejected with a validation error (HTTP 400).
Edit after grades are finalized
Blocked if the quarter is locked; an administrator must unlock it (logged).
Learner transfers or drops
Account is deactivated, not deleted; records are kept for audit.
Rounding
Exact decimals throughout; rounding applied only where the school’s class record applies it, using one documented rule.

6. Data Design
Figures 4 and 5 show the entities and relationships. Entities in red are produced by the grade engine; those in amber hold configuration and history.

Figure 4. Entity-relationship diagram: people, classes, and scores

Figure 5. Entity-relationship diagram: computed grades, configuration, and audit
Constraints and indexes
Rule
Purpose
User.username unique; StudentProfile.lrn unique, 12 digits
No duplicate accounts or learners.
Score unique on (assessment_id, student_id)
One score per learner per assessment.
QuarterGrade unique on (student_id, subject_id, quarter)
One computed grade per learner, subject, and quarter; makes recomputation an update.
SemesterGrade unique on (student_id, subject_id, semester); GeneralAverage unique on (student_id, semester)
Same idea at semester level.
ClassAssignment unique on (subject_id, section_id, school_year)
Each subject in a section has exactly one responsible teacher.
Grade and score columns use exact decimals, for example NUMERIC(5,2)
Avoids floating-point rounding differences.
Indexes on Score(student_id), Score(assessment_id), QuarterGrade(student_id, quarter), AuditLog(entity, timestamp)
Fast student grade lookups and audit searches.
Foreign keys use PROTECT; people are deactivated, never deleted
Prevents accidental loss of academic records.
QuarterLock (class_assignment_id, quarter, locked_by, locked_at) – optional table
Supports locking finalized quarters.

Data lifecycle
At the start of a school year the administrator creates the new sections and assignments and imports learners from a CSV file. At the end of the year, records are kept read-only. Data is retained only as long as the school needs it, and removal follows the school’s records policy. Schema changes are applied through versioned database migrations.
7. API Design
Conventions
Base path /api/v1/; JSON requests and responses; dates in ISO 8601 with time zone.
Authentication header: Authorization: Bearer <access token>.
Status codes: 200 OK, 201 Created, 400 validation error, 401 not authenticated or token expired, 403 not allowed, 404 not found, 409 conflict (for example, quarter locked), 429 too many requests, 500 server error.
Every error uses one format so the clients can show messages consistently.
List endpoints are paginated; the grades endpoint returns one student’s semester in a single response.
Method
Endpoint
Role
Purpose
POST
/auth/login/
All
Username and password → access and refresh tokens
POST
/auth/refresh/
All
Renew the access token (refresh token rotated)
POST
/auth/logout/
All
Invalidate the refresh token
POST
/auth/change-password/
All
Change password (required on first login)
GET
/me/
All
Current user and role
GET
/me/grades/?semester=
Student
Own quarterly grades, semester finals, general average
GET
/teacher/classes/
Teacher
Assigned subject–section classes
GET, POST
/classes/{id}/assessments/
Teacher
List or create assessments
PATCH, DELETE
/assessments/{id}/
Teacher
Edit or remove an assessment
GET, PUT
/assessments/{id}/scores/
Teacher
Read or bulk-save scores (triggers recomputation)
GET
/classes/{id}/grades/
Teacher
Computed grades for the class
GET, POST
/admin/students/
Admin
List or create learners
POST
/admin/students/import/
Admin
Import learners from CSV
POST
/admin/users/{id}/reset-password/
Admin
Issue a temporary password
GET, POST
/admin/sections/, /subjects/, /assignments/
Admin
Manage structure and teacher assignments
POST, DELETE
/admin/classes/{id}/quarters/{q}/lock/
Admin
Lock or unlock a quarter
GET, PUT
/admin/grading-config/
Admin
View or update weights and transmutation table
GET
/admin/audit-log/
Admin
Search grade-change history
GET
/health/
Public
Service status for monitoring

Sample exchanges
Login request and response:
POST /api/v1/auth/login/
{ "username": "000000000000", "password": "********" }

200 OK
{ "access": "<jwt>", "refresh": "<jwt>",
  "role": "student", "must_change_password": false }

Student grades (response is limited to the logged-in learner):
GET /api/v1/me/grades/?semester=1

200 OK
{
  "student": { "lrn": "000000000000", "name": "Sample Student",
               "section": "Lovelace" },
  "semester": 1,
  "subjects": [
    { "subject": "Subject A", "q1": 89, "q2": 91, "final": 90 },
    { "subject": "Subject B", "q1": 87, "q2": 89, "final": 88 }
  ],
  "general_average": 89,
  "last_updated": "2027-01-15T09:30:00+08:00"
}

Error format:
403 Forbidden
{ "error": { "code": "forbidden",
             "message": "You are not assigned to this class." } }

8. Key Interaction: From Score Entry to Student View
Figure 6 follows one complete cycle. A teacher saves scores; the API checks permissions and validity, stores the scores and an audit record in one transaction, and has the grade engine recompute the affected grades. Later, a student requests grades and the API returns only that student’s records, identified from the token rather than from any identifier the client sends.

Figure 6. Sequence of score entry, recomputation, and student viewing
9. Security and Data Privacy
Authentication and passwords
Item
Proposed setting
Access token
Short-lived (for example, 15 minutes).
Refresh token
Longer-lived (for example, 7 days), rotated on use, invalidated on logout.
Password storage
Salted hash using Django’s password hashers; plain passwords are never stored or logged.
Initial password
Random, generated by the system, and not derived from the LRN (the LRN is not secret). Must be changed at first login.
Password rules
Minimum length, not equal to the username, not a common password.
Lockout and throttling
Temporary lockout after repeated failed logins (for example, 5 attempts); rate limits at Nginx and in the API.

Threat model
Threat
Example
Mitigation
Guessing credentials
Trying many passwords on an LRN
Throttling, lockout, strong initial passwords, forced change.
Viewing another learner’s grades
Changing an ID in a request
The student endpoint ignores client-supplied IDs and uses the token; object-level permission checks; tests for this case.
Teacher editing another class
Calling the scores endpoint for an unassigned class
ClassAssignment check on every write; 403 and audit entry.
Unauthorized grade changes
Silent edits after grades are released
Audit log with old and new values; quarter locking.
Injection
SQL injection through a search field
ORM with parameterized queries; serializer validation.
Cross-site scripting
Script in a student name or assessment title
React escapes output by default; no raw HTML rendering; Content-Security-Policy header.
Stolen token or lost phone
Someone else opens the app
Short access-token life, secure token storage, logout invalidates the refresh token, administrator can deactivate the account.
Traffic interception
Reading data on public Wi-Fi
HTTPS only with redirect from HTTP; HSTS.
Data loss
Disk failure or mistaken deletion
Daily backups, off-server copy, tested restores, no hard deletion of records.
Leaked secrets
Keys committed to a code repository
Secrets in environment variables; .env excluded from version control.

Data privacy (Data Privacy Act of 2012, Republic Act No. 10173)
Collect only what the system needs: LRN, name, section, and scores. No contact numbers, addresses, or photographs.
Obtain consent from learners and, for minors, from parents or guardians, and inform them what is stored and who can see it.
Limit access: students see only their own grades; teachers see only their assigned classes; administrators are few and named.
Keep logs free of passwords and tokens; protect backups with encryption.
Define who is responsible for handling a suspected data breach and how affected users are informed; coordinate with the school’s data protection officer.
10. Deployment and Operations
Figure 7 shows the deployment. The system runs on one small server (a low-cost virtual private server or a school machine) using Docker Compose with Nginx, the Django API, and PostgreSQL in separate containers. Only Nginx is exposed to the internet.

Figure 7. Deployment diagram
Topic
Approach
Environments
Development (each developer’s machine), and production. A staging copy is useful during the evaluation period to test updates before release.
Configuration
Environment variables for secrets and settings; a committed .env.example lists the names without values.
Build and release
Automated checks (lint and tests) before each release; container images rebuilt and restarted with Docker Compose; database migrations applied on release; the previous image kept for rollback.
Mobile distribution
Android package installed directly or through a private testing channel during the study.
Logging and monitoring
Application and Nginx logs with rotation; /health/ endpoint checked by an uptime monitor; alerts when the service or backup job fails.
Backup and restore
Scheduled database dump, kept for a set number of days, with an encrypted copy off the server. Restore tested periodically (for example, monthly).
Capacity estimate
Assuming about 40 learners, 8 subjects, and 15 assessments per subject per quarter, there are about 4,800 score rows per quarter, or under 20,000 per school year. A single small server handles this comfortably; extending to more sections requires no design change.
Time zone
Server stores UTC; the apps display Philippine time.

11. Testing Strategy
Level
What is tested
Examples of tools
Unit
Grade engine with worked examples and edge cases; validators; permission rules.
pytest
API / integration
Each endpoint with correct and incorrect roles; transaction behavior; recomputation after saves.
pytest with Django REST test client
Client
Mobile screens and state handling; portal components and the score grid validation.
Flutter test; Vitest and Testing Library
Security
Access to another learner’s data, unassigned classes, expired tokens, and lockout.
Automated tests plus a manual checklist
Accuracy (Objective 3)
Compare application-computed grades with the manual class-record computation for every learner in the section.
Comparison sheet: matches ÷ total learners-subjects
Compatibility
Several Android versions and screen sizes; common browsers (Chrome, Edge, Firefox).
Physical devices and browser testing
Usability (Objective 2)
CSUQ survey after hands-on use by students and teachers.
Questionnaire and descriptive statistics

Test cases for Objective 3 can be organized under the functional suitability characteristic of ISO/IEC 25010 (functional completeness, correctness, and appropriateness).
12. Suggested Project Structure
grade-monitoring/
|-- backend/                  Django REST Framework API
|   |-- config/               settings, urls, wsgi
|   |-- accounts/  academics/  grading/  audit/  common/
|   |-- grading/engine.py     pure functions, no database access
|   |-- tests/
|   |-- Dockerfile  requirements.txt  manage.py
|-- web/                      React + Vite + Tailwind CSS
|   |-- src/api/  auth/  pages/  components/  hooks/
|-- mobile/                   Flutter app
|   |-- lib/core/  data/  domain/  features/{auth,grades,settings}/
|-- deploy/
|   |-- docker-compose.yml  nginx.conf  backup.sh  .env.example
|-- docs/                     this document, API reference, test reports

13. Implementation Roadmap
Phase
Work
Output
1. Foundation
Requirements confirmation with teachers; collect a sample class record; set up repositories, Docker, and database.
Confirmed grading rules and a running skeleton.
2. Core API
Accounts, roles, academic records, assessments, scores, audit log.
Working API with permission tests.
3. Grade engine
Implement and test computation with real examples; configuration tables.
Engine matching manual results.
4. Teacher portal
Login, class list, assessments, score grid, class grades, admin pages.
Usable web portal.
5. Student app
Login, first-login password change, dashboard, subject grades, profile.
Installable Android app.
6. Hardening and deployment
Security tests, HTTPS, backups, monitoring, data import.
Production deployment.
7. Evaluation
Accuracy testing, device testing, and the CSUQ survey.
Data for Chapters IV and V.

14. Assumptions and Risks
Assumption or risk
Impact
Response
Grading weights, transmutation table, and rounding differ from what is assumed here
Wrong grades
Verify with current DepEd issuances and the school; keep them configurable; test with real class records.
Teachers encode scores late or incompletely
Outdated or incomplete grades
Class view flags blanks; “last updated” time shown to students.
Students lack a compatible phone or data connection
Limited reach
Optional offline cache; allow viewing through a mobile browser as a later enhancement.
Server or internet outage during use
Temporary unavailability
Restart policy, backups, and monitoring; grades remain in the official records.
Privacy concerns of learners and parents
Low trust or non-compliance
Consent, data minimization, access controls, and a clear explanation of the data stored.
Application mistaken for the official record
Disputes
State clearly that official grades remain those in the school’s records.

15. Possible Future Enhancements
Read-only parent accounts, push notifications when new grades are posted, an iOS build, a read-only mobile browser view, class and subject summaries for teachers, support for other sections and grade levels, and export of grade reports. These are outside the current scope of the study.
Abbreviations
Term
Meaning
API
Application Programming Interface
CSUQ
Computer System Usability Questionnaire
ERD
Entity-Relationship Diagram
HPS
Highest Possible Score
JWT
JSON Web Token
LRN
Learner Reference Number
PS / WS
Percentage Score / Weighted Score
PT / WW / QA
Performance Tasks / Written Work / Quarterly Assessment
REST
Representational State Transfer
TLS
Transport Layer Security (the encryption behind HTTPS)

