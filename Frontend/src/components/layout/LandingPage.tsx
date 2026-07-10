import { useChronosStore } from '../../store/useChronosStore';
import { Network, MessageSquare, Users, Scale, Database, Sparkles } from 'lucide-react';

const FEATURES = [
  { icon: Network, title: 'Future Simulation Engine', desc: 'Simulate multiple future outcomes across careers, finances, and life.' },
  { icon: MessageSquare, title: 'Future Self Conversations', desc: "Talk with your future self and learn from decisions you haven't made yet." },
  { icon: Users, title: 'Multi-Agent Council', desc: 'Watch a council of AI experts debate your hardest decisions.' },
  { icon: Scale, title: 'Regret Analysis', desc: 'Understand the tradeoffs and regret of every path before committing.' },
  { icon: Database, title: 'Decision Memory', desc: 'Track past decisions and their real outcomes over time.' },
  { icon: Sparkles, title: 'Opportunity Discovery', desc: 'Surface hidden opportunities your current path would never reveal.' },
];

export function LandingPage() {
  const setStep = useChronosStore((state) => state.setStep);
  // Duplicate features so the marquee loops seamlessly
  const LOOPED_FEATURES = [...FEATURES, ...FEATURES];

  return (
    <div className="flex flex-col min-h-screen bg-white text-gray-900">
      {/* Hero Section */}
      <div className="flex-1 flex flex-col justify-center px-10 md:px-20 max-w-7xl">
        <p className="text-xs tracking-[0.2em] text-gray-400 uppercase mb-6 font-medium">
          Decision Intelligence, Reconsidered
        </p>
        
        {/* Changed from font-bold to font-normal for elegant serif look */}
        <h1 className="text-6xl md:text-8xl lg:text-[9rem] font-serif font-normal tracking-tighter leading-[0.85] mb-8">
          Chronos<br/>Engine
        </h1>
        
        <p className="text-lg md:text-xl text-gray-500 max-w-2xl leading-relaxed mb-12">
          A single system of record for every decision your organization makes — modeled, simulated, and measured before it ships.
        </p>

        <button
          onClick={() => setStep(1)}
          className="w-fit border border-gray-900 px-8 py-4 text-xs uppercase tracking-widest font-semibold transition-all duration-300 hover:bg-gray-900 hover:text-white"
        >
          Launch Program
        </button>
      </div>

      {/* Interactive Carousel */}
      <div className="h-64 border-t border-gray-100 flex items-center overflow-hidden bg-gray-50/50 group">
        <div className="flex items-center gap-8 animate-marquee group-hover:[animation-play-state:paused] w-max px-4">
          {LOOPED_FEATURES.map((f, i) => (
            <div 
              key={i} 
              className="w-80 flex-shrink-0 p-6 bg-white border border-gray-100 shadow-sm transition-all duration-500 
                         group-hover:opacity-30 hover:!opacity-100 hover:scale-105 cursor-default"
            >
              <f.icon className="h-6 w-6 text-gray-900 mb-4" />
              <h3 className="font-serif font-semibold text-xl text-gray-900 mb-2">{f.title}</h3>
              <p className="text-sm text-gray-500 leading-relaxed">{f.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}