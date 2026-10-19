import { LiquidMetalShader } from "@/components/ui/liquid-metal-shader";

/** Shared visual profile; no authentication, task or query data enters the renderer. */
export function AppBackground({mode="auth"}: {mode?: "auth"|"workspace"}) {
  return <LiquidMetalShader mode={mode} interactive={mode==="auth"}
    speed={mode==="auth"?.46:.14} distortion={mode==="auth"?.49:.24}
    pixelRatio={mode==="auth"?1.5:1.25}/>;
}
