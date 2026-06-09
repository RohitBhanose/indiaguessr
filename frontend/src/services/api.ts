import type { GameSession, GuessResponse, GameResults } from '../types';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8001/api/v1';

export const api = {
  /**
   * Start a new game session
   */
  async startGame(mode: 'india' | 'world'): Promise<GameSession> {
    const res = await fetch(`${API_BASE_URL}/api/v1/games`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ mode }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to start game');
    }
    return res.json();
  },

  /**
   * Submit the guessed coordinates for the active round
   */
  async submitGuess(gameId: string, latitude: number, longitude: number): Promise<GuessResponse> {
    const res = await fetch(`${API_BASE_URL}/games/${gameId}/guess`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ latitude, longitude }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to submit guess');
    }
    return res.json();
  },

  /**
   * Advance to the next round in the session
   */
  async nextRound(gameId: string): Promise<GameSession> {
    const res = await fetch(`${API_BASE_URL}/games/${gameId}/next`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to load next round');
    }
    return res.json();
  },

  /**
   * Retrieve final game breakdown and total score
   */
  async getResults(gameId: string): Promise<GameResults> {
    const res = await fetch(`${API_BASE_URL}/games/${gameId}/results`);
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to fetch game results');
    }
    return res.json();
  },

  /**
   * Update the active round's actual coordinates when Street View is auto-replaced
   */
  async updateRoundLocation(gameId: string, latitude: number, longitude: number): Promise<GameSession> {
    const res = await fetch(`${API_BASE_URL}/games/${gameId}/round/location`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ latitude, longitude }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to update round location');
    }
    return res.json();
  },
};

