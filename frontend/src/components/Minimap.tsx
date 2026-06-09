import { memo, useEffect, useState } from 'react';
import { MapContainer, TileLayer, Marker, Polyline, useMap, useMapEvents } from 'react-leaflet';
import L from 'leaflet';
import GoogleMinimap from './GoogleMinimap';

// Reusable SVG markers for Leaflet DivIcon
const createCustomIcon = (color: string, shadowColor: string) => {
  return L.divIcon({
    html: `
      <div style="position: relative; width: 18px; height: 18px;">
        <span style="
          position: absolute;
          top: 0; left: 0;
          display: block;
          width: 18px;
          height: 18px;
          border-radius: 50%;
          background: ${color};
          border: 3px solid #ffffff;
          box-shadow: 0 0 12px ${shadowColor};
          animation: pulse 2s infinite ease-in-out;
        "></span>
      </div>
    `,
    className: 'custom-glowing-marker',
    iconSize: [18, 18],
    iconAnchor: [9, 9]
  });
};

const guessIcon = createCustomIcon('#6366f1', 'rgba(99, 102, 241, 0.7)'); // Indigo
const actualIcon = createCustomIcon('#22c55e', 'rgba(34, 197, 94, 0.7)'); // Green

interface MinimapProps {
  guessedLatLng: [number, number] | null;
  actualLatLng: [number, number] | null;
  onGuessChange: (lat: number, lng: number) => void;
  showResult: boolean;
  disabled: boolean;
  gameMode: 'india' | 'world';
}

// Helper component to capture map click events
function MapClickHandler({ 
  onMapClick, 
  disabled 
}: { 
  onMapClick: (lat: number, lng: number) => void; 
  disabled: boolean 
}) {
  useMapEvents({
    click(e) {
      if (!disabled) {
        onMapClick(e.latlng.lat, e.latlng.lng);
      }
    },
  });
  return null;
}

// Helper component to automatically adjust viewport bounds to display both coordinates
function MapBoundsManager({
  guessed,
  actual,
  showResult
}: {
  guessed: [number, number] | null;
  actual: [number, number] | null;
  showResult: boolean;
}) {
  const map = useMap();

  useEffect(() => {
    if (showResult && guessed && actual) {
      const bounds = L.latLngBounds([guessed, actual]);
      map.fitBounds(bounds, {
        padding: [50, 50],
        maxZoom: 10,
        animate: true,
        duration: 1.2
      });
    }
  }, [showResult, guessed, actual, map]);

  return null;
}

function Minimap({
  guessedLatLng,
  actualLatLng,
  onGuessChange,
  showResult,
  disabled,
  gameMode
}: MinimapProps) {
  const [googleLoaded, setGoogleLoaded] = useState(false);
  const googleKey = (import.meta.env.VITE_GOOGLE_MAPS_API_KEY as string) || '';

  useEffect(() => {
    if (!googleKey) return;
    const scriptId = 'google-maps-script';
    if ((window as any).google && (window as any).google.maps) {
      setGoogleLoaded(true);
      return;
    }
    let script = document.getElementById(scriptId) as HTMLScriptElement;
    if (!script) {
      script = document.createElement('script');
      script.id = scriptId;
      script.src = `https://maps.googleapis.com/maps/api/js?key=${googleKey}`;
      script.async = true;
      script.defer = true;
      script.onload = () => setGoogleLoaded(true);
      script.onerror = () => setGoogleLoaded(false);
      document.head.appendChild(script);
    } else {
      const checkInterval = setInterval(() => {
        if ((window as any).google && (window as any).google.maps) {
          setGoogleLoaded(true);
          clearInterval(checkInterval);
        }
      }, 200);
      return () => clearInterval(checkInterval);
    }
  }, [googleKey]);
  // Center of India vs center of Earth
  const initialCenter: [number, number] = gameMode === 'india' ? [22.9734, 78.6569] : [20.0, 0.0];
  const initialZoom = gameMode === 'india' ? 4 : 2;

  // Build a custom mouse-following reticle cursor (data URI SVG)
  const getReticleCursor = () => {
    const svg = `<svg xmlns='http://www.w3.org/2000/svg' width='28' height='28' viewBox='0 0 28 28'><circle cx='14' cy='14' r='12' stroke='%23ffffff' stroke-width='2' fill='none' opacity='0.95'/><circle cx='14' cy='14' r='2' fill='%23ffffff'/></svg>`;
    return `url("data:image/svg+xml;utf8,${encodeURIComponent(svg)}") 14 14, crosshair`;
  };

  const reticleCursor = getReticleCursor();

  if (googleLoaded) {
    return (
      <div className="w-full h-full relative rounded-2xl overflow-hidden border border-bgDark-700 shadow-2xl" style={{ cursor: reticleCursor }}>
        <GoogleMinimap
          guessedLatLng={guessedLatLng}
          actualLatLng={actualLatLng}
          onGuessChange={onGuessChange}
          showResult={showResult}
          disabled={disabled}
          gameMode={gameMode}
          cursorStyle={reticleCursor}
        />
      </div>
    );
  }

  return (
    <div className="w-full h-full relative rounded-2xl overflow-hidden border border-bgDark-700 shadow-2xl" style={{ cursor: reticleCursor }}>
      <MapContainer
        center={initialCenter}
        zoom={initialZoom}
        style={{ width: '100%', height: '100%', cursor: reticleCursor }}
        zoomControl={true}
        attributionControl={true}
      >
        {/* Light-themed tiles for better readability in guessing map */}
        <TileLayer
          url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions">CARTO</a>'
        />

        <MapClickHandler onMapClick={onGuessChange} disabled={disabled} />
        
        <MapBoundsManager 
          guessed={guessedLatLng} 
          actual={actualLatLng} 
          showResult={showResult} 
        />

        {/* User's Guessed Location Marker */}
        {guessedLatLng && (
          <Marker position={guessedLatLng} icon={guessIcon} />
        )}

        {/* Actual Location Marker */}
        {showResult && actualLatLng && (
          <Marker position={actualLatLng} icon={actualIcon} />
        )}

        {/* Dotted Polyline connecting Guess and Actual location */}
        {showResult && guessedLatLng && actualLatLng && (
          <Polyline
            positions={[guessedLatLng, actualLatLng]}
            pathOptions={{
              color: '#818cf8',
              weight: 3,
              dashArray: '8, 8',
              opacity: 0.8
            }}
          />
        )}
      </MapContainer>
    </div>
  );
}

export default memo(Minimap);
