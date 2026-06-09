import { useEffect, useState } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { api } from '../services/api';
import type { GameResults } from '../types';
import GoogleResultsMap from '../components/GoogleResultsMap';
import { 
  Trophy, 
  MapPin, 
  RotateCcw, 
  Home, 
  Globe, 
  Award, 
  Loader2
} from 'lucide-react';

export default function Results() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const gameId = searchParams.get('game_id') || '';

  const [results, setResults] = useState<GameResults | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchResults() {
      if (!gameId) {
        setError('No game ID specified.');
        setLoading(false);
        return;
      }
      try {
        setLoading(true);
        const data = await api.getResults(gameId);
        setResults(data);
        setError(null);
      } catch (err: any) {
        console.error(err);
        setError(err.message || 'Failed to fetch game results.');
      } finally {
        setLoading(false);
      }
    }
    fetchResults();
  }, [gameId]);

  if (loading) {
    return (
      <div className="min-h-screen bg-bgDark-950 flex flex-col items-center justify-center text-slate-100 relative overflow-hidden">
        <div className="absolute inset-0 bg-radial-glow opacity-30 pointer-events-none" />
        <div className="absolute inset-0 bg-grid-pattern opacity-10 pointer-events-none" />
        
        <div className="flex flex-col items-center gap-4 px-8 py-10 rounded-2xl glass-panel-heavy border border-white/10 shadow-glow max-w-sm text-center z-10 animate-scale-up">
          <Loader2 className="w-12 h-12 text-brand-500 animate-spin drop-shadow-glow" />
          <h3 className="text-sm font-extrabold tracking-widest text-slate-300 uppercase mt-2">Compiling Results</h3>
          <p className="text-xs text-slate-400 font-light">Analyzing distance vectors and scoring arrays...</p>
        </div>
      </div>
    );
  }

  if (error || !results) {
    return (
      <div className="min-h-screen bg-bgDark-950 flex flex-col items-center justify-center text-slate-100 p-6 text-center relative overflow-hidden">
        <div className="absolute inset-0 bg-radial-glow opacity-25 pointer-events-none" />
        <div className="flex flex-col items-center max-w-md px-8 py-10 rounded-2xl glass-panel border border-red-500/25 shadow-glow z-10 animate-scale-up">
          <div className="w-16 h-16 rounded-full bg-red-500/10 border border-red-500/20 flex items-center justify-center text-red-400 mb-6">
            <Trophy className="w-8 h-8" />
          </div>
          <h2 className="text-xl font-black mb-2 text-white">Results Registry Fault</h2>
          <p className="text-slate-400 text-sm mb-6 font-light">{error || 'Could not fetch game results.'}</p>
          <button
            onClick={() => navigate('/')}
            className="flex items-center gap-2 px-6 py-3.5 rounded-xl bg-brand-500 hover:bg-brand-600 font-bold text-sm tracking-wide text-white transition-all shadow-glow border border-brand-400/20"
          >
            <Home className="w-4 h-4" />
            <span>RETURN HOME</span>
          </button>
        </div>
      </div>
    );
  }

  const scorePercent = (results.total_score / 25000) * 100;
  let grade = 'Explorer';
  let gradeDesc = 'Not bad! Keep exploring to master the landscapes.';
  let gradeGlow = 'from-indigo-500 to-purple-500';
  
  if (scorePercent >= 95) {
    grade = 'Grandmaster Guessr';
    gradeDesc = 'Unbelievable precision! You know the Earth like the back of your hand.';
    gradeGlow = 'from-amber-400 to-orange-500';
  } else if (scorePercent >= 80) {
    grade = 'Master Navigator';
    gradeDesc = 'Excellent guesses! Very high regional awareness.';
    gradeGlow = 'from-emerald-400 to-teal-500';
  } else if (scorePercent >= 50) {
    grade = 'Skilled Scout';
    gradeDesc = 'Solid performance! With a bit more practice, you will be unstoppable.';
    gradeGlow = 'from-blue-400 to-indigo-500';
  }

  return (
    <div className="h-screen w-screen bg-bgDark-950 flex flex-col md:flex-row overflow-hidden font-sans text-slate-100 select-none">
      
      {/* LEFT COLUMN: SCORE & ANALYSIS */}
      <div className="w-full md:w-[42%] h-full flex flex-col justify-between p-6 md:p-8 overflow-y-auto shrink-0 border-r border-white/10 relative z-10 bg-bgDark-950/90 backdrop-blur-xl">
        
        {/* Background glow orb */}
        <div className="absolute top-0 left-0 w-[80%] h-[40%] bg-radial-glow opacity-30 pointer-events-none" />

        {/* Title */}
        <div className="flex items-center justify-between border-b border-white/10 pb-4 mb-6">
          <div className="flex items-center gap-2 cursor-pointer" onClick={() => navigate('/')}>
            <div className="w-8 h-8 rounded-lg bg-brand-500 flex items-center justify-center font-black text-white text-md shadow-glow">I</div>
            <span className="text-base font-extrabold tracking-tight text-white">
              India<span className="text-brand-500 font-bold">Guessr</span>
            </span>
          </div>
          <span className="text-[10px] px-3.5 py-1 rounded-full bg-white/5 border border-white/10 font-bold text-slate-300 uppercase tracking-widest">
            {results.mode} Mode
          </span>
        </div>

        {/* Hero Score Badge */}
        <div className="text-center my-auto flex flex-col items-center animate-scale-up">
          
          <div className="w-16 h-16 rounded-2xl bg-brand-500/10 border border-brand-500/20 flex items-center justify-center text-brand-400 mb-5 shadow-glow">
            <Award className="w-8 h-8 drop-shadow-glow" />
          </div>

          <span className="text-[10px] text-slate-500 tracking-widest font-extrabold uppercase block mb-1">Final Score Summary</span>
          
          <h2 className="text-5xl md:text-6xl font-black tracking-tight text-white mb-3 flex items-baseline justify-center gap-1">
            <span>{results.total_score.toLocaleString()}</span>
            <span className="text-slate-500 text-lg font-bold"> / 25,000</span>
          </h2>

          <div className="w-full max-w-[320px] bg-bgDark-900 h-2.5 rounded-full overflow-hidden mb-6 border border-white/5">
            <div 
              className="bg-gradient-to-r from-brand-500 via-purple-500 to-indigo-500 h-full rounded-full shadow-glow" 
              style={{ width: `${scorePercent}%` }}
            />
          </div>

          {/* Grade display */}
          <div className="glass-panel p-5 rounded-2xl max-w-sm w-full mb-8 text-center border border-white/10 shadow-glow relative overflow-hidden group">
            <div className={`absolute inset-0 bg-gradient-to-r ${gradeGlow} opacity-5 group-hover:opacity-10 transition-opacity duration-300`} />
            <span className="text-[10px] text-slate-500 uppercase tracking-widest block font-bold mb-1">Performance Title</span>
            <span className="text-md font-black text-white block mb-1.5 tracking-tight">{grade}</span>
            <p className="text-xs text-slate-400 font-light leading-relaxed">{gradeDesc}</p>
          </div>

          {/* Core summary stats */}
          <div className="grid grid-cols-2 gap-4 w-full mb-8">
            <div className="bg-bgDark-900/50 p-4 rounded-2xl border border-white/5 text-left relative overflow-hidden">
              <span className="text-[10px] text-slate-500 font-bold block uppercase tracking-widest">Avg Precision</span>
              <span className="text-xl font-black text-slate-100 mt-1.5 block">
                {results.average_distance_km.toFixed(1)} <span className="text-xs text-slate-500 font-bold">km</span>
              </span>
            </div>
            
            <div className="bg-bgDark-900/50 p-4 rounded-2xl border border-white/5 text-left relative overflow-hidden">
              <span className="text-[10px] text-slate-500 font-bold block uppercase tracking-widest">Map Universe</span>
              <span className="text-xl font-black text-slate-100 mt-1.5 block capitalize flex items-center gap-1.5">
                {results.mode === 'india' ? (
                  <>
                    <MapPin className="w-4 h-4 text-brand-500 animate-pulse" />
                    <span>India</span>
                  </>
                ) : (
                  <>
                    <Globe className="w-4 h-4 text-emerald-500 animate-pulse" />
                    <span>World</span>
                  </>
                )}
              </span>
            </div>
          </div>

        </div>

        {/* Round by round breakdown list */}
        <div className="flex flex-col gap-3 mb-8 w-full animate-fade-in">
          <h4 className="text-[10px] font-extrabold text-slate-400 uppercase tracking-widest mb-1 border-b border-white/10 pb-2">Round Breakdown</h4>
          {results.rounds.map((round) => (
            <div 
              key={round.round_number}
              className="flex items-center justify-between p-3.5 bg-bgDark-900/30 rounded-xl border border-white/5 hover:border-brand-500/30 transition-all hover:bg-bgDark-900/60 duration-300 group"
            >
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg bg-bgDark-800 border border-white/5 flex items-center justify-center font-black text-xs text-slate-300 transition-colors group-hover:bg-brand-500 group-hover:text-white">
                  {round.round_number}
                </div>
                <div>
                  <span className="text-[10px] text-slate-500 block font-bold uppercase tracking-wider">Distance Offset</span>
                  <span className="text-xs font-semibold text-slate-200">
                    {round.distance_km !== null ? `${round.distance_km.toFixed(1)} km` : 'Skipped'}
                  </span>
                </div>
              </div>
              <div className="text-right">
                <span className="text-[10px] text-slate-500 block uppercase tracking-wider font-bold">Earned</span>
                <span className="text-sm font-black text-emerald-400">
                  {round.score !== null ? `+${round.score} pts` : '0 pts'}
                </span>
              </div>
            </div>
          ))}
        </div>

        {/* Action Buttons */}
        <div className="grid grid-cols-2 gap-4 border-t border-white/10 pt-6 mt-auto">
          <button
            onClick={() => navigate(`/game?mode=${results.mode}`)}
            className="flex items-center justify-center gap-2 py-4 px-4 rounded-xl bg-brand-500 hover:bg-brand-600 text-white font-extrabold text-xs tracking-wider transition-all duration-300 hover:scale-105 active:scale-95 shadow-glow border border-brand-400/20"
          >
            <RotateCcw className="w-4 h-4" />
            <span>PLAY AGAIN</span>
          </button>
          
          <button
            onClick={() => navigate('/')}
            className="flex items-center justify-center gap-2 py-4 px-4 rounded-xl bg-bgDark-900 hover:bg-bgDark-850 border border-white/10 text-slate-200 font-extrabold text-xs tracking-wider transition-all duration-300 hover:scale-105 active:scale-95"
          >
            <Home className="w-4 h-4" />
            <span>CHANGE MODE</span>
          </button>
        </div>

      </div>

      {/* RIGHT COLUMN: MAP SUMMARY OF ALL 5 ROUNDS */}
      <div className="flex-1 h-full relative z-0">
        <GoogleResultsMap results={results} />
      </div>

    </div>
  );
}

