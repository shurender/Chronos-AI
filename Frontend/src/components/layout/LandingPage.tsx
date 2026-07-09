import {
  Play,
  ArrowRight,
  Network,
  MessageSquare,
  Users,
  Scale,
  Database,
  Sparkles,
  Hexagon,
  Cpu,
  Rocket,
  FlaskConical,
  Layers,
  User,
} from 'lucide-react';
import { useChronosStore } from '../../store/useChronosStore';

const FEATURES = [
  {
    icon: Network,
    title: 'Future Simulation Engine',
    desc: 'Simulate multiple future outcomes across careers, finances, and life.',
    color: 'text-cyan-300',
    bg: 'bg-cyan-400/10',
    border: 'border-cyan-400/20',
  },
  {
    icon: MessageSquare,
    title: 'Future Self Conversations',
    desc: "Talk with your future self and learn from decisions you haven't made yet.",
    color: 'text-sky-300',
    bg: 'bg-sky-400/10',
    border: 'border-sky-400/20',
  },
  {
    icon: Users,
    title: 'Multi-Agent Council',
    desc: 'Watch a council of AI experts debate your hardest decisions.',
    color: 'text-violet-300',
    bg: 'bg-violet-400/10',
    border: 'border-violet-400/20',
  },
  {
    icon: Scale,
    title: 'Regret Analysis',
    desc: 'Understand the tradeoffs and regret of every path before committing.',
    color: 'text-emerald-300',
    bg: 'bg-emerald-400/10',
    border: 'border-emerald-400/20',
  },
  {
    icon: Database,
    title: 'Decision Memory',
    desc: 'Track past decisions and their real outcomes over time.',
    color: 'text-blue-300',
    bg: 'bg-blue-400/10',
    border: 'border-blue-400/20',
  },
  {
    icon: Sparkles,
    title: 'Opportunity Discovery',
    desc: 'Surface hidden opportunities your current path would never reveal.',
    color: 'text-amber-300',
    bg: 'bg-amber-400/10',
    border: 'border-amber-400/20',
  },
];

const NODES = [
  {
    icon: Cpu,
    label: 'AI Engineer',
    sub: 'TIMELINE A',
    style: { top: '4%', left: '0%' },
    end: { x: 16, y: 18 },
    color: 'text-cyan-300',
    bg: 'bg-cyan-400/10',
    border: 'border-cyan-400/30',
  },
  {
    icon: Rocket,
    label: 'Startup Founder',
    sub: 'TIMELINE B',
    style: { top: '0%', right: '0%' },
    end: { x: 84, y: 14 },
    color: 'text-violet-300',
    bg: 'bg-violet-400/10',
    border: 'border-violet-400/30',
  },
  {
    icon: FlaskConical,
    label: 'Research Scientist',
    sub: 'TIMELINE C',
    style: { bottom: '12%', left: '4%' },
    end: { x: 18, y: 82 },
    color: 'text-emerald-300',
    bg: 'bg-emerald-400/10',
    border: 'border-emerald-400/30',
  },
  {
    icon: Layers,
    label: 'Product Executive',
    sub: 'TIMELINE D',
    style: { bottom: '0%', right: '2%' },
    end: { x: 86, y: 88 },
    color: 'text-amber-300',
    bg: 'bg-amber-400/10',
    border: 'border-amber-400/30',
  },
];

