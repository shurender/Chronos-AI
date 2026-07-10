import { useState, useEffect, useRef } from 'react';
import { useChronosStore } from '../../store/useChronosStore';
import { Network, MessageSquare, Users, Scale, Database, Sparkles, type LucideIcon } from 'lucide-react';

interface Feature {
  icon: LucideIcon;
  title: string;
  desc: string;
}

const FEATURES: Feature[] = [
  { icon: Network, title: 'Future Simulation Engine', desc: 'Simulate multiple future outcomes across careers, finances, and life.' },
  { icon: MessageSquare, title: 'Future Self Conversations', desc: "Talk with your future self and learn from decisions you haven't made yet." },
  { icon: Users, title: 'Multi-Agent Council', desc: 'Watch a council of AI experts debate your hardest decisions.' },
  { icon: Scale, title: 'Regret Analysis', desc: 'Understand the tradeoffs and regret of every path before committing.' },
  { icon: Database, title: 'Decision Memory', desc: 'Track past decisions and their real outcomes over time.' },
  { icon: Sparkles, title: 'Opportunity Discovery', desc: 'Surface hidden opportunities your current path would never reveal.' },
];

// Reusable Scroll Animation Component
function FadeInBlock({ children, delay = 0 }: { children: React.ReactNode; delay?: number }) {
  const [isVisible, setIsVisible] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const observer = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting) {
        setIsVisible(true);
        observer.disconnect();
      }
    }, { threshold: 0.2 });

    if (ref.current) observer.observe(ref.current);
    return () => observer.disconnect();
  }, []);

  return (
    <div 
      ref={ref} 
      className={`transition-all duration-1000 ease-out ${isVisible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-12'}`} 
      style={{ transitionDelay: `${delay}ms` }}
    >
      {children}
    </div>
  );
}

