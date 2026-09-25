# EAR Teacher Portal

This update keeps the existing colors, cards, table, and general layout. It adds Recuperation Management and an intentionally blank Tests Management section.

## Available now

- Choose one of four student statuses first. Grade reports require only a grade; absence reports require only missed and total classes, besides student, class, and subject.
- Reuse students from your own previous reports. Class and subject offer suggestions and carry forward between entries. Add another keeps the status and class context for batch entry.
- Remove your own reports with a confirmation. Removal hides the report; the backend retains a soft-deleted copy for administrator recovery.
- No solution notes, reflection prompts, recovery-task descriptions, or recovery-plan section.
- Status is the teacher's selection, not calculated from unconfirmed school thresholds. Each student/subject can have one active grade report and one active absence report per teacher.

## Hosting requirement

GitHub Pages serves only the HTML demonstration. It cannot run the included Python teacher server. The private workflow is implemented but is not deployed by uploading these files to GitHub. Until a teacher server is hosted, click **Try fictional demo**. That demo has two fictional examples; all edits disappear when the tab reloads. It never uses old browser-saved reports or pretends that selecting a teacher is authentication.

To activate actual private accounts, host `index.html` and `teacher_server.py` together on a school-approved Python host with a persistent private disk and HTTPS reverse proxy. This server serves the HTML and the API from one origin. It intentionally does not expose the database or arbitrary files and is not a school SSO integration.

## Local setup for the school's administrator

Requires Python 3.10 or later with SQLite and scrypt support. No third-party Python packages.

1. Store the private database outside the public/repository folder by setting `EAR_DATA_DIR` to an administrator-controlled persistent directory.
2. Create each **verified staff** account using:

   `python3 teacher_server.py add-teacher teacher@ear.com.br "Teacher Name"`

   Replace the example address and name. The command prompts privately for a password and confirmation. It does not put passwords in source files. A school email suffix alone is not proof of being a teacher; the administrator must verify the person's staff role before provisioning the account. Public sign-up is intentionally absent.
3. For local evaluation, run `python3 teacher_server.py serve` and open `http://localhost:8000`.
4. For hosted use, set `EAR_ORIGIN` to the exact HTTPS origin, for example `https://teachers.school.example`, with no trailing path. Start the server behind an HTTPS reverse proxy, forwarding to its loopback listener. Set timeouts and request-size limits at the proxy. This reference server should be reviewed and load-tested by school IT before deployment with actual records.
5. Keep the private disk, backups, and staff credentials out of GitHub. Establish the school's backup, password-reset, account-revocation, and retention procedures. Do not use a public static directory for `EAR_DATA_DIR`.

## Privacy and ownership

Passwords are hashed using salted scrypt. Sessions use random server-side tokens, HttpOnly/SameSite cookies, and Secure cookies under HTTPS. Sessions expire after eight hours. Writes require a matching Origin. Login attempts are rate limited. No report or credential is saved to browser storage.

Every report read, update, and removal includes the authenticated teacher's owner ID in the database query. The server ignores any owner supplied by the browser. Teachers cannot see or remove another teacher's reports, even with a guessed report ID. Totals and student suggestions derive solely from that teacher's fetched records. Optimistic revisions reject stale updates and deletions. Removed reports are excluded from all teacher reads.

The previous browser demo did not track ownership. Its data is not automatically imported into any account; assigning those records to a teacher would be unsafe. Existing exported backups remain unchanged.

## Verification

Run `python3 test_teacher_server.py` to check anonymous access, two-teacher isolation, forged ownership, cross-origin writes, stale changes, irrelevant-field normalization, and deletion ownership. These tests use temporary fake accounts and a temporary database, never real school records.

No backend hosting, account provisioning, or actual student-data migration has been performed by this code update.
