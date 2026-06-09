import { useEffect, useRef } from 'react';

interface GoogleMinimapProps {
  guessedLatLng: [number, number] | null;
  actualLatLng: [number, number] | null;
  onGuessChange: (lat: number, lng: number) => void;
  showResult: boolean;
  disabled: boolean;
  gameMode: 'india' | 'world';
  cursorStyle?: string;
}
export default function GoogleMinimap({ guessedLatLng, actualLatLng, onGuessChange, showResult, disabled, gameMode, cursorStyle }: GoogleMinimapProps) {
  const mapRef = useRef<HTMLDivElement | null>(null);
  const googleMapRef = useRef<any>(null);
  const guessMarkerRef = useRef<any>(null);
  const actualMarkerRef = useRef<any>(null);
  const polyRef = useRef<any>(null);

  useEffect(() => {
    if (!(window as any).google?.maps || !mapRef.current) return;
    const google = (window as any).google;
    const center = gameMode === 'india' ? { lat: 22.9734, lng: 78.6569 } : { lat: 20.0, lng: 0.0 };
    const zoom = gameMode === 'india' ? 4 : 2;
    if (!googleMapRef.current) {
      googleMapRef.current = new google.maps.Map(mapRef.current, {
        center,
        zoom,
        mapTypeId: 'roadmap',
        disableDefaultUI: true,
        zoomControl: true,
      });

      // Apply custom cursor if provided
      try {
        const div = googleMapRef.current.getDiv();
        if (div && div.style) div.style.cursor = cursorStyle || 'crosshair';
      } catch (e) {}

      // Click handler uses event coordinates (mouse pointer)
      googleMapRef.current.addListener('click', (e: any) => {
        if (disabled) return;
        const lat = e.latLng.lat();
        const lng = e.latLng.lng();
        onGuessChange(lat, lng);
      });
    }

    // Update guess marker
    if (guessedLatLng) {
      const pos = { lat: guessedLatLng[0], lng: guessedLatLng[1] };
      if (!guessMarkerRef.current) {
        guessMarkerRef.current = new google.maps.Marker({ position: pos, map: googleMapRef.current, label: 'G' });
      } else {
        guessMarkerRef.current.setPosition(pos);
        guessMarkerRef.current.setMap(googleMapRef.current);
      }
    } else if (guessMarkerRef.current) {
      guessMarkerRef.current.setMap(null);
      guessMarkerRef.current = null;
    }

    // Update actual marker
    if (showResult && actualLatLng) {
      const pos = { lat: actualLatLng[0], lng: actualLatLng[1] };
      if (!actualMarkerRef.current) {
        actualMarkerRef.current = new google.maps.Marker({ position: pos, map: googleMapRef.current, label: 'A' });
      } else {
        actualMarkerRef.current.setPosition(pos);
        actualMarkerRef.current.setMap(googleMapRef.current);
      }
    } else if (actualMarkerRef.current) {
      actualMarkerRef.current.setMap(null);
      actualMarkerRef.current = null;
    }

    // Polyline between guess and actual
    if (showResult && guessedLatLng && actualLatLng) {
      const path = [ { lat: guessedLatLng[0], lng: guessedLatLng[1] }, { lat: actualLatLng[0], lng: actualLatLng[1] } ];
      if (!polyRef.current) {
        polyRef.current = new google.maps.Polyline({ path, geodesic: true, strokeColor: '#818cf8', strokeOpacity: 0.8, strokeWeight: 3, icons: [{offset: '0', repeat: '20px'}] });
        polyRef.current.setMap(googleMapRef.current);
      } else {
        polyRef.current.setPath(path);
        polyRef.current.setMap(googleMapRef.current);
      }
      // Fit bounds
      const bounds = new google.maps.LatLngBounds();
      bounds.extend(new google.maps.LatLng(guessedLatLng[0], guessedLatLng[1]));
      bounds.extend(new google.maps.LatLng(actualLatLng[0], actualLatLng[1]));
      googleMapRef.current.fitBounds(bounds, 50);
    } else if (polyRef.current) {
      polyRef.current.setMap(null);
      polyRef.current = null;
    }

    return () => {
      // leave map in DOM; Google Maps API handles cleanup when container removed
    };
  }, [guessedLatLng, actualLatLng, showResult, disabled, gameMode, onGuessChange]);

  return (
    <div ref={mapRef} style={{ width: '100%', height: '100%', cursor: cursorStyle || 'crosshair' }} />
  );
}
