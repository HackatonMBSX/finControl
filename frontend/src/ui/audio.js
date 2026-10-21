/* Alertas sonoros (Web Audio API). */
import { DB, state } from '../data/store.js';
import { contarAlertas } from '../domain/calc.js';

let audioCtx = null;

export function getCtx() {
  if (!audioCtx) {
    try { audioCtx = new (window.AudioContext || window.webkitAudioContext)(); } catch (e) { }
  }
  return audioCtx;
}

export function playTone(freq, type, dur, vol, delay) {
  const ctx = getCtx(); if (!ctx) return;
  try {
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.connect(gain); gain.connect(ctx.destination);
    osc.type = type || 'sine';
    osc.frequency.value = freq;
    const t0 = ctx.currentTime + (delay || 0);
    gain.gain.setValueAtTime(0, t0);
    gain.gain.linearRampToValueAtTime(vol || 0.12, t0 + 0.02);
    gain.gain.exponentialRampToValueAtTime(0.001, t0 + dur);
    osc.start(t0); osc.stop(t0 + dur + 0.02);
  } catch (e) { }
}

export function playAlert(type) {
  if (!state.som || !DB.config.somAtivo) return;
  if (type === 'critical') {
    // três bipes urgentes
    playTone(1046, 'square', 0.18, 0.14, 0);
    playTone(880, 'square', 0.18, 0.14, 0.22);
    playTone(1046, 'square', 0.22, 0.16, 0.44);
  } else if (type === 'warning') {
    playTone(784, 'sine', 0.28, 0.11, 0);
    playTone(659, 'sine', 0.30, 0.11, 0.32);
  } else if (type === 'success') {
    playTone(659, 'sine', 0.15, 0.10, 0);
    playTone(988, 'sine', 0.22, 0.10, 0.16);
  } else {
    playTone(587, 'sine', 0.20, 0.09, 0);
  }
}

export function dispararAlertaSonoro() {
  if (state.alertaTocado) return;
  const a = contarAlertas();
  if (a.atrasadas > 0) { playAlert('critical'); state.alertaTocado = true; }
  else if (a.venceHoje > 0) { playAlert('warning'); state.alertaTocado = true; }
}
