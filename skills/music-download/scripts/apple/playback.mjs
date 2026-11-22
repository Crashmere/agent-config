// The controller owns recording and restoration; this monitor only evaluates observed Music state.
export class PlaybackMonitor {
  constructor({trackId, duration, probeSeconds, startupTimeout = 12, endTolerance = 1.5}) {
    if (!trackId || !(duration > 0)) throw new Error('Track identity and positive duration are required');
    Object.assign(this, {trackId, duration, probeSeconds, startupTimeout, endTolerance});
    this.started = false;
    this.latestPosition = 0;
  }

  update(current, elapsed) {
    if (!this.started) {
      if (current.state === 'playing' && current.track?.id !== this.trackId) {
        throw new Error('Music started an unexpected or unidentified song');
      }
      this.started = current.state === 'playing' && current.track?.id === this.trackId;
      if (!this.started) {
        if (elapsed > this.startupTimeout) throw new Error('Selected song did not begin');
        return {started: false, complete: false};
      }
      if (!Number.isFinite(current.track.position) || current.track.position > 1.5) {
        throw new Error('Selected song did not start at its beginning');
      }
    }
    if (current.track && current.track.id !== this.trackId) throw new Error('Music advanced to another song');
    if (current.state === 'playing' && (!current.track || !Number.isFinite(current.track.position))) {
      throw new Error('Playing song identity or position is unavailable');
    }
    this.latestPosition = Math.max(this.latestPosition, current.track?.position ?? 0);
    if (current.state !== 'playing') {
      if (this.latestPosition < this.duration - this.endTolerance) throw new Error('Music stopped before the song ended');
      // Music can clear currentTrack on normal stop; retain the last verified position.
      return {started: true, complete: true};
    }
    if (elapsed > this.startupTimeout + (this.probeSeconds ?? this.duration) + 10) {
      throw new Error('Playback exceeded its bound');
    }
    return {started: true, complete: this.probeSeconds !== undefined && this.latestPosition >= this.probeSeconds};
  }
}
