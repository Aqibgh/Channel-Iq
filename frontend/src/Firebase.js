import { initializeApp } from "firebase/app";
import { getAuth, GoogleAuthProvider } from "firebase/auth";
import { getFirestore } from "firebase/firestore";
import { getStorage } from "firebase/storage";

const firebaseConfig = {
  apiKey: process.env.REACT_APP_FIREBASE_API_KEY,
  authDomain: process.env.REACT_APP_FIREBASE_AUTH_DOMAIN,
  projectId: process.env.REACT_APP_FIREBASE_PROJECT_ID,
  storageBucket: process.env.REACT_APP_FIREBASE_STORAGE_BUCKET,
  messagingSenderId: process.env.REACT_APP_FIREBASE_MESSAGING_SENDER_ID,
  appId: process.env.REACT_APP_FIREBASE_APP_ID,
  measurementId: process.env.REACT_APP_FIREBASE_MEASUREMENT_ID,
};

const requiredConfig = [
  "apiKey",
  "authDomain",
  "projectId",
  "storageBucket",
  "messagingSenderId",
  "appId",
];

const missingConfig = requiredConfig.filter((key) => !firebaseConfig[key]);
export const firebaseConfigured = missingConfig.length === 0;

// Keep the public demo renderable without publishing Firebase credentials.
// Authentication and persistence become available as soon as the documented
// REACT_APP_FIREBASE_* values are supplied.
const app = firebaseConfigured ? initializeApp(firebaseConfig) : null;

export const auth = app ? getAuth(app) : null;
export const provider = app ? new GoogleAuthProvider() : null;
export const db = app ? getFirestore(app) : null;
export const storage = app ? getStorage(app) : null;
export const clientId = process.env.REACT_APP_GOOGLE_CLIENT_ID || "";

export default app;
