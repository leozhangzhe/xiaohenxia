import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { LiquidGlassButtonDemo } from "@/components/ui/liquid-glass-button-demo";
import "@/styles/globals.css";

const root = document.getElementById("root");
if (root) createRoot(root).render(<StrictMode><LiquidGlassButtonDemo /></StrictMode>);