export function LandingPage({ onLaunch }: { onLaunch?: () => void } = {}) {
  const triggerAppLaunch = useChronosStore((state) => state.triggerAppLaunch);
  const setActiveSection = useChronosStore((state) => state.setActiveSection);
  const [hoveredFeature, setHoveredFeature] = useState<Feature | null>(null);

  // Prefer the curtain-aware transition passed down from App; fall back to
  // the raw store action so this component still works standalone.
  const launch = onLaunch ?? triggerAppLaunch;

  // Duplicate features so the marquee loops seamlessly
  const LOOPED_FEATURES = [...FEATURES, ...FEATURES];

  // Scroll Spy for Sidebar
  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach(entry => {
          if (entry.isIntersecting && entry.target.id) {
            setActiveSection(entry.target.id);
          }
        });
      },
      { threshold: 0.2 }
    );

    ['chronos-top', 'impact-section', 'faq-section'].forEach(id => {
      const el = document.getElementById(id);
      if (el) observer.observe(el);
    });

    return () => observer.disconnect();
  }, [setActiveSection]);

  return (
    <div className="flex flex-col bg-white text-gray-900 w-full">
      
      {/* ── Section 1: Hero & Marquee ── */}
      <section id="chronos-top" className="min-h-screen flex flex-col justify-between pt-20">
        <div className="flex-1 flex flex-col justify-center px-10 md:px-20 max-w-7xl">
          <p className="text-xs tracking-[0.2em] text-gray-400 uppercase mb-6 font-medium">
            Decision Intelligence, Reconsidered
          </p>
          
          <div className="relative h-48 md:h-[14rem] lg:h-[18rem] mb-4">
            
            {/* Default State: Chronos Engine */}
            <div 
              className={`absolute inset-0 transition-all duration-700 ease-out 
                ${!hoveredFeature ? 'opacity-100 translate-y-0 pointer-events-auto' : 'opacity-0 -translate-y-4 pointer-events-none'}`}
            >
              <h1 className="text-6xl md:text-8xl lg:text-[9rem] font-serif font-normal tracking-tighter leading-[0.85] mb-8 text-gray-900">
                Chronos<br/>Engine
              </h1>
              <p className="text-lg md:text-xl text-gray-500 max-w-2xl leading-relaxed">
                A single system of record for every decision your organization makes — modeled, simulated, and measured before it ships.
              </p>
            </div>

            {/* Dynamic Hover States */}
            {FEATURES.map((f) => (
              <div 
                key={f.title}
                className={`absolute inset-0 transition-all duration-700 ease-out
                  ${hoveredFeature?.title === f.title ? 'opacity-100 translate-y-0 pointer-events-auto' : 'opacity-0 translate-y-4 pointer-events-none'}`}
              >
                <h1 className="text-5xl md:text-7xl lg:text-[7rem] font-serif font-normal tracking-tighter leading-[0.9] mb-6 text-gray-900">
                  {f.title}
                </h1>
                <p className="text-lg md:text-2xl text-gray-500 max-w-2xl leading-relaxed">
                  {f.desc}
                </p>
              </div>
            ))}
          </div>

          <button
            onClick={() => launch()}
            className="w-fit mt-12 border border-gray-900 px-8 py-4 text-xs uppercase tracking-widest font-semibold transition-all duration-300 hover:bg-gray-900 hover:text-white"
          >
            Launch Program
          </button>
        </div>

        {/* Interactive Marquee Carousel */}
        <div className="h-64 border-t border-gray-100 flex items-center overflow-hidden bg-gray-50/50">
          {/* Use native inline styles to reliably pause animation on hover */}
          <div
            className="flex w-max animate-marquee"
            style={{ animationPlayState: hoveredFeature ? 'paused' : 'running' }}
          >
            {/* Two structurally identical sets, each with its own matching
                gap/padding — required for the -50% translate loop to be
                seamless. The OUTER track itself must have zero gap/padding
                of its own, or the halves stop being exactly equal width and
                the loop jumps at the seam every cycle. */}
            {[0, 1].map((setIndex) => (
              <div key={`set-${setIndex}`} className="flex gap-8 pl-4 pr-8" aria-hidden={setIndex === 1}>
                {FEATURES.map((f, i) => (
                  <div
                    key={`set${setIndex}-${i}`}
                    onMouseEnter={() => setHoveredFeature(f)}
                    onMouseLeave={() => setHoveredFeature(null)}
                    className="w-80 flex-shrink-0 p-6 bg-white border border-gray-100 shadow-sm transition-all duration-500 
                              hover:!opacity-100 hover:scale-105 cursor-default"
                    style={{ opacity: hoveredFeature && hoveredFeature.title !== f.title ? 0.3 : 1 }}
                  >
                    <f.icon className="h-6 w-6 text-gray-900 mb-4" />
                    <h3 className="font-serif font-semibold text-xl text-gray-900 mb-2">{f.title}</h3>
                    <p className="text-sm text-gray-500 leading-relaxed">{f.desc}</p>
                  </div>
                ))}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Section 2: Practical Use Cases ── */}
      <section id="impact-section" className="min-h-[80vh] flex flex-col justify-center px-10 md:px-20 max-w-7xl py-32 border-t border-gray-100">
        <FadeInBlock delay={0}>
          <p className="text-xs tracking-[0.2em] text-gray-400 uppercase mb-6 font-medium">
            Practical Applications
          </p>
        </FadeInBlock>
        <FadeInBlock delay={100}>
          <h1 className="text-5xl md:text-7xl font-serif font-normal tracking-tighter leading-tight mb-16">
            De-risk every critical maneuver.
          </h1>
        </FadeInBlock>
        <div className="grid md:grid-cols-3 gap-12 md:gap-8">
          <FadeInBlock delay={200}>
            <div className="border-t border-gray-200 pt-6">
              <h3 className="font-serif text-2xl mb-3">Startup Pivots</h3>
              <p className="text-gray-500 text-sm leading-relaxed">Model cash runway, technical debt, and market adoption rates before committing to a costly B2B or Enterprise pivot.</p>
            </div>
          </FadeInBlock>
          <FadeInBlock delay={300}>
            <div className="border-t border-gray-200 pt-6">
              <h3 className="font-serif text-2xl mb-3">Executive Hiring</h3>
              <p className="text-gray-500 text-sm leading-relaxed">Simulate team dynamics and cultural integration using historical communication graphs and behavioral precedents.</p>
            </div>
          </FadeInBlock>
          <FadeInBlock delay={400}>
            <div className="border-t border-gray-200 pt-6">
              <h3 className="font-serif text-2xl mb-3">M&A Strategy</h3>
              <p className="text-gray-500 text-sm leading-relaxed">Forecast integration timelines and highlight deep structural contradictions in product architecture prior to acquisition.</p>
            </div>
          </FadeInBlock>
        </div>
      </section>

      {/* ── Section 3: Video Section ── */}
      <section className="py-32 bg-gray-50 border-y border-gray-100 flex flex-col items-center justify-center px-10">
        <FadeInBlock delay={0}>
          <div className="text-center mb-12">
            <h2 className="text-sm tracking-[0.2em] uppercase text-gray-500 font-semibold mb-3">How it works</h2>
            <p className="text-4xl md:text-5xl font-serif font-normal">Seamless ingestion to simulation.</p>
          </div>
        </FadeInBlock>
        
        <FadeInBlock delay={150}>
          <div className="w-full max-w-5xl aspect-video bg-gray-200 rounded-xl border border-gray-300 shadow-xl flex items-center justify-center relative overflow-hidden">
            <div className="text-center">
              <span className="bg-white px-4 py-2 rounded-full text-xs font-bold uppercase tracking-widest shadow-sm text-gray-600">
                Video Canvas Placeholder
              </span>
              <p className="mt-4 text-sm text-gray-500 max-w-sm mx-auto">
                Implement Framer Motion <code>useScroll</code> here to scrub a canvas image sequence based on viewport scroll progress.
              </p>
            </div>
          </div>
        </FadeInBlock>
      </section>

      {/* ── Section 4: FAQ ── */}
      <section id="faq-section" className="px-10 md:px-20 max-w-5xl py-32 mx-auto w-full">
        <FadeInBlock delay={0}>
          <h2 className="text-4xl md:text-5xl font-serif font-normal tracking-tighter mb-16">
            Frequently Asked Questions
          </h2>
        </FadeInBlock>
        
        <div className="space-y-12">
          <FadeInBlock delay={100}>
            <div className="border-b border-gray-200 pb-10">
              <h3 className="text-xl font-semibold mb-4 text-gray-900">How does Chronos differ from predictive AI models?</h3>
              <p className="text-gray-500 leading-relaxed">
                Chronos is a deterministic, heuristic simulation engine, not a generative black box. It maps your historical decisions into a factual graph and runs conditional probability branches based on verifiable constraints. It does not "hallucinate" the future; it stress-tests your assumptions against your own history.
              </p>
            </div>
          </FadeInBlock>
          <FadeInBlock delay={200}>
            <div className="border-b border-gray-200 pb-10">
              <h3 className="text-xl font-semibold mb-4 text-gray-900">Is my company's data safe?</h3>
              <p className="text-gray-500 leading-relaxed">
                All memory graph data is vectorized and stored locally via ChromaDB. The multi-agent simulation occurs entirely within your secure VPC. We do not use your Slack messages or GitHub commits to train external base models.
              </p>
            </div>
          </FadeInBlock>
          <FadeInBlock delay={300}>
            <div className="border-b border-gray-200 pb-10">
              <h3 className="text-xl font-semibold mb-4 text-gray-900">What integrations are currently supported?</h3>
              <p className="text-gray-500 leading-relaxed">
                The MVP currently ingests raw markdown, PDF reports, and JSON exports from Slack, GitHub, and Notion. Native OAuth integrations for real-time webhooks are slated for v2.0.
              </p>
            </div>
          </FadeInBlock>
        </div>
      </section>

      {/* ── Section 5: Final CTA ── */}
      <section className="py-32 bg-gray-900 text-center px-10">
        <FadeInBlock delay={0}>
          <h2 className="text-4xl md:text-6xl font-serif font-normal tracking-tighter mb-8 text-white">
            Ready to see your future?
          </h2>
        </FadeInBlock>
        <FadeInBlock delay={150}>
          <button
            onClick={() => launch()}
            className="mt-6 border border-white/20 bg-white px-10 py-5 text-sm uppercase tracking-widest font-bold text-gray-900 transition-all duration-300 hover:bg-gray-200 hover:scale-105"
          >
            Launch Program
          </button>
        </FadeInBlock>
      </section>

    </div>
  );
}