import { useState } from "react";
import { Button, LiquidButton, MetalButton } from "@/components/ui/liquid-glass-button";

// The supplied demo, with a fluid width so it also fits narrow viewports.
export default function DemoOne() {
  const [clicks, setClicks] = useState(0);

  return (
    <section aria-label="液态玻璃按钮预览" className="space-y-4">
      <div className="relative isolate flex h-[200px] w-full max-w-[800px] items-center justify-center overflow-hidden rounded-xl bg-linear-to-br from-chart-3 via-chart-4 to-chart-5">
        <LiquidButton onClick={() => setClicks((count) => count + 1)}>
          Liquid Glass
        </LiquidButton>
      </div>
      <p role="status" className="text-sm text-muted-foreground">已点击 {clicks} 次</p>
    </section>
  );
}

export function LiquidGlassButtonDemo() {
  const [metalClicks, setMetalClicks] = useState(0);

  return (
    <main className="mx-auto max-w-4xl space-y-10 px-6 py-12">
      <header className="space-y-3">
        <h1 className="text-3xl font-semibold tracking-tight">液态玻璃按钮</h1>
        <p className="text-muted-foreground">组件独立预览，可用鼠标、触屏或键盘操作。</p>
      </header>
      <DemoOne />
      <section className="space-y-4" aria-labelledby="button-states">
        <h2 id="button-states" className="text-lg font-semibold">尺寸与状态</h2>
        <div className="flex flex-wrap items-center gap-4">
          <LiquidButton size="sm">小号</LiquidButton>
          <LiquidButton size="lg">大号</LiquidButton>
          <LiquidButton disabled>禁用</LiquidButton>
          <LiquidButton asChild size="xl"><a href="#metal-buttons">查看金属按钮</a></LiquidButton>
          <Button variant="outline" onClick={() => window.scrollTo({ top: 0 })}>返回顶部</Button>
        </div>
      </section>
      <section id="metal-buttons" className="space-y-4" aria-labelledby="metal-title">
        <h2 id="metal-title" className="text-lg font-semibold">金属按钮</h2>
        <div className="flex flex-wrap items-center gap-4">
          {(["default", "primary", "success", "error", "gold", "bronze"] as const).map((variant) => (
            <MetalButton key={variant} variant={variant} onClick={() => setMetalClicks((count) => count + 1)}>{variant}</MetalButton>
          ))}
          <MetalButton disabled>禁用</MetalButton>
        </div>
        <p role="status" className="text-sm text-muted-foreground">金属按钮已点击 {metalClicks} 次</p>
      </section>
    </main>
  );
}
