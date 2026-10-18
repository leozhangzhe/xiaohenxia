# React authentication component demos

The default route now shows the supplied glass sign-up component. The existing
HextaUI sign-in demo remains available at `/sign-in`. These are standalone React
demos; the parent application's CherryPy/Mako authentication is unchanged.

## Glass sign-up component

- Component: `components/ui/sign-up.tsx` (`AuthComponent`, plus `TextLoop`).
- Supplied customization example: `demo.tsx` (`CustomAuthDemo`, also exported as `Demo`).
- Shared styles: `styles/globals.css`, including shadcn theme and chart colors.
- Required runtime packages: `lucide-react`, `framer-motion`, `canvas-confetti`,
  `class-variance-authority`; TypeScript declarations: `@types/canvas-confetti`.
  All are included in `package.json` and `package-lock.json`; use `npm ci`.

```tsx
import { AuthComponent } from "@/components/ui/sign-up";

export default function CustomAuthDemo() {
  return <AuthComponent brandName="MyWebApp" />;
}
```

The email → password → confirmation flow validates each step, accepts Enter,
supports password visibility and back navigation, and presents loading,
mismatched-password, and success states. The supplied SVG gradients, glass
controls, blur transitions, text loop, and confetti are retained. Input names,
autofill hints, a native modal focus trap, focus restoration, timer cleanup,
mobile wrapping, reduced-motion handling, and one-click button behavior were
added during integration. Confetti uses the main thread so React StrictMode can
attach the same canvas again without transferring it to a worker twice.

This component simulates completion after 4.5 seconds and **does not create an
account**, transmit credentials, or persist them. The success dialog says so.
Google/GitHub display an explanatory dialog until an application provides
`onSocialSignIn(provider)`. Real account creation requires replacing the demo
submission with an authenticated backend flow. The six-character password
minimum and welcome copy are supplied demo behavior, not the parent app's policy.

The package already supports TypeScript, Tailwind v4, `@/` imports, `cn()`, and
shadcn's `components/ui` convention; no CLI reinitialization is needed. The setup
instructions below remain available for projects that do not have this structure.

Verification: strict TypeScript and the production build passed; the UI detector
returned no findings. Browser checks covered invalid email, short password,
password visibility, mismatched passwords, retry, loading and successful demo
completion, social-provider feedback, and focus restoration after closing a
dialog. Initial layouts at 1440 × 900 and 390 × 844 fit without horizontal
overflow; an independent review of those captures returned `ship`. The original
`/sign-in` route was also checked. The browser console showed no warnings or
errors during the sign-up flow. Evidence is in `.impeccable/review/sign-up/`.

## Original HextaUI sign-in demo

The parent application uses CherryPy/Mako templates (`../spiderfoot/templates`)
and plain CSS (`../spiderfoot/static/css`). It did not have React, TypeScript,
Tailwind CSS, shadcn aliases, or a React components directory. This isolated Vite
package adds those capabilities without replacing the application's existing
authentication pages. The requested dark HextaUI appearance and remote image URLs
are retained. The component also supports Enter to submit, accessible input names,
password autofill, announced errors, and small-screen padding.

## Run this demo

Use Node.js 22.12+ (Node 24 is supported). From this directory:

```powershell
npm ci
npm run dev
```

Open the local URL printed by Vite (normally http://127.0.0.1:5173) for sign-up,
or append `/sign-in` for the original demo.
`npm run build` checks TypeScript and writes a production bundle to `dist/`.
`npm run preview` serves that bundle locally.

## Paths and imports

| Purpose | Path relative to this package |
| --- | --- |
| Reusable UI components | `components/ui/` |
| Supplied component | `components/ui/modern-stunning-sign-in.tsx` |
| Supplied sign-up component | `components/ui/sign-up.tsx` |
| Demo | `demo.tsx` |
| Application entry | `main.tsx` |
| Global styles and shadcn theme tokens | `styles/globals.css` |
| Class merging helper | `lib/utils.ts` |
| shadcn CLI settings | `components.json` |

`@/` resolves to this package's root in both `tsconfig.json` and
`vite.config.ts`, so the requested import works unchanged:

```tsx
import { SignIn1 } from "@/components/ui/modern-stunning-sign-in";

export default function Demo() {
  return <SignIn1 />;
}
```

Create and keep `components/ui` as the shared home for reusable UI primitives.
The legacy application has no equivalent directory. This convention makes
copied components discoverable and ensures the shadcn CLI's `aliases.ui` and
imports refer to the same location. It is a configurable convention, not a React
requirement. Here `/components/ui` means inside this frontend package.

## Setup instructions for another project

For a fresh project, the [official shadcn Vite guide](https://ui.shadcn.com/docs/installation/vite)
supports CLI scaffolding. Run this in a new empty project directory and follow
the prompts:

```powershell
npx shadcn@latest init -t vite
```

Alternatively, start with the React + TypeScript Vite template:

```powershell
npm create vite@latest sign-in-app -- --template react-ts
cd sign-in-app
npm install
npm install -D typescript @types/react @types/react-dom @types/node
npm install -D tailwindcss @tailwindcss/vite
```

Configure the Tailwind Vite plugin alongside `react()` in `vite.config.ts` and
add `@import "tailwindcss";` to the global stylesheet imported by the entry
module. Tailwind v4 uses this CSS-first setup; no `tailwind.config.js` or v3
`@tailwind` directives are necessary. See the
[official Tailwind Vite instructions](https://tailwindcss.com/docs/installation/using-vite).

Configure `@/*` in TypeScript and `@` in Vite before initializing shadcn.
Vite's standard React template uses `src/`, so its aliases normally point to
`./src/*` and `./src`. In this package both point to the package root instead.
Then, in a project that has not already been initialized:

```powershell
npx shadcn@latest init
```

Set `aliases.ui` to `@/components/ui` and `tailwind.css` to the global stylesheet
in [components.json](https://ui.shadcn.com/docs/components-json). For Tailwind v4,
leave `tailwind.config` empty. This package already includes that configuration,
theme tokens, `cn()`, and dependencies, so reinitialization is unnecessary. Add
other shadcn components from this directory when needed, for example:

```powershell
npx shadcn@latest add button
```

The supplied component uses React and Tailwind directly, so it needs no shadcn
primitive or third-party authentication package.

## HextaUI demo boundaries

Email/password validation is local and valid inputs display the supplied demo
alert; no credentials are sent or stored. Google sign-in has no OAuth handler,
and the sign-up link retains the supplied `#` placeholder. Those require real
authentication integration before production use. The developer-count copy is
part of the supplied HextaUI demo, not a claim about the parent application.

Images are fetched from the supplied `cdn.21st.dev` URLs and require network
access. The existing application avoids external CDNs; this demo is kept
separate from its authenticated routes and startup scripts for that reason too.

## Original HextaUI verification

- `npm run build` passed strict TypeScript checking and the Vite production build.
- Browser checks confirmed missing-field and invalid-email errors, and Enter
  submission with valid demo inputs displayed the supplied success alert.
- Desktop (1440 × 900), mobile (390 × 844), and the initial 345px browser width
  were visually inspected. Mobile and desktop had no horizontal overflow.
- All six supplied remote images loaded during verification.
- The UI detector reported no findings.
