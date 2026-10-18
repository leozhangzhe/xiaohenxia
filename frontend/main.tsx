import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { MotionConfig } from "framer-motion";
import { AuthComponent } from "@/components/ui/sign-up";
import "@/styles/globals.css";
import "@/styles/glass.css";
import "@/styles/auth.css";
const element=document.getElementById("auth-root");
if(element){const d=element.dataset;createRoot(element).render(<StrictMode><MotionConfig reducedMotion="user"><AuthComponent mode={d.mode==="login"?"login":"register"} docroot={d.docroot} csrfToken={d.csrfToken} initialError={d.error} initialSuccess={d.success} next={d.next} version={d.version}/></MotionConfig></StrictMode>);}
else{const demo=document.getElementById("root");if(demo)createRoot(demo).render(<main style={{padding:40}}>正式页面由 Python 提供 Session 与 CSRF。请从 <a href="http://127.0.0.1:5001/login">消痕侠登录页</a> 进入；此 Vite 页面不提供模拟登录注册。</main>);}
