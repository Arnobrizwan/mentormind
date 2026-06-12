import { DestroyRef, Directive, ElementRef, effect, inject, input } from '@angular/core';

/** True when the user has asked the OS to minimise motion. */
export function prefersReducedMotion(): boolean {
  return (
    typeof matchMedia !== 'undefined' && matchMedia('(prefers-reduced-motion: reduce)').matches
  );
}

/**
 * Entrance-stagger delay for the nth item of a list: `step` ms per index,
 * capped so long lists don't keep the tail waiting (default ~10 items).
 */
export function staggerDelay(index: number, step = 50, capItems = 10): number {
  return Math.min(index, capItems) * step;
}

/**
 * Counts the element's text up from 0 to the bound value on first render
 * (~700ms, ease-out, requestAnimationFrame). Later value changes — and
 * reduced-motion users — jump straight to the final number.
 *
 * Usage: `<span [stCountUp]="42"></span>`
 */
@Directive({ selector: '[stCountUp]' })
export class CountUp {
  private readonly el = inject<ElementRef<HTMLElement>>(ElementRef);
  private frame = 0;
  private played = false;

  readonly stCountUp = input.required<number>();

  constructor() {
    inject(DestroyRef).onDestroy(() => cancelAnimationFrame(this.frame));

    effect(() => {
      const target = this.stCountUp();
      cancelAnimationFrame(this.frame);

      if (this.played || prefersReducedMotion() || !Number.isFinite(target)) {
        this.render(target);
        return;
      }

      this.played = true;
      const duration = 700;
      const start = performance.now();
      const tick = (now: number): void => {
        const t = Math.min(1, (now - start) / duration);
        const eased = 1 - Math.pow(1 - t, 3); // ease-out cubic
        this.render(target * eased);
        if (t < 1) this.frame = requestAnimationFrame(tick);
      };
      this.frame = requestAnimationFrame(tick);
    });
  }

  private render(value: number): void {
    this.el.nativeElement.textContent = String(Math.round(value));
  }
}
