# EAR Teacher Portal — Firebase setup

This branch prepares Google sign-in and private Firestore reports. It has not been deployed. The existing appearance, status-first form, editing/removal and blank Tests Management section are retained. The old Python server is not used by this version.

## 1. Add your web app configuration
In Firebase Console, open Project settings > General > Your apps. Register a Web app (</>) if necessary and find its firebaseConfig.
Edit index.html on the firebase-setup branch. Search for REPLACE THESE VALUES.
Replace the quoted placeholders for all six variables:
- FIREBASE_API_KEY → apiKey
- FIREBASE_AUTH_DOMAIN → authDomain
- FIREBASE_PROJECT_ID → projectId
- FIREBASE_STORAGE_BUCKET → storageBucket
- FIREBASE_MESSAGING_SENDER_ID → messagingSenderId
- FIREBASE_APP_ID → appId

Keep the quotes. Use the values Firebase gives you; do not guess the bucket or domain.
These are browser app configuration values. Do not put a service-account private key in HTML or GitHub.

## 2. Install the access rules first
Open Firestore Database > Rules. Replace the rules with the complete contents of firestore.rules and click Publish. This assumes the default Firestore database.
The rules require Google authentication, a verified email, an approved teacher document and ownership of the teacher workspace. No client can approve themselves.
If this Firebase project already contains another app's data/rules, merge the rules carefully rather than replacing its unrelated rules.

## 3. Authorize the website domain
Authentication > Settings > Authorized domains:
- Firebase Hosting: confirm YOUR_PROJECT_ID.web.app is allowed.
- GitHub Pages (if used later): add lucaszhou-code.github.io (no https or /Recuperation).
- Local testing: add localhost manually if absent.
Google must be enabled under Authentication > Sign-in method.

## 4. Approve teachers manually
After a teacher first tries Google sign-in, Firebase Authentication > Users shows their UID. The portal also displays the UID when approval is missing.
In Firestore > Data:
1. Create collection teachers.
2. Document ID: paste the teacher's exact Authentication UID.
3. Add field active, type boolean, value true.
4. Save, then have the teacher sign in again.
Do this for your own account first. You do NOT need to create the reports subcollection; the first report creates it.
Set active to false to block future database access. Previously viewed information cannot be taken back from someone.
Only approve actual teachers. School email alone does not prove someone is a teacher.
Each teacher's reports live at teachers/TEACHER_UID/reports/REPORT_ID.
Project administrators with Firebase Console access can still access database data.

## 5. Test before school use
Serve the folder over HTTP, not by double-clicking index.html. For example, use VS Code Live Server on localhost.
With two approved test Google accounts and fictional students:
- Teacher A creates, edits and removes a report.
- Teacher B sees an empty independent workspace.
- Sign out: report rows and editor fields disappear.
- An unapproved Google account gets no report access.
Use Firestore Rules Playground or Emulator Suite to verify: unauthenticated requests fail; A cannot read/write/delete B's report; clients cannot change teachers/UID approval documents; invalid grades/absences fail.
Google sign-in and deployed rules have not been live-tested against your project yet. Existing demo or Python-server records are not migrated automatically.

## 6. Publish later
Choose one website host:
A. Firebase Hosting with GitHub storing the source (recommended if you want to use the Hosting you already created).
B. GitHub Pages hosting index.html, with Firebase providing Authentication and Firestore.
You do not need both website hosts.

For Firebase Hosting, after configuration and tests:
- Download/clone this branch.
- Install Firebase CLI, then run firebase login.
- Run firebase use --add and select your Firebase project.
- Run firebase deploy --only firestore:rules,hosting.
The included firebase.json uploads only index.html; it does not upload the old server or instructions.
For future automatic GitHub deployments, run firebase init hosting:github and follow Firebase's setup prompts for lucaszhou-code/Recuperation. Choose the intended deployment branch; no build step is needed.
The generated Hosting workflow deploys the website, not Firestore rules. Publish rule changes separately.
Do not merge to main or enable automatic deployment until placeholders are replaced and testing passes.

Official references:
- https://firebase.google.com/docs/auth/web/google-signin
- https://firebase.google.com/docs/firestore/security/rules-conditions
- https://firebase.google.com/docs/hosting/github-integration
