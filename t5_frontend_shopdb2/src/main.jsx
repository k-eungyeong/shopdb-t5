<<<<<<< Updated upstream
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'
=======
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { AuthProvider } from "./auth/AuthContext";
import "./index.css";
import App from "./App.jsx";
>>>>>>> Stashed changes

createRoot(document.getElementById("root")).render(
  <StrictMode>
<<<<<<< Updated upstream
    <App />
  </StrictMode>,
)
=======
    <BrowserRouter>
      <AuthProvider><App /></AuthProvider>
    </BrowserRouter>
  </StrictMode>,
);
>>>>>>> Stashed changes
