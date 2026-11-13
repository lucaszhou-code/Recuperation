# EAR Teacher Portal — Firebase and admin setup

Firebase loads directly in index.html from Google's CDN. No local Firebase installation is needed when you use GitHub Pages and Firebase Console.

## Activate this update
1. In Firebase Authentication > Sign-in method, enable **Email/Password**. Keep Google enabled.
2. In Firestore Database > Rules, paste the complete firestore.rules file from this repository and click Publish. Saving the file to GitHub does not publish database rules.
3. Open the updated website and sign in with Google as **lucas.zhou@ear.com.br**. The Admin tab appears for that verified account.
4. Under Admin > Set my admin password, enter your own password. Firebase requires at least six characters (your project's policy may require more). The requested four-character password cannot be used. No admin password is embedded in HTML.
5. You can subsequently use either Google or email/password to sign in.

If the updated site does not appear, confirm your host deployed the latest main branch, then refresh. With Firebase Hosting, deploying GitHub source and publishing rules are separate actions.

## Create accounts
In Admin, enter a teacher's name, email and initial password, then choose Create account.
The account is created in Firebase Authentication and an approved teachers/UID record is created automatically. You remain signed in as admin.
Share the initial password privately with the teacher. Passwords are sent to Firebase Authentication, not stored in Firestore.
If the email already exists, use Firebase Console to manage that existing account. This form creates new accounts only.
If approval fails, the page attempts to remove the newly created login account. If cleanup also fails, it displays the UID for administrator review.

## Access and privacy
The admin permission requires the exact email lucas.zhou@ear.com.br and a verified email in the Firebase authentication token. Merely typing that email into a form does not grant admin access.
Only that admin can create or update teacher approval documents through the website. Approved teachers can use Google or email/password.
Reports remain under teachers/UID/reports and only their owner can read, edit or delete them through the app, including when the administrator is signed in.
Firebase project administrators can still access data through Firebase Console.
To revoke access, set the teacher document's active field to false in Firebase Console. This blocks later database requests, but cannot take back already viewed information.
Firebase client account registration can be called outside this UI. Such accounts do not gain portal access unless approved; Firestore rules enforce approval.

## Firebase configuration
The six FIREBASE_* variables in index.html retain your existing web app configuration.
Keep the website domain under Authentication > Settings > Authorized domains.
Never put service-account credentials or an administrator password into HTML.

## Verification
JavaScript syntax and mocked account creation tests passed, covering retained admin session, rejection of other/unverified admin identities, cleanup after failed approval, password minimum, and password linking.
Live Google/email sign-in, the rendered Admin tab and deployed Firestore rules still need testing against your Firebase project.
Before using real student data, test with two fictional teacher accounts: each can manage its own reports and cannot access another teacher's records. In Firestore Rules Playground or Emulator Suite, also check that an ordinary teacher cannot modify approvals and that an unverified admin email is denied admin access.

Official documentation:
- https://firebase.google.com/docs/auth/web/password-auth
- https://firebase.google.com/docs/firestore/security/rules-conditions
