export interface GameSession {
  game_id: string;
  mode: 'india' | 'world';
  current_round: number;
  streetview_lat: number;
  streetview_lng: number;
  panorama_id?: string | null;
}

export interface RoundResult {
  round_number: number;
  guessed_lat: number | null;
  guessed_lng: number | null;
  actual_lat: number;
  actual_lng: number;
  distance_km: number | null;
  score: number | null;
}

export interface GameResults {
  game_id: string;
  mode: 'india' | 'world';
  total_score: number;
  average_distance_km: number;
  rounds: RoundResult[];
}

export interface GuessResponse {
  round_number: number;
  guessed_lat: number;
  guessed_lng: number;
  actual_lat: number;
  actual_lng: number;
  distance_km: number;
  score: number;
  is_game_completed: boolean;
}
