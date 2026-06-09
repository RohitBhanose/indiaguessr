import { memo, useEffect, useRef, useState } from 'react';
import { Compass, RotateCcw, AlertTriangle, Move } from 'lucide-react';
import { api } from '../services/api';

interface StreetViewProps {
  latitude: number;
  longitude: number;
  apiKey: string;
  panoramaId?: string | null;
  gameId?: string;
  onLocationUpdated?: (lat: number, lng: number) => void;
  onNoPanorama?: () => void;
}

const MOCK_PANO_IMAGES: { [key: string]: string } = {
  "27.1751": "https://images.unsplash.com/photo-1564507592333-c60657eea523?auto=format&fit=crop&w=1920&q=80",
  "18.9220": "https://images.unsplash.com/photo-1566552881560-0be862a7c445?auto=format&fit=crop&w=1920&q=80",
  "28.5244": "https://images.unsplash.com/photo-1587135941948-670b381f08ce?auto=format&fit=crop&w=1920&q=80",
  "12.9756": "https://images.unsplash.com/photo-1596176530529-78163a4f7af2?auto=format&fit=crop&w=1920&q=80",
  "18.9415": "https://images.unsplash.com/photo-1562979314-bee7453e911c?auto=format&fit=crop&w=1920&q=80",
  "26.9124": "https://images.unsplash.com/photo-1477587458883-471a5ed94245?auto=format&fit=crop&w=1920&q=80",
  "17.3616": "https://images.unsplash.com/photo-1608958416710-bb979bd1a9c3?auto=format&fit=crop&w=1920&q=80",
  "10.0889": "https://images.unsplash.com/photo-1593693397690-362cb9666fc2?auto=format&fit=crop&w=1920&q=80",
  "34.0268": "https://images.unsplash.com/photo-1614093666270-b74a3f1d5d1c?auto=format&fit=crop&w=1920&q=80",
  "48.8584": "https://images.unsplash.com/photo-1502602898657-3e91760cbb34?auto=format&fit=crop&w=1920&q=80",
  "40.7580": "https://images.unsplash.com/photo-1534430480872-3498386e7856?auto=format&fit=crop&w=1920&q=80",
  "41.8902": "https://images.unsplash.com/photo-1552832230-c0197dd311b5?auto=format&fit=crop&w=1920&q=80",
  "35.6595": "https://images.unsplash.com/photo-1540959733332-eab4deceeaf7?auto=format&fit=crop&w=1920&q=80",
  "51.5007": "https://images.unsplash.com/photo-1513635269975-59663e0ac1ad?auto=format&fit=crop&w=1920&q=80",
  "29.9792": "https://images.unsplash.com/photo-1539650116574-8efeb43e2750?auto=format&fit=crop&w=1920&q=80",
  "-33.8568": "https://images.unsplash.com/photo-1506973035872-a4ec16b8e8d9?auto=format&fit=crop&w=1920&q=80",
};

const DEFAULT_MOCK_IMAGE = "https://images.unsplash.com/photo-1469854523086-cc02fe5d8800?auto=format&fit=crop&w=1920&q=80";

function isOfficialPanorama(panoId: string, copyright: string): boolean {
  const copyrightLower = copyright.toLowerCase();
  if (
    copyrightLower.includes('google') ||
    copyrightLower.includes('trekker') ||
    copyrightLower.includes('street view')
  ) {
    return true;
  }
  return panoId.startsWith('CAoS') || !panoId.startsWith('AF1Qip');
}

function isIndoorPanorama(copyright: string): boolean {
  const copyrightLower = copyright.toLowerCase();
  return (
    copyrightLower.includes('indoor') ||
    copyrightLower.includes('interior') ||
    copyrightLower.includes('business')
  );
}

export default memo(StreetView);

