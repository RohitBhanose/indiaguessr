import { useEffect, useRef, useState } from 'react';
import { MapContainer, TileLayer, Marker, Polyline } from 'react-leaflet';
import L from 'leaflet';
import type { GameResults } from '../types';

interface Props {
  results: GameResults;
}

const guessIcon = L.divIcon({
  html: `<span style="display:block;width:14px;height:14px;border-radius:50%;background:#6366f1;border:2px solid #fff;"></span>`,
  className: '',
  iconSize: [14, 14],
  iconAnchor: [7, 7],
});

const actualIcon = L.divIcon({
  html: `<span style="display:block;width:14px;height:14px;border-radius:50%;background:#22c55e;border:2px solid #fff;"></span>`,
  className: '',
  iconSize: [14, 14],
  iconAnchor: [7, 7],
});

export default function GoogleResultsMap({ results }: Props) {
  const mapRef = useRef<HTMLDivElement | null>(null);
  const googleMapRef = useRef<any>(null);
  const markersRef = useRef<any[]>([]);
  const polysRef = useRef<any[]>([]);
  const [loaded, setLoaded] = useState(false);
  const googleKey = (import.meta.env.VITE_GOOGLE_MAPS_API_KEY as string) || '';

  useEffect(() => {
    if (!googleKey) return;
    const scriptId = 'google-maps-results-script';
    if (window.google?.maps) {
      setLoaded(true);
      return;
    }
    let script = document.getElementById(scriptId) as HTMLScriptElement;
    if (!script) {
      script = document.createElement('script');
      script.id = scriptId;
      script.src = `https://maps.googleapis.com/maps/api/js?key=${googleKey}`;
      script.async = true;
      script.defer = true;
      script.onload = () => setLoaded(true);
      document.head.appendChild(script);
    } else {
      const checkInterval = setInterval(() => {
        if (window.google?.maps) {
          setLoaded(true);
          clearInterval(checkInterval);
        }
      }, 200);
      return () => clearInterval(checkInterval);
    }
  }, [googleKey]);

  useEffect(() => {
    if (!loaded || !window.google?.maps || !mapRef.current) return;
    const google = window.google;

    if (!googleMapRef.current) {
      googleMapRef.current = new google.maps.Map(mapRef.current, {
        center: { lat: 20, lng: 0 },
        zoom: 2,
        mapTypeId: 'roadmap',
        disableDefaultUI: true,
        zoomControl: true,
      });
      try {
        googleMapRef.current.getDiv().style.cursor = 'crosshair';
      } catch {
        // ignore
      }
    }

    markersRef.current.forEach((m) => m.setMap(null));
    polysRef.current.forEach((p) => p.setMap(null));
    markersRef.current = [];
    polysRef.current = [];

    const bounds = new google.maps.LatLngBounds();

    results.rounds.forEach((r) => {
      if (r.guessed_lat === null || r.guessed_lng === null) return;
      const guessPos = { lat: r.guessed_lat, lng: r.guessed_lng };
      const actualPos = { lat: r.actual_lat, lng: r.actual_lng };

      const guessMarker = new google.maps.Marker({
        position: guessPos,
        map: googleMapRef.current!,
        label: { text: String(r.round_number), color: 'white', fontSize: '12px' },
      });
      const actualMarker = new google.maps.Marker({
        position: actualPos,
        map: googleMapRef.current!,
        label: { text: String(r.round_number), color: 'white', fontSize: '12px' },
      });
      markersRef.current.push(guessMarker, actualMarker);

      const poly = new google.maps.Polyline({
        path: [guessPos, actualPos],
        geodesic: true,
        strokeColor: '#818cf8',
        strokeOpacity: 0.8,
        strokeWeight: 3,
      });
      poly.setMap(googleMapRef.current!);
      polysRef.current.push(poly);

      bounds.extend(new google.maps.LatLng(guessPos.lat, guessPos.lng));
      bounds.extend(new google.maps.LatLng(actualPos.lat, actualPos.lng));
    });

    if (!bounds.isEmpty()) {
      googleMapRef.current!.fitBounds(bounds, 50);
    }

    return () => {
      markersRef.current.forEach((m) => m.setMap(null));
      polysRef.current.forEach((p) => p.setMap(null));
    };
  }, [loaded, results]);

  if (!googleKey || !loaded) {
    const center: [number, number] =
      results.mode === 'india' ? [22.9734, 78.6569] : [20.0, 0.0];
    const zoom = results.mode === 'india' ? 4 : 2;

    return (
      <div className="w-full h-full">
        <MapContainer center={center} zoom={zoom} style={{ width: '100%', height: '100%' }}>
          <TileLayer
            url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
            attribution='&copy; OpenStreetMap &copy; CARTO'
          />
          {results.rounds.map((r) => {
            if (r.guessed_lat === null || r.guessed_lng === null) return null;
            return (
              <div key={r.round_number}>
                <Marker position={[r.guessed_lat, r.guessed_lng]} icon={guessIcon} />
                <Marker position={[r.actual_lat, r.actual_lng]} icon={actualIcon} />
                <Polyline
                  positions={[
                    [r.guessed_lat, r.guessed_lng],
                    [r.actual_lat, r.actual_lng],
                  ]}
                  pathOptions={{ color: '#818cf8', weight: 3, dashArray: '8, 8' }}
                />
              </div>
            );
          })}
        </MapContainer>
      </div>
    );
  }

  return <div className="w-full h-full" ref={mapRef} />;
}
