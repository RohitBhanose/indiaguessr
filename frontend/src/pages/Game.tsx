import { useCallback, useEffect, useState } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { api } from '../services/api';
import type { GameSession, GuessResponse } from '../types';
import StreetView from '../components/StreetView';
import Minimap from '../components/Minimap';
import { 
  Globe, 
  Flag, 
  CheckCircle, 
  ArrowRight, 
  MapPin, 
  Trophy, 
  Navigation,
  RotateCcw,
  Loader2
} from 'lucide-react';

export default function Game() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const mode = (searchParams.get('mode') as 'india' | 'world') || 'india';
  const apiKey = import.meta.env.VITE_GOOGLE_MAPS_API_KEY || '';

  // Game state
  const [session, setSession] = useState<GameSession | null>(null);
  const [guessedLatLng, setGuessedLatLng] = useState<[number, number] | null>(null);
  const [submittedRound, setSubmittedRound] = useState<GuessResponse | null>(null);
  const [totalScore, setTotalScore] = useState<number>(0);
  
  // Loading & Error States
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Layout states
  const [isMapExpanded, setIsMapExpanded] = useState(false);

  // Initialize game session
  useEffect(() => {
    async function initGame() {
      try {
        setLoading(true);
        const newSession = await api.startGame(mode);
        setSession(newSession);
        setTotalScore(0);
        setError(null);
      } catch (err: any) {
        console.error(err);
        setError(err.message || 'Failed to start game session.');
      } finally {
        setLoading(false);
      }
    }
    initGame();
  }, [mode]);

  const handleGuessChange = useCallback((lat: number, lng: number) => {
    if (submittedRound) return; // Locked on submission
    setGuessedLatLng([lat, lng]);
  }, [submittedRound]);

  const handleLocationUpdated = useCallback((newLat: number, newLng: number) => {
    setSession((current) => {
      if (!current) return current;
      return {
        ...current,
        streetview_lat: newLat,
        streetview_lng: newLng
      };
    });
  }, []);

  const handleSubmitGuess = async () => {
    if (!session || !guessedLatLng || submittedRound || submitting) return;

    try {
      setSubmitting(true);
      const result = await api.submitGuess(
        session.game_id,
        guessedLatLng[0],
        guessedLatLng[1]
      );
      setSubmittedRound(result);
      setTotalScore((s) => s + (result.score || 0));
    } catch (err: any) {
      console.error(err);
      alert(err.message || 'Error submitting guess.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleNextRound = async () => {
    if (!session || !submittedRound) return;

    if (submittedRound.is_game_completed) {
      navigate(`/results?game_id=${session.game_id}`);
      return;
    }

    try {
      setLoading(true);
      setGuessedLatLng(null);
      setSubmittedRound(null);
      
      const nextSession = await api.nextRound(session.game_id);
      setSession(nextSession);
    } catch (err: any) {
      console.error(err);
      setError('Failed to load next round.');
    } finally {
      setLoading(false);
    }
  };

  const handleMapMouseEnter = useCallback(() => {
    setIsMapExpanded(true);
  }, []);

  const handleMapMouseLeave = useCallback(() => {
    setIsMapExpanded(false);
  }, []);

  if (loading && !session) {
    return (
      <div className="min-h-screen bg-bgDark-950 flex flex-col items-center justify-center text-slate-100 relative overflow-hidden">
        {/* Decorative background grid and glow */}
        <div className="absolute inset-0 bg-radial-glow opacity-30 pointer-events-none" />
        <div className="absolute inset-0 bg-grid-pattern opacity-10 pointer-events-none" />
        
        <div className="flex flex-col items-center gap-4 px-8 py-10 rounded-2xl glass-panel-heavy border border-white/10 shadow-glow max-w-sm text-center z-10 animate-scale-up">
          <Loader2 className="w-12 h-12 text-brand-500 animate-spin drop-shadow-glow" />
          <h3 className="text-sm font-extrabold tracking-widest text-slate-300 uppercase mt-2">Initializing Round</h3>
          <p className="text-xs text-slate-400 font-light">Loading high-fidelity Street View panorama...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-bgDark-950 flex flex-col items-center justify-center text-slate-100 p-6 text-center relative overflow-hidden">
        <div className="absolute inset-0 bg-radial-glow opacity-25 pointer-events-none" />
        <div className="flex flex-col items-center max-w-md px-8 py-10 rounded-2xl glass-panel border border-red-500/20 shadow-[0_15px_40px_rgba(239,68,68,0.1)] z-10 animate-scale-up">
          <div className="w-16 h-16 rounded-full bg-red-500/10 border border-red-500/20 flex items-center justify-center text-red-400 mb-6">
            <Flag className="w-8 h-8" />
          </div>
          <h2 className="text-xl font-black mb-2 text-white tracking-tight">System Initialization Error</h2>
          <p className="text-slate-400 text-sm mb-8 font-light">{error}</p>
          <button
            onClick={() => navigate('/')}
            className="flex items-center gap-2 px-6 py-3.5 rounded-xl bg-brand-500 hover:bg-brand-600 font-bold text-sm tracking-wide text-white transition-all duration-300 shadow-glow hover:scale-105 active:scale-95 border border-brand-400/20"
          >
            <RotateCcw className="w-4 h-4" />
            <span>RETURN HOME</span>
          </button>
        </div>
      </div>
    );
  }
  if (!session) return null;

  const showResult = !!submittedRound;

  return (
    <div className="h-screen w-screen bg-bgDark-950 flex flex-col overflow-hidden relative font-sans text-slate-100 selection:bg-brand-500/30">
      
      {/* 1. TOP HUD HEADER BAR */}
      <header className="h-20 border-b border-white/10 bg-bgDark-950/85 backdrop-blur-xl flex items-center justify-between px-6 z-20 shrink-0">
        <div className="flex items-center gap-6">
          <div className="flex items-center gap-2.5 cursor-pointer group" onClick={() => navigate('/')}>
            <div className="w-9 h-9 rounded-xl bg-brand-500 flex items-center justify-center font-black text-white text-lg shadow-glow group-hover:scale-105 transition-all">I</div>
            <span className="font-extrabold tracking-tight text-slate-100 text-lg md:text-xl transition-all group-hover:text-brand-400">
              India<span className="text-brand-500 font-bold">Guessr</span>
            </span>
          </div>
          
          <div className="h-6 w-px bg-white/10 hidden sm:block" />

          {/* Mode Badge */}
          <div className="hidden sm:flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-white/5 border border-white/10 text-xs font-semibold text-slate-300">
            {session.mode === 'india' ? (
              <>
                <MapPin className="w-4 h-4 text-brand-500 animate-pulse" />
                <span>India Mode</span>
              </>
            ) : (
              <>
                <Globe className="w-4 h-4 text-emerald-500 animate-pulse" />
                <span>World Mode</span>
              </>
            )}
          </div>
        </div>

        {/* HUD Info Widgets */}
        <div className="flex items-center gap-6">
          {/* Round counter */}
          <div className="flex flex-col items-end sm:items-center bg-white/5 border border-white/5 rounded-xl px-4 py-1.5">
            <span className="text-[10px] text-slate-500 font-bold tracking-widest uppercase">Round</span>
            <span className="text-base font-black text-white">{session.current_round} <span className="text-slate-500 text-xs font-semibold">/ 5</span></span>
          </div>

          {/* Score Counter */}
          <div className="flex flex-col items-end sm:items-center bg-amber-500/5 border border-amber-500/10 rounded-xl px-4 py-1.5">
            <span className="text-[10px] text-amber-500/60 font-bold tracking-widest uppercase">Accumulated Score</span>
            <span className="text-base font-black text-amber-400 flex items-center gap-1.5 drop-shadow-gold">
              <Trophy className="w-4 h-4 text-amber-400" />
              <span>{totalScore}</span>
            </span>
          </div>
        </div>
      </header>

      {/* 2. MAIN SPLIT/FULL VIEW AREA */}
      <main className="flex-1 w-full relative flex flex-col md:flex-row overflow-hidden">
        
        {/* Left Side: Street View Container (Toggles 50% split when result is revealed) */}
        <div className={`h-full relative transition-all duration-500 ease-in-out ${showResult ? 'w-full md:w-1/2' : 'w-full'}`}>
          <StreetView 
            key={`${session.game_id}-${session.current_round}`}
            latitude={session.streetview_lat}
            longitude={session.streetview_lng}
            panoramaId={session.panorama_id}
            apiKey={apiKey}
            gameId={session.game_id}
            onLocationUpdated={handleLocationUpdated}
          />
        </div>

        {/* Right Side: Leaflet Map Container */}
        {!showResult ? (
          /* FLOATING MINI-MAP (PLAYING STATE) */
          <div 
            onMouseEnter={handleMapMouseEnter}
            onMouseLeave={handleMapMouseLeave}
            className={`absolute bottom-6 right-6 z-20 transition-all duration-300 ease-in-out shadow-[0_20px_50px_rgba(0,0,0,0.6)] rounded-2xl overflow-hidden border border-white/10 ${
              isMapExpanded 
                ? 'w-[320px] h-[240px] md:w-[480px] md:h-[360px] opacity-100 scale-100' 
                : 'w-[180px] h-[140px] md:w-[280px] md:h-[200px] opacity-85 hover:opacity-100 hover:scale-105'
            }`}
          >
            <div className="w-full h-full relative">
              <Minimap
                guessedLatLng={guessedLatLng}
                actualLatLng={null}
                onGuessChange={handleGuessChange}
                showResult={false}
                disabled={false}
                gameMode={session.mode}
              />
              
              {/* Floating Submit HUD overlay */}
              {guessedLatLng && (
                <div className="absolute bottom-4 inset-x-4 z-[999] pointer-events-none flex justify-center">
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleSubmitGuess();
                    }}
                    disabled={submitting}
                    className="pointer-events-auto flex items-center gap-2 px-5 py-3 rounded-xl bg-brand-500 hover:bg-brand-600 text-white font-extrabold text-xs tracking-wider shadow-glow transition-all duration-300 hover:scale-105 active:scale-95 disabled:bg-bgDark-800 disabled:text-slate-500 border border-brand-400/20"
                  >
                    {submitting ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <CheckCircle className="w-4 h-4" />
                    )}
                    <span>SUBMIT GUESS</span>
                  </button>
                </div>
              )}
            </div>
          </div>
        ) : (
          /* SPLIT PANEL VIEW (RESULT REVEALED STATE) */
          <div className="w-full md:w-1/2 h-full relative animate-fade-in border-l border-white/10 flex flex-col">
            <div className="flex-1 w-full relative">
              <Minimap
                guessedLatLng={guessedLatLng}
                actualLatLng={[submittedRound.actual_lat, submittedRound.actual_lng]}
                onGuessChange={handleGuessChange}
                showResult={true}
                disabled={true}
                gameMode={session.mode}
              />
            </div>

            {/* Results Floating Panel on Map */}
            <div className="absolute top-6 left-6 right-6 z-[999] glass-panel-heavy p-6 rounded-2xl flex flex-col sm:flex-row items-center justify-between gap-6 border border-white/10 shadow-[0_20px_50px_rgba(0,0,0,0.5)]">
              <div className="flex items-center gap-4">
                <div className="p-3.5 rounded-xl bg-brand-500/10 border border-brand-500/20 text-brand-400">
                  <Navigation className="w-7 h-7 animate-pulse drop-shadow-glow" />
                </div>
                <div>
                  <h4 className="text-sm font-black text-slate-100 tracking-wide">Round {submittedRound.round_number} Complete</h4>
                  <p className="text-xs text-slate-400 font-light mt-1">
                    Your guess was <span className="text-brand-400 font-extrabold">{submittedRound.distance_km.toFixed(2)} km</span> away.
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-6 w-full sm:w-auto justify-between sm:justify-end border-t sm:border-t-0 border-white/5 pt-4 sm:pt-0">
                <div className="text-right">
                  <span className="text-[10px] text-slate-500 uppercase tracking-widest block font-bold">Points Awarded</span>
                  <span className="text-3xl font-black text-emerald-400 drop-shadow-glow">+{submittedRound.score} <span className="text-xs text-emerald-500/70 font-extrabold">pts</span></span>
                </div>
                
                <button
                  onClick={handleNextRound}
                  className="flex items-center gap-2 px-6 py-4 rounded-xl bg-brand-500 hover:bg-brand-600 text-white font-extrabold text-xs tracking-wider transition-all duration-300 hover:scale-105 active:scale-95 shadow-glow border border-brand-400/20"
                >
                  <span>{submittedRound.is_game_completed ? 'VIEW BREAKDOWN' : 'NEXT ROUND'}</span>
                  <ArrowRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
