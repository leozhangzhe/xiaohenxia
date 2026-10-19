"use client";
/* React API adapted from Nacre UI (MIT). See third_party/liquid-metal/README.md.
 * Both template and React surfaces use the same AppBackground renderer. */
import { useEffect, useRef, type ComponentPropsWithoutRef } from "react";
import styles from "./liquid-metal-shader.module.css";

export interface LiquidMetalShaderProps extends ComponentPropsWithoutRef<"div"> {
  baseColor?: string;
  distortion?: number;
  highlightColor?: string;
  interactive?: boolean;
  metalColor?: string;
  pixelRatio?: number;
  scale?: number;
  speed?: number;
  mode?: "auth" | "workspace";
}
declare global {
  interface Window {
    AppBackground?: {
      mount(root: HTMLElement, options?: Omit<LiquidMetalShaderProps, keyof ComponentPropsWithoutRef<"div">>): {destroy(): void};
      destroy(): void;
    };
  }
}
export function LiquidMetalShader({mode="auth", interactive=true, pixelRatio=1.5,
  speed=.46, distortion=.49, scale=1.15, baseColor="#13131e", metalColor="#9fa9c8",
  highlightColor="#e4e9ff", className="", ...props}: LiquidMetalShaderProps) {
  const element=useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!element.current) return;
    const background=window.AppBackground?.mount(element.current, {mode,interactive,pixelRatio,
      speed,distortion,scale,baseColor,metalColor,highlightColor});
    return () => background?.destroy();
  }, [mode,interactive,pixelRatio,speed,distortion,scale,baseColor,metalColor,highlightColor]);
  return <div {...props} ref={element} className={`app-background ${styles.root} ${className}`}
    data-mode={mode} aria-hidden="true"/>;
}
if (import.meta.hot) import.meta.hot.dispose(() => window.AppBackground?.destroy());
