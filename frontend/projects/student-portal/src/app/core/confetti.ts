import { Component, DestroyRef, inject, signal } from '@angular/core';

/** Poster brand palette — magenta, purple, yellow, coral. */
const COLORS = ['#ff5ca3', '#7c3aed', '#ffd23f', '#fb7185', '#e84e92'];

interface Piece {
  tx: string;
  ty: string;
  rot: string;
  color: string;
  delay: string;
  round: boolean;
}

/**
 * Lightweight CSS-only celebration burst: a ring of small confetti pieces
 * flies outward from the center of the host (~900ms) and is then removed
 * from the DOM. Position the parent `relative`; the burst is purely
 * decorative (`aria-hidden`) and never intercepts pointer events.
 *
 * Under `prefers-reduced-motion: reduce` nothing is shown.
 *
 * Usage: `<mm-confetti />` inside a relatively-positioned element.
 */
@Component({
  selector: 'mm-confetti',
  host: { 'aria-hidden': 'true' },
  template: `
    @if (active()) {
      @for (p of pieces; track $index) {
        <span
          class="piece"
          [class.piece--round]="p.round"
          [style.--tx]="p.tx"
          [style.--ty]="p.ty"
          [style.--rot]="p.rot"
          [style.background]="p.color"
          [style.animation-delay]="p.delay"
        ></span>
      }
    }
  `,
  styles: `
    :host {
      position: absolute;
      inset: 0;
      pointer-events: none;
      overflow: visible;
    }

    .piece {
      position: absolute;
      top: 50%;
      left: 50%;
      width: 7px;
      height: 11px;
      border-radius: 2px;
      opacity: 0;
      animation: confetti-fly 900ms cubic-bezier(0.16, 1, 0.3, 1) forwards;
      will-change: transform, opacity;
    }

    .piece--round {
      width: 8px;
      height: 8px;
      border-radius: 50%;
    }

    @keyframes confetti-fly {
      0% {
        opacity: 1;
        transform: translate(-50%, -50%) scale(0.3) rotate(0deg);
      }
      70% {
        opacity: 1;
      }
      100% {
        opacity: 0;
        transform: translate(calc(-50% + var(--tx)), calc(-50% + var(--ty))) scale(1)
          rotate(var(--rot));
      }
    }

    @media (prefers-reduced-motion: reduce) {
      .piece {
        display: none;
      }
    }
  `,
})
export class ConfettiBurst {
  protected readonly active = signal(true);

  /** Deterministic spread — no randomness, so SSR/tests stay stable. */
  protected readonly pieces: Piece[] = Array.from({ length: 14 }, (_, i) => {
    const angle = (i / 14) * Math.PI * 2 + (i % 3) * 0.12;
    const dist = 58 + (i % 4) * 16;
    return {
      tx: `${Math.round(Math.cos(angle) * dist)}px`,
      ty: `${Math.round(Math.sin(angle) * dist * 0.85)}px`,
      rot: `${120 + (i % 5) * 60}deg`,
      color: COLORS[i % COLORS.length],
      delay: `${(i % 4) * 30}ms`,
      round: i % 3 === 0,
    };
  });

  constructor() {
    // Pieces finish at opacity 0 — drop them from the DOM once done.
    const timer = setTimeout(() => this.active.set(false), 1100);
    inject(DestroyRef).onDestroy(() => clearTimeout(timer));
  }
}
