import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import Demo from "@/demo";
import { SignIn1 } from "@/components/ui/modern-stunning-sign-in";
import "@/styles/globals.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    {window.location.pathname === "/sign-in" ? <SignIn1 /> : <Demo />}
  </StrictMode>,
);
