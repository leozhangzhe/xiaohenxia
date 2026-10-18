"use client";
import { useState, useRef, useEffect, type FormEvent, type ReactNode } from "react";
import { ArrowRight, ArrowLeft, UserRound, LockKeyhole, Eye, EyeOff, LoaderCircle, CircleCheck, AlertCircle } from "lucide-react";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { GlassButton, GradientBackground } from "@/components/ui/auth-primitives";
export interface AuthComponentProps {
 mode?:"login"|"register"; logo?:ReactNode; brandName?:string; docroot?:string; csrfToken?:string;
 initialError?:string; initialSuccess?:string; next?:string; version?:string;
}
/** Same-origin native POST: only Python's response decides authentication and success. */
export function AuthComponent({mode="register",logo,brandName="消痕侠",docroot="",csrfToken="",initialError="",initialSuccess="",next="/",version=""}:AuthComponentProps) {
 const register=mode==="register";
 const [step,setStep]=useState<"username"|"password"|"confirm">("username");
 const [username,setUsername]=useState(""); const [password,setPassword]=useState(""); const [confirm,setConfirm]=useState("");
 const [visible,setVisible]=useState(false); const [pending,setPending]=useState(false); const [error,setError]=useState(initialError);
 const input=useRef<HTMLInputElement>(null); const reduced=useReducedMotion();
 const finalStep=register?step==="confirm":step==="password";
 useEffect(()=>{if(step!=="username")input.current?.focus();},[step]);
 useEffect(()=>{const restore=()=>setPending(false);window.addEventListener("pageshow",restore);return ()=>window.removeEventListener("pageshow",restore);},[]);
 function submit(event:FormEvent<HTMLFormElement>){
  if(pending){event.preventDefault();return;}
  let message="";
  if(!username.trim())message="请输入用户名。";
  else if(register&&(username.trim().length<3||username.trim().length>32))message="用户名长度需在 3–32 个字符之间。";
  else if(step!=="username"&&(!password||(register&&password.length<8)))message=register?"密码至少 8 位，建议使用至少 12 位的独立密码。":"请输入密码。";
  else if(step==="confirm"&&password!==confirm)message="两次输入的密码不一致，请重新确认。";
  else if(!csrfToken)message="安全令牌未加载，请刷新页面后重试。";
  if(message){event.preventDefault();setError(message);return;}
  setError("");
  if(!finalStep){event.preventDefault();setVisible(false);setStep(step==="username"?"password":"confirm");return;}
  // Keep native navigation and server status codes; never synthesize success.
  setPending(true);
 }
 const heading=initialSuccess?"账号已创建":step==="username"?(register?"从这里，开始。":"欢迎回来。"):step==="password"?(register?"设置你的密码。":"进入你的工作区。"):"再确认一次。";
 const description=step==="username"?(register?"创建账号，整理你的数字痕迹线索。":"登录消痕侠，继续查看与核验线索。"):step==="password"?(register?"至少 8 位，建议使用长且不重复的密码。":"输入账号密码，继续处理你的任务。"):"确认密码后，系统将创建你的账号。";
 return <div className="auth-sign-up min-h-svh bg-background text-foreground">
  <header className="auth-brand"><a href={docroot+(register?"/register":"/login")} aria-label="消痕侠数字痕迹管理平台">{logo||<img src={docroot+"/static/img/xhen-brand.svg"} alt=""/>}<span>{brandName}<small>数字痕迹管理平台</small></span></a></header>
  <div className="auth-background" aria-hidden="true"><GradientBackground/></div>
  <main className="auth-center"><div className="auth-content">
   <AnimatePresence mode="wait" initial={false}><motion.div key={heading} initial={reduced?false:{opacity:.3,y:5}} animate={{opacity:1,y:0}} exit={{opacity:0}} transition={{duration:reduced?0:.2}} className="auth-heading"><h1>{heading}</h1><p>{initialSuccess?"注册成功，请使用刚创建的用户名和密码登录。":description}</p></motion.div></AnimatePresence>
   {initialSuccess?<div className="auth-success" role="status"><CircleCheck aria-hidden="true"/><p>{initialSuccess}</p><a className="auth-link-button" href={docroot+"/login"}>前往登录 <ArrowRight size={16}/></a></div>:
   <form method="post" action={docroot+"/"+mode} onSubmit={submit} className="auth-form" aria-label={register?"创建账号":"登录消痕侠"}>
    <input type="hidden" name="csrf_token" value={csrfToken}/>{!register&&<input type="hidden" name="next" value={next}/>}
    <fieldset aria-busy={pending}>
     {step!=="confirm"?<div className="auth-field"><label htmlFor="username">用户名</label><div className="glass-input-wrap"><div className="glass-input"><span className="glass-input-text-area"/><UserRound size={19} aria-hidden="true"/><input id="username" name="username" type="text" value={username} onChange={e=>{setUsername(e.target.value);setError("");}} readOnly={step!=="username"} autoComplete="username" placeholder={register?"设置用户名":"输入用户名"} maxLength={register?32:64} required aria-describedby={register?"username-hint":undefined}/></div></div>{register&&<small id="username-hint">3–32 个字符，首尾空格会自动去除。</small>}</div>:<><input type="hidden" name="username" value={username}/><input type="hidden" name="password" value={password}/><div className="auth-identity"><UserRound size={16}/><span>{username.trim()}</span></div></>}
     {step!=="username"&&<div className="auth-field"><label htmlFor={step==="confirm"?"confirm":"password"}>{step==="confirm"?"确认密码":"密码"}</label><div className="glass-input-wrap"><div className="glass-input"><span className="glass-input-text-area"/><LockKeyhole size={19} aria-hidden="true"/><input ref={input} id={step==="confirm"?"confirm":"password"} name={step==="confirm"?"confirm":"password"} type={visible?"text":"password"} value={step==="confirm"?confirm:password} onChange={e=>{if(step==="confirm")setConfirm(e.target.value);else setPassword(e.target.value);setError("");}} autoComplete={register?"new-password":"current-password"} placeholder={step==="confirm"?"再次输入密码":"输入密码"} minLength={register?8:undefined} required aria-describedby={error?"auth-error":undefined}/><button type="button" className="auth-eye" onClick={()=>setVisible(!visible)} aria-label={visible?"隐藏密码":"显示密码"} aria-pressed={visible}>{visible?<EyeOff size={18}/>:<Eye size={18}/>}</button></div></div></div>}
     {error&&<div id="auth-error" className="auth-feedback" role="alert"><AlertCircle size={17} aria-hidden="true"/><p>{error}</p></div>}
     <GlassButton type="submit" disabled={pending||!csrfToken} className="auth-submit">{pending?<><LoaderCircle className="auth-spinner" size={17}/>正在{register?"创建账号":"登录"}…</>:<>{finalStep?(register?"创建账号":"登录工作区"):"继续"}<ArrowRight size={17} aria-hidden="true"/></>}</GlassButton>
     {step!=="username"&&<button className="auth-back" type="button" onClick={()=>{setStep(step==="confirm"?"password":"username");setVisible(false);setError("");}}><ArrowLeft size={15}/>返回上一步</button>}
    </fieldset>
   </form>}
   {!initialSuccess&&<p className="auth-switch">{register?"已有账号？":"还没有账号？"} <a href={docroot+(register?"/login":"/register")}>{register?"立即登录":"创建账号"}<ArrowRight size={13} aria-hidden="true"/></a></p>}
  </div></main>
  <footer className="auth-boundary"><p>仅查询本人或已获授权的目标 · 数据覆盖有限，线索需要人工核验。</p><p>当前数据源未发现匹配，不代表不存在相关信息。</p><p>申请记录需要人工跟进，不会自动删除平台内容。<span className="auth-version">{version&&"v"+version}</span></p></footer>
 </div>;
}