function StreetView({
  latitude,
  longitude,
  apiKey,
  panoramaId,
  gameId,
  onLocationUpdated,
  onNoPanorama,
}: StreetViewProps) {
  console.log('StreetView rerendered');
  const containerRef = useRef<HTMLDivElement>(null);
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const panoramaRef = useRef<any>(null);
  const svServiceRef = useRef<any>(null);

  const [googleApiLoaded, setGoogleApiLoaded] = useState(false);
  const [isMockMode, setIsMockMode] = useState(!apiKey);
  const [isDragging, setIsDragging] = useState(false);
  const [startX, setStartX] = useState(0);
  const [scrollLeft, setScrollLeft] = useState(0);
  const [heading, setHeading] = useState(0);
  const [loadingPanorama, setLoadingPanorama] = useState(!!apiKey);
  const [panoramaError, setPanoramaError] = useState<string | null>(null);
  const [loadingText, setLoadingText] = useState('Loading Street View…');
  const [retryCount, setRetryCount] = useState(0);

  useEffect(() => {
    console.log('StreetView mounted');
  }, []);

  useEffect(() => {
    if (!apiKey) {
      setIsMockMode(true);
      setLoadingPanorama(false);
      return;
    }

    const scriptId = 'google-maps-streetview-script';
    let script = document.getElementById(scriptId) as HTMLScriptElement;

    const initPanorama = () => {
      setGoogleApiLoaded(true);
      setIsMockMode(false);
    };

    if (window.google?.maps) {
      initPanorama();
      return;
    }

    if (!script) {
      script = document.createElement('script');
      script.id = scriptId;
      script.src = `https://maps.googleapis.com/maps/api/js?key=${apiKey}&callback=__googleMapsInitCallback`;
      script.async = true;
      script.defer = true;

      window.__googleMapsInitCallback = () => {
        initPanorama();
      };

      script.onerror = () => {
        setIsMockMode(true);
        setLoadingPanorama(false);
        setPanoramaError('Google Maps script failed to load.');
      };

      document.head.appendChild(script);
    } else {
      const checkInterval = setInterval(() => {
        if (window.google?.maps) {
          initPanorama();
          clearInterval(checkInterval);
        }
      }, 200);
      return () => clearInterval(checkInterval);
    }
  }, [apiKey]);

  useEffect(() => {
    if (!googleApiLoaded || isMockMode || !containerRef.current || !window.google?.maps) {
      return;
    }

    let cancelled = false;
    const google = window.google;
    const searchRadii = [50, 250, 1000, 5000, 15000];

    const cleanupPanorama = () => {
      if (panoramaRef.current) {
        try {
          google.maps.event.clearInstanceListeners(panoramaRef.current);
        } catch {
          // ignore
        }
        panoramaRef.current = null;
      }
      if (containerRef.current) {
        containerRef.current.innerHTML = '';
      }
    };

    const handleLoadFailure = (reason: string) => {
      if (cancelled) return;
      console.warn('StreetView: falling back to mock mode —', reason);
      setPanoramaError(reason);
      setIsMockMode(true);
      setLoadingPanorama(false);
      onNoPanorama?.();
    };

    const syncSnappedLocation = async (foundLat: number, foundLng: number) => {
      if (
        Math.abs(foundLat - latitude) <= 1e-5 &&
        Math.abs(foundLng - longitude) <= 1e-5
      ) {
        return;
      }

      onLocationUpdated?.(foundLat, foundLng);
      if (gameId) {
        try {
          await api.updateRoundLocation(gameId, foundLat, foundLng);
        } catch (e) {
          console.error('StreetView: failed to update round coordinates', e);
        }
      }
    };

    const renderPanorama = async (
      pano: string,
      foundLat: number | null,
      foundLng: number | null
    ) => {
      if (cancelled || !containerRef.current) return;

      try {
        cleanupPanorama();

        panoramaRef.current = new google.maps.StreetViewPanorama(containerRef.current, {
          pano,
          pov: { heading: 90, pitch: 0 },
          zoom: 0,
          addressControl: false,
          showRoadLabels: false,
          motionTracking: false,
          motionTrackingControl: false,
          linksControl: true,
          panControl: true,
          zoomControl: true,
          enableCloseButton: false,
        });

        panoramaRef.current.addListener('pano_changed', () => {
          const status = panoramaRef.current?.getStatus();
          if (status && status !== google.maps.StreetViewStatus.OK) {
            handleLoadFailure('Panorama became unavailable after load.');
          }
        });

        panoramaRef.current.addListener('pov_changed', () => {
          const pov = panoramaRef.current?.getPov();
          if (pov?.heading !== undefined) {
            setHeading(Math.round(pov.heading % 360));
          }
        });

        setLoadingPanorama(false);
        setPanoramaError(null);
        console.log('Panorama loaded');

        if (foundLat !== null && foundLng !== null) {
          await syncSnappedLocation(foundLat, foundLng);
        }
      } catch (err) {
        console.error('StreetView: exception creating panorama', err);
        handleLoadFailure('Error rendering panorama instance.');
      }
    };

    const validatePanoramaData = (
      data: any,
      status: string
    ): { ok: boolean; reason?: string; panoId?: string; lat?: number; lng?: number } => {
      if (status !== google.maps.StreetViewStatus.OK || !data?.location?.pano) {
        return { ok: false, reason: 'No Street View coverage found nearby.' };
      }

      const panoId = data.location.pano;
      const foundLatLng = data.location.latLng;
      const copyright = data.copyright || '';

      if (!isOfficialPanorama(panoId, copyright)) {
        return { ok: false, reason: 'User photo sphere rejected.' };
      }
      if (isIndoorPanorama(copyright)) {
        return { ok: false, reason: 'Indoor panorama rejected.' };
      }

      return {
        ok: true,
        panoId,
        lat: foundLatLng?.lat() ?? null,
        lng: foundLatLng?.lng() ?? null,
      };
    };

    const searchByRadius = (index = 0) => {
      if (cancelled) return;

      const radius = searchRadii[index] ?? 15000;
      console.log('Panorama loading');
      setLoadingPanorama(true);
      setPanoramaError(null);
      setLoadingText(
        index === 0 && panoramaId
          ? 'Loading verified panorama…'
          : `Searching official coverage (${radius}m)…`
      );

      const svService = svServiceRef.current ?? new google.maps.StreetViewService();
      svServiceRef.current = svService;

      const request: any = panoramaId && index === 0
        ? { pano: panoramaId }
        : {
            location: new google.maps.LatLng(latitude, longitude),
            radius,
            source: google.maps.StreetViewSource.OUTDOOR,
          };

      svService.getPanorama(request, async (data: any, status: string) => {
        if (cancelled) return;

        const validation = validatePanoramaData(data, status);
        if (validation.ok && validation.panoId) {
          await renderPanorama(
            validation.panoId,
            validation.lat ?? null,
            validation.lng ?? null
          );
          return;
        }

        if (index < searchRadii.length - 1) {
          searchByRadius(index + 1);
          return;
        }

        handleLoadFailure(validation.reason || 'No navigable outdoor Street View found nearby.');
      });
    };

    setLoadingPanorama(true);
    searchByRadius(0);

    return () => {
      cancelled = true;
      cleanupPanorama();
    };
  }, [
    googleApiLoaded,
    isMockMode,
    latitude,
    longitude,
    panoramaId,
    gameId,
    onLocationUpdated,
    onNoPanorama,
    retryCount,
  ]);

  const getMockImage = () => {
    const latKey = latitude.toFixed(4);
    return MOCK_PANO_IMAGES[latKey] || DEFAULT_MOCK_IMAGE;
  };

  const handleMouseDown = (e: React.MouseEvent) => {
    if (!scrollContainerRef.current) return;
    setIsDragging(true);
    setStartX(e.pageX - scrollContainerRef.current.offsetLeft);
    setScrollLeft(scrollContainerRef.current.scrollLeft);
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!isDragging || !scrollContainerRef.current) return;
    e.preventDefault();
    const x = e.pageX - scrollContainerRef.current.offsetLeft;
    const walk = (x - startX) * 1.5;
    scrollContainerRef.current.scrollLeft = scrollLeft - walk;

    const maxScroll =
      scrollContainerRef.current.scrollWidth - scrollContainerRef.current.clientWidth;
    const currentScroll = scrollContainerRef.current.scrollLeft;
    const percent = maxScroll > 0 ? currentScroll / maxScroll : 0;
    setHeading(Math.round(percent * 360));
  };

  const handleMouseUpOrLeave = () => {
    setIsDragging(false);
  };

  const resetMockScroll = () => {
    if (scrollContainerRef.current) {
      const target =
        (scrollContainerRef.current.scrollWidth - scrollContainerRef.current.clientWidth) / 2;
      scrollContainerRef.current.scrollLeft = target;
      setHeading(180);
    }
  };

  useEffect(() => {
    if (isMockMode) {
      setTimeout(resetMockScroll, 100);
    }
  }, [latitude, longitude, isMockMode]);

  const handleRetry = () => {
    setPanoramaError(null);
    setIsMockMode(false);
    setLoadingPanorama(true);
    setRetryCount((c) => c + 1);
  };

  return (
    <div className="w-full h-full relative rounded-2xl overflow-hidden border border-bgDark-700 shadow-2xl bg-bgDark-900 group">
      {!isMockMode ? (
        <div ref={containerRef} className="w-full h-full bg-bgDark-800" id="streetview-panorama" />
      ) : (
        <div
          ref={scrollContainerRef}
          className="w-full h-full overflow-hidden whitespace-nowrap cursor-grab select-none active:cursor-grabbing"
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUpOrLeave}
          onMouseLeave={handleMouseUpOrLeave}
          style={{ overflowX: 'hidden' }}
        >
          <div className="inline-block h-full w-[300%] relative">
            <img
              src={getMockImage()}
              alt="Simulated Street View panorama"
              className="w-full h-full object-cover pointer-events-none"
              onError={(e) => {
                (e.target as HTMLImageElement).src = DEFAULT_MOCK_IMAGE;
              }}
            />
            <div className="absolute inset-0 bg-gradient-to-t from-bgDark-950/40 via-transparent to-bgDark-950/20 pointer-events-none" />
          </div>
        </div>
      )}

      {loadingPanorama && !isMockMode && (
        <div className="absolute inset-0 z-30 flex items-center justify-center bg-bgDark-950/70 backdrop-blur-sm transition-all duration-300">
          <div className="flex flex-col items-center gap-4 px-6 py-8 rounded-2xl glass-panel border border-white/10 shadow-glow max-w-xs text-center">
            <div className="w-12 h-12 border-4 border-t-transparent border-brand-500 rounded-full animate-spin shadow-glow" />
            <div className="text-sm font-bold text-slate-100 tracking-wide">{loadingText}</div>
            <div className="text-xs text-slate-400 font-light">Validating official Google coverage...</div>
          </div>
        </div>
      )}

      {panoramaError && isMockMode && (
        <div className="absolute top-4 right-4 z-40 max-w-xs">
          <div className="bg-bgDark-950/95 border border-amber-500/20 p-3 rounded-xl text-xs text-slate-300 flex items-start gap-2">
            <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
            <div>
              <p>{panoramaError} Showing simulated panorama.</p>
              {apiKey && (
                <button
                  onClick={handleRetry}
                  className="mt-2 text-brand-400 hover:text-brand-300 font-semibold"
                >
                  Retry Street View
                </button>
              )}
            </div>
          </div>
        </div>
      )}

      <div className="absolute top-4 left-4 z-10 flex items-center gap-3">
        <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-bgDark-950/85 backdrop-blur-md border border-white/5 text-xs font-semibold text-slate-200">
          <Compass
            className="w-3.5 h-3.5 text-brand-500 animate-pulse"
            style={{ transform: `rotate(${heading}deg)` }}
          />
          <span>
            {heading}°{' '}
            {heading >= 337 || heading < 23
              ? 'N'
              : heading >= 23 && heading < 67
                ? 'NE'
                : heading >= 67 && heading < 112
                  ? 'E'
                  : heading >= 112 && heading < 157
                    ? 'SE'
                    : heading >= 157 && heading < 202
                      ? 'S'
                      : heading >= 202 && heading < 247
                        ? 'SW'
                        : heading >= 247 && heading < 292
                          ? 'W'
                          : 'NW'}
          </span>
        </div>

        {isMockMode && (
          <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-amber-500/10 border border-amber-500/20 text-xs font-medium text-amber-300 backdrop-blur-md">
            <AlertTriangle className="w-3.5 h-3.5" />
            <span>Mock Mode</span>
          </div>
        )}
      </div>

      {isMockMode && (
        <div className="absolute inset-x-0 bottom-4 flex justify-center pointer-events-none transition-opacity duration-300 opacity-80 group-hover:opacity-0">
          <div className="flex items-center gap-2 px-4 py-2 rounded-xl bg-bgDark-950/90 backdrop-blur-md border border-white/5 text-xs text-slate-300">
            <Move className="w-4 h-4 text-brand-500 animate-bounce" />
            <span>Drag mouse horizontally to look around</span>
            <button
              onClick={(e) => {
                e.stopPropagation();
                resetMockScroll();
              }}
              className="pointer-events-auto ml-2 p-1 hover:bg-white/10 rounded-md transition-colors"
              title="Reset View"
            >
              <RotateCcw className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
