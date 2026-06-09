import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Globe, MapPin, Play, Sparkles, BookOpen, CheckCircle2, AlertCircle } from 'lucide-react';

export default function Home() {
  const navigate = useNavigate();
  const [selectedMode, setSelectedMode] = useState<'india' | 'world' | null>(null);

  const hasApiKey = !!(import.meta.env.VITE_GOOGLE_MAPS_API_KEY);

  const handleStartGame = () => {
    if (selectedMode) {
      navigate(`/game?mode=${selectedMode}`);
    }
  };

  return (
    <div className="min-h-screen bg-bgDark-950 flex flex-col items-center justify-between p-6 relative overflow-hidden select-none">
      
      {/* Background Decorative Grid and Glowing Orbs */}
      <div className="absolute inset-0 bg-grid-pattern opacity-10 pointer-events-none" />
      <div className="absolute inset-0 bg-radial-glow opacity-40 pointer-events-none" />
      
      <div className="absolute top-[-20%] left-[-20%] w-[60%] h-[60%] bg-brand-500/10 rounded-full blur-[180px] pointer-events-none" />
      <div className="absolute bottom-[-20%] right-[-20%] w-[60%] h-[60%] bg-purple-500/5 rounded-full blur-[180px] pointer-events-none" />

      {/* Header / Logo */}
      <div className="w-full max-w-5xl flex justify-between items-center z-10 py-5 border-b border-white/10">
        <div className="flex items-center gap-3 cursor-pointer">
          <img
              src="/logo.png"
              alt="IndiaGuessr"
              className="w-10 h-10 rounded-xl object-cover shadow-glow"
          />
          <span className="text-xl font-extrabold tracking-tight text-white">
            India<span className="text-brand-500 font-bold">Guessr</span>
          </span>
        </div>
        <div className="text-[10px] text-slate-500 font-bold tracking-widest bg-white/5 border border-white/5 px-3 py-1 rounded-full uppercase">
          Production Pass v1.1
        </div>
      </div>

      {/* Main Hero & Config Panel */}
      <div className="w-full max-w-4xl flex flex-col items-center text-center z-10 my-auto py-10 animate-scale-up">
        
        {/* Title Badge */}
        <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-brand-500/10 border border-brand-500/20 text-xs font-bold text-brand-400 mb-6 drop-shadow-glow">
          <Sparkles className="w-3.5 h-3.5" />
          <span className="tracking-wider uppercase text-[10px]">🌍 TEST YOUR GEOGRAPHY INSTINCTS</span>
        </div>

        {/* Hero Headlines */}
        <h1 className="text-5xl md:text-7xl font-black tracking-tight text-white mb-6 leading-none">
          Where In The World
          Are You? <br />
          <span className="bg-gradient-to-r from-brand-400 via-brand-500 to-indigo-500 bg-clip-text text-transparent drop-shadow-glow">geographic unknown.</span>
        </h1>
        
        <p className="text-slate-400 text-sm md:text-base max-w-lg mb-12 font-light leading-relaxed">
          Road signs. Architecture. Language.
          Every clue matters.
          How close can you get?
        </p>

        {/* Mode Selector */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 w-full max-w-3xl mb-12">
          
          {/* India Mode Card */}
          <div 
            onClick={() => setSelectedMode('india')}
            className={`glass-panel group relative rounded-2xl p-7 text-left cursor-pointer transition-all duration-300 hover:-translate-y-1 hover:border-brand-500/40 hover:bg-bgDark-900/60 ${
              selectedMode === 'india' 
                ? 'border-brand-500 bg-brand-500/5 shadow-glow ring-1 ring-brand-500/20' 
                : 'border-white/10 bg-bgDark-950/40'
            }`}
          >
            {selectedMode === 'india' && (
              <span className="absolute top-6 right-6 text-brand-500">
                <CheckCircle2 className="w-6 h-6 fill-brand-500/10 animate-scale-up" />
              </span>
            )}
            <div className={`w-12 h-12 rounded-xl flex items-center justify-center mb-5 transition-all duration-300 group-hover:scale-105 ${
              selectedMode === 'india' ? 'bg-brand-500 text-white shadow-glow' : 'bg-white/5 text-slate-400 group-hover:bg-white/10'
            }`}>
              <MapPin className="w-5 h-5" />
            </div>
            <h3 className="text-lg font-black text-slate-100 mb-2">India Mode</h3>
            <p className="text-slate-400 text-xs font-light leading-relaxed">
              Explore rural villages, historic landmarks, coastal highways, and crowded metropolitan centers of India. Features optimized coverage with balanced spatial quality.
            </p>
          </div>

          {/* World Mode Card */}
          <div 
            onClick={() => setSelectedMode('world')}
            className={`glass-panel group relative rounded-2xl p-7 text-left cursor-pointer transition-all duration-300 hover:-translate-y-1 hover:border-emerald-500/40 hover:bg-bgDark-900/60 ${
              selectedMode === 'world' 
                ? 'border-emerald-500 bg-emerald-500/5 shadow-[0_0_20px_rgba(16,185,129,0.15)] ring-1 ring-emerald-500/20' 
                : 'border-white/10 bg-bgDark-950/40'
            }`}
          >
            {selectedMode === 'world' && (
              <span className="absolute top-6 right-6 text-emerald-500">
                <CheckCircle2 className="w-6 h-6 fill-emerald-500/10 animate-scale-up" />
              </span>
            )}
            <div className={`w-12 h-12 rounded-xl flex items-center justify-center mb-5 transition-all duration-300 group-hover:scale-105 ${
              selectedMode === 'world' ? 'bg-emerald-500 text-white shadow-[0_0_15px_rgba(16,185,129,0.4)]' : 'bg-white/5 text-slate-400 group-hover:bg-white/10'
            }`}>
              <Globe className="w-5 h-5" />
            </div>
            <h3 className="text-lg font-black text-slate-100 mb-2">World Mode</h3>
            <p className="text-slate-400 text-xs font-light leading-relaxed">
              Travel across various continents. Test your skills on worldwide street layouts, unique traffic signs, global vegetation, and landmarks on a planetary scale.
            </p>
          </div>

        </div>

        {/* Action Button */}
        <button
          onClick={handleStartGame}
          disabled={!selectedMode}
          className={`flex items-center gap-2 px-10 py-4.5 rounded-xl font-extrabold text-xs tracking-wider transition-all duration-300 transform border ${
            selectedMode 
              ? 'bg-brand-500 hover:bg-brand-600 text-white shadow-glow cursor-pointer hover:scale-105 border-brand-400/20 active:scale-95' 
              : 'bg-bgDark-900 text-slate-500 cursor-not-allowed border-white/5'
          }`}
        >
          <Play className="w-4 h-4 fill-current animate-pulse" />
          <span>START GAME SESSION</span>
        </button>

      </div>

      {/* Rules & API Info Section */}
      <div className="w-full max-w-5xl grid grid-cols-1 md:grid-cols-3 gap-6 z-10 border-t border-white/10 pt-8 mt-auto pb-4">
        
        {/* Rules Card 1 */}
        <div className="flex gap-4 text-left p-4 rounded-xl hover:bg-white/5 transition-all">
          <div className="p-2.5 rounded-xl bg-white/5 border border-white/5 h-fit text-slate-400 mt-1">
            <BookOpen className="w-4 h-4" />
          </div>
          <div>
            <h4 className="text-xs font-bold text-slate-200 tracking-wider uppercase mb-1">Game Structure</h4>
            <p className="text-[11px] text-slate-500 font-light leading-relaxed">
              Play 5 rounds in succession. Scan your panoramic surroundings, determine geographical markers, and guess coordinates.
            </p>
          </div>
        </div>

        {/* Rules Card 2 */}
        <div className="flex gap-4 text-left p-4 rounded-xl hover:bg-white/5 transition-all">
          <div className="p-2.5 rounded-xl bg-white/5 border border-white/5 h-fit text-slate-400 mt-1">
            <MapPin className="w-4 h-4" />
          </div>
          <div>
            <h4 className="text-xs font-bold text-slate-200 tracking-wider uppercase mb-1">Exponential Scoring</h4>
            <p className="text-[11px] text-slate-500 font-light leading-relaxed">
              Earn up to 5,000 points per round. Scoring uses a distance-based exponential decay function (higher precision is rewarded).
            </p>
          </div>
        </div>

        {/* API Warning Panel */}
        <div className="flex gap-4 text-left p-4 rounded-xl hover:bg-white/5 transition-all">
          <div className={`p-2.5 rounded-xl border h-fit mt-1 ${hasApiKey ? 'bg-emerald-500/10 border-emerald-500/25 text-emerald-400 shadow-[0_0_15px_rgba(16,185,129,0.05)]' : 'bg-amber-500/10 border-amber-500/25 text-amber-400 shadow-[0_0_15px_rgba(245,158,11,0.05)]'}`}>
            {hasApiKey ? <CheckCircle2 className="w-4 h-4" /> : <AlertCircle className="w-4 h-4" />}
          </div>
          <div>
            <h4 className="text-xs font-bold text-slate-200 tracking-wider uppercase mb-1">Coverage Status</h4>
            <p className="text-[11px] text-slate-500 font-light leading-relaxed">
              {hasApiKey 
                ? "Google Maps API Key is active. Authenticated live official coverage verification is fully operational." 
                : "No Google Maps API Key found. Operating in Mock Mode using beautiful curated panoramic landscape presets."}
            </p>
          </div>
        </div>

      </div>

    </div>
  );
}