export function LandingPage() {
  const setStep = useChronosStore((state) => state.setStep);

  return (
    <div className="relative min-h-screen w-full overflow-x-hidden bg-[#080b14] text-white">
      {/* Signature motion + starfield styles */}
      <style>{`
        @keyframes chronos-flow { to { stroke-dashoffset: -24; } }
        .chronos-flow-line { stroke-dasharray: 3 7; animation: chronos-flow 2.2s linear infinite; }
        @keyframes chronos-pulse {
          0% { transform: scale(0.85); opacity: 0.55; }
          70% { transform: scale(1.6); opacity: 0; }
          100% { opacity: 0; }
        }
        .chronos-pulse-ring { animation: chronos-pulse 3s ease-out infinite; }
        @keyframes chronos-float {
          0%, 100% { transform: translateY(0px); }
          50% { transform: translateY(-8px); }
        }
        .chronos-float { animation: chronos-float 6s ease-in-out infinite; }
        @media (prefers-reduced-motion: reduce) {
          .chronos-flow-line, .chronos-pulse-ring, .chronos-float { animation: none; }
        }
      `}</style>

      {/* Starfield + ambient glow background */}
      <div className="pointer-events-none fixed inset-0 -z-10">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_1px_1px,rgba(255,255,255,0.13)_1px,transparent_0)] bg-[size:26px_26px] opacity-60" />
        <div className="absolute -top-40 left-1/4 h-[500px] w-[500px] rounded-full bg-[radial-gradient(circle,rgba(34,211,238,0.14),transparent_65%)] blur-2xl" />
        <div className="absolute top-1/3 right-0 h-[420px] w-[420px] rounded-full bg-[radial-gradient(circle,rgba(167,139,250,0.12),transparent_65%)] blur-2xl" />
      </div>

      {/* Navbar */}
      <nav className="sticky top-0 z-50 border-b border-white/5 bg-[#080b14]/70 backdrop-blur-md">
        <div className="mx-auto flex h-20 max-w-7xl items-center justify-between px-6 lg:px-10">
          <div className="flex items-center gap-2.5">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl border border-cyan-400/30 bg-cyan-400/10">
              <Hexagon className="h-5 w-5 text-cyan-400" strokeWidth={2.2} />
            </div>
            <span className="text-lg font-semibold tracking-tight">
              Chronos <span className="text-cyan-400">AI</span>
            </span>
          </div>

          <div className="hidden items-center gap-8 text-sm text-white/60 md:flex">
            <a href="#features" className="transition-colors hover:text-white">
              Features
            </a>
            <a href="#impact" className="transition-colors hover:text-white">
              Impact
            </a>
          </div>

          <button
            onClick={() => setStep(1)}
            className="rounded-full bg-cyan-400 px-5 py-2.5 text-sm font-semibold text-[#061018] shadow-[0_0_20px_rgba(34,211,238,0.4)] transition-transform hover:scale-105 hover:shadow-[0_0_30px_rgba(34,211,238,0.6)]"
          >
            Launch App
          </button>
        </div>
      </nav>

      {/* Hero */}
      <section className="relative mx-auto grid max-w-7xl grid-cols-1 items-center gap-16 px-6 pb-24 pt-20 lg:grid-cols-2 lg:px-10 lg:pt-28">
        <div>
          <div className="mb-8 inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-4 py-1.5 text-xs tracking-wide text-white/70">
            <span className="h-1.5 w-1.5 rounded-full bg-cyan-400 shadow-[0_0_8px_rgba(34,211,238,0.8)]" />
            Decision Intelligence Platform
          </div>

          <h1 className="mb-6 text-5xl font-bold leading-[1.05] tracking-tight sm:text-6xl">
            Before You Choose,
            <br />
            <span className="bg-gradient-to-r from-cyan-300 via-sky-300 to-violet-400 bg-clip-text text-transparent">
              See What Happens.
            </span>
          </h1>

          <p className="mb-10 max-w-md text-lg leading-relaxed text-white/60">
            Chronos AI simulates possible futures using AI-powered decision intelligence — so you can live the
            outcome before you commit to the choice.
          </p>

          <div className="flex flex-wrap items-center gap-4">
            <button
              onClick={() => setStep(1)}
              className="group inline-flex items-center gap-2 rounded-full bg-cyan-400 px-6 py-3.5 text-sm font-semibold text-[#061018] shadow-[0_0_20px_rgba(34,211,238,0.4)] transition-all hover:scale-105 hover:shadow-[0_0_30px_rgba(34,211,238,0.6)]"
            >
              Explore My Futures
              <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
            </button>
            <button className="inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/5 px-6 py-3.5 text-sm font-semibold text-white/80 backdrop-blur-sm transition-colors hover:bg-white/10">
              <Play className="h-3.5 w-3.5 fill-current" />
              Watch Simulation
            </button>
          </div>
        </div>

        {/* Node graph visual */}
        <div className="relative hidden h-[520px] lg:block">
          {/* concentric rings */}
          <div className="absolute left-1/2 top-1/2 h-[220px] w-[220px] -translate-x-1/2 -translate-y-1/2 rounded-full border border-white/[0.06]" />
          <div className="absolute left-1/2 top-1/2 h-[340px] w-[340px] -translate-x-1/2 -translate-y-1/2 rounded-full border border-white/[0.05]" />
          <div className="absolute left-1/2 top-1/2 h-[460px] w-[460px] -translate-x-1/2 -translate-y-1/2 rounded-full border border-white/[0.04]" />

          {/* pulse rings */}
          <div className="chronos-pulse-ring absolute left-1/2 top-1/2 h-16 w-16 -translate-x-1/2 -translate-y-1/2 rounded-full border border-cyan-400/50" />
          <div
            className="chronos-pulse-ring absolute left-1/2 top-1/2 h-16 w-16 -translate-x-1/2 -translate-y-1/2 rounded-full border border-cyan-400/50"
            style={{ animationDelay: '1.5s' }}
          />

          {/* connecting lines */}
          <svg className="absolute inset-0 h-full w-full" viewBox="0 0 100 100" preserveAspectRatio="none">
            <defs>
              <linearGradient id="chronosLine" x1="0" y1="0" x2="1" y2="1">
                <stop offset="0%" stopColor="rgba(34,211,238,0.9)" />
                <stop offset="100%" stopColor="rgba(34,211,238,0.05)" />
              </linearGradient>
            </defs>
            {NODES.map((n, i) => (
              <line
                key={i}
                x1="50"
                y1="50"
                x2={n.end.x}
                y2={n.end.y}
                stroke="url(#chronosLine)"
                strokeWidth="0.4"
                vectorEffect="non-scaling-stroke"
                className="chronos-flow-line"
              />
            ))}
          </svg>

          {/* center node */}
          <div className="absolute left-1/2 top-1/2 flex -translate-x-1/2 -translate-y-1/2 flex-col items-center gap-2">
            <div className="flex h-16 w-16 items-center justify-center rounded-full border border-cyan-400/40 bg-cyan-400/10 shadow-[0_0_30px_rgba(34,211,238,0.35)]">
              <User className="h-6 w-6 text-cyan-300" />
            </div>
            <span className="text-[10px] font-medium tracking-[0.2em] text-white/50">CURRENT YOU</span>
          </div>

          {/* satellite node cards */}
          {NODES.map((n, i) => (
            <div
              key={n.label}
              className="chronos-float absolute w-[148px] rounded-2xl border border-white/10 bg-white/[0.06] p-4 shadow-xl backdrop-blur-md"
              style={{ ...n.style, animationDelay: `${i * 0.6}s` }}
            >
              <div className={`mb-2.5 flex h-8 w-8 items-center justify-center rounded-full border ${n.bg} ${n.border}`}>
                <n.icon className={`h-4 w-4 ${n.color}`} />
              </div>
              <p className="text-sm font-semibold leading-tight">{n.label}</p>
              <p className={`mt-0.5 text-[10px] font-medium tracking-widest ${n.color}`}>{n.sub}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Stats bar */}
      <section className="mx-auto mb-28 max-w-6xl px-6 lg:px-10">
        <div className="grid grid-cols-1 gap-10 rounded-[2rem] border border-white/10 bg-gradient-to-b from-white/[0.06] to-white/[0.02] px-10 py-12 text-center shadow-[0_0_60px_rgba(0,0,0,0.35)] sm:grid-cols-3">
          <div className="sm:border-r sm:border-white/10">
            <p className="mb-2 bg-gradient-to-r from-cyan-300 to-sky-400 bg-clip-text text-4xl font-bold text-transparent sm:text-5xl">
              1.2M+
            </p>
            <p className="text-xs tracking-[0.2em] text-white/40">FUTURE SIMULATIONS</p>
          </div>
          <div className="sm:border-r sm:border-white/10">
            <p className="mb-2 bg-gradient-to-r from-sky-300 to-blue-400 bg-clip-text text-4xl font-bold text-transparent sm:text-5xl">
              8.7M+
            </p>
            <p className="text-xs tracking-[0.2em] text-white/40">DECISIONS ANALYZED</p>
          </div>
          <div>
            <p className="mb-2 bg-gradient-to-r from-blue-400 to-violet-400 bg-clip-text text-4xl font-bold text-transparent sm:text-5xl">
              $2.1B+
            </p>
            <p className="text-xs tracking-[0.2em] text-white/40">POTENTIAL REGRET PREVENTED</p>
          </div>
        </div>
      </section>

      {/* Features grid */}
      <section id="features" className="mx-auto max-w-6xl px-6 pb-32 text-center lg:px-10">
        <h2 className="mb-4 text-4xl font-bold tracking-tight sm:text-5xl">
          An operating system for your future
        </h2>
        <p className="mx-auto mb-16 max-w-xl text-white/50">
          Six engines working together to model, debate, and stress-test every decision that matters.
        </p>

        <div className="grid gap-6 text-left sm:grid-cols-2 lg:grid-cols-3">
          {FEATURES.map((f) => (
            <div
              key={f.title}
              className="group rounded-2xl border border-white/10 bg-white/[0.03] p-7 transition-colors hover:border-white/20 hover:bg-white/[0.06]"
            >
              <div className={`mb-5 flex h-11 w-11 items-center justify-center rounded-full border ${f.bg} ${f.border}`}>
                <f.icon className={`h-5 w-5 ${f.color}`} />
              </div>
              <h3 className="mb-2 text-lg font-semibold">{f.title}</h3>
              <p className="text-sm leading-relaxed text-white/50">{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Final CTA */}
      <section id="impact" className="mx-auto max-w-4xl px-6 pb-24 text-center lg:px-10">
        <h2 className="mb-4 text-4xl font-bold tracking-tight sm:text-5xl">Your futures are waiting.</h2>
        <p className="mx-auto mb-10 max-w-lg text-white/50">
          Step into the simulation and see where every path leads — before you take the first step.
        </p>
        <button
          onClick={() => setStep(1)}
          className="group inline-flex items-center gap-2 rounded-full bg-cyan-400 px-8 py-4 text-sm font-semibold text-[#061018] shadow-[0_0_20px_rgba(34,211,238,0.4)] transition-all hover:scale-105 hover:shadow-[0_0_30px_rgba(34,211,238,0.6)]"
        >
          Explore My Futures
          <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
        </button>
      </section>

      {/* Footer */}
      <footer className="border-t border-white/5 py-10">
        <div className="mx-auto flex max-w-6xl items-center justify-center gap-2 px-6 text-sm text-white/40 lg:px-10">
          <Hexagon className="h-4 w-4 text-cyan-400/70" />
          Chronos AI © 2026 — Decision Intelligence, reimagined.
        </div>
      </footer>
    </div>
  );
}
