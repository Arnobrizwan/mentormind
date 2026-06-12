import { DestroyRef, Directive, ElementRef, effect, inject, input } from '@angular/core';

/**
 * Animates the host element's text content from its previously shown value
 * (0 on first render) up to the bound value over ~700ms with an ease-out
 * curve, via requestAnimationFrame.
 *
 * Under `prefers-reduced-motion: reduce` the value is set instantly.
 *
 * Usage: `<span [mmCountUp]="points()"></span>`
 */
@Directive({ selector: '[mmCountUp]' })
export class CountUpDirective {
  readonly mmCountUp = input.required<number>();

  private static readonly DURATION_MS = 700;

  private readonly el = inject<ElementRef<HTMLElement>>(ElementRef);
  private frame: number | null = null;
  /** Last value painted into the DOM — animations resume from here. */
  private shown = 0;

  constructor() {
    const reduceMotion =
      typeof window !== 'undefined' &&
      typeof window.matchMedia === 'function' &&
      window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    effect(() => {
      const target = this.mmCountUp();
      if (reduceMotion || !Number.isFinite(target)) {
        this.cancel();
        this.render(target);
        return;
      }
      this.animateTo(target);
    });

    inject(DestroyRef).onDestroy(() => this.cancel());
  }

  private animateTo(target: number): void {
    this.cancel();
    const from = this.shown;
    if (from === target) {
      this.render(target);
      return;
    }
    const start = performance.now();
    const tick = (now: number) => {
      const t = Math.min(1, (now - start) / CountUpDirective.DURATION_MS);
      const eased = 1 - Math.pow(1 - t, 3); // ease-out cubic
      this.render(Math.round(from + (target - from) * eased));
      this.frame = t < 1 ? requestAnimationFrame(tick) : null;
    };
    this.frame = requestAnimationFrame(tick);
  }

  private render(value: number): void {
    this.shown = value;
    this.el.nativeElement.textContent = String(value);
  }

  private cancel(): void {
    if (this.frame !== null) {
      cancelAnimationFrame(this.frame);
      this.frame = null;
    }
  }
}
