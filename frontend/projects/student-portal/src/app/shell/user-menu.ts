import {
  Component,
  ElementRef,
  computed,
  effect,
  inject,
  output,
  signal,
  viewChild,
} from '@angular/core';
import { RouterLink } from '@angular/router';

import { AuthService } from '../core/auth';
import { User } from '../core/models';

/** The API may include a premium flag the base model doesn't declare yet. */
type MaybePremiumUser = User & { is_premium?: boolean };

@Component({
  selector: 'mm-user-menu',
  imports: [RouterLink],
  host: {
    '(document:click)': 'onDocumentClick($event)',
    '(document:keydown.escape)': 'onEscape()',
  },
  template: `
    <button
      #trigger
      type="button"
      class="avatar"
      (click)="toggle()"
      aria-haspopup="menu"
      aria-controls="user-menu-panel"
      [attr.aria-expanded]="open()"
      [attr.aria-label]="'Account menu — ' + name()"
    >
      @if (avatarUrl()) {
        <img class="avatar__img" [src]="avatarUrl()" alt="" />
      } @else {
        <span class="avatar__letter" aria-hidden="true">{{ initial() }}</span>
      }
    </button>

    @if (open()) {
      <div
        class="menu"
        id="user-menu-panel"
        role="menu"
        aria-label="Account"
        (keydown)="onMenuKeydown($event)"
      >
        <div class="menu__id">
          <span class="menu__name">{{ name() }}</span>
          @if (isPremium()) {
            <span class="stamp menu__premium">Premium</span>
          }
        </div>
        <a #firstItem routerLink="/profile" role="menuitem" class="menu__item" (click)="close()">
          Profile
        </a>
        <button
          type="button"
          role="menuitem"
          class="menu__item menu__item--danger"
          (click)="onSignOut()"
        >
          Sign out
        </button>
      </div>
    }
  `,
  styles: `
    :host {
      position: relative;
      display: inline-flex;
    }

    .avatar {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 38px;
      height: 38px;
      padding: 0;
      overflow: hidden;
      border: 1.5px solid var(--line-strong);
      border-radius: 50%;
      background: var(--grad-btn);
      cursor: pointer;

      &:hover {
        border-color: var(--accent);
        box-shadow: var(--glow);
      }
    }

    .avatar__img {
      width: 100%;
      height: 100%;
      object-fit: cover;
    }

    .avatar__letter {
      color: #fff;
      font-family: var(--font-display);
      font-size: 0.95rem;
      font-weight: 700;
      line-height: 1;
    }

    .menu {
      position: absolute;
      top: calc(100% + 10px);
      right: 0;
      z-index: 70;
      min-width: 200px;
      overflow: hidden;
      border: 1.5px solid var(--line-strong);
      border-radius: 16px;
      background: var(--card);
      box-shadow: var(--shadow-lift);
      animation: menu-in 160ms var(--ease) both;
    }

    @keyframes menu-in {
      from {
        opacity: 0;
        transform: translateY(-6px);
      }
      to {
        opacity: 1;
        transform: translateY(0);
      }
    }

    .menu__id {
      display: flex;
      flex-direction: column;
      align-items: flex-start;
      gap: 0.35rem;
      padding: 0.8rem 1rem 0.65rem;
      border-bottom: 1px solid var(--line);
    }

    .menu__name {
      max-width: 220px;
      overflow: hidden;
      font-size: 0.88rem;
      font-weight: 700;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .menu__premium {
      font-size: 0.56rem;
      padding: 0.2rem 0.6rem;
    }

    .menu__item {
      display: block;
      width: 100%;
      padding: 0.62rem 1rem;
      border: 0;
      background: none;
      color: var(--ink);
      font-family: var(--font-body);
      font-size: 0.9rem;
      font-weight: 600;
      text-align: left;
      text-decoration: none;
      cursor: pointer;

      &:hover {
        background: color-mix(in srgb, var(--accent) 8%, transparent);
      }
    }

    .menu__item--danger {
      color: var(--danger);
      border-top: 1px solid var(--line);

      &:hover {
        background: color-mix(in srgb, var(--danger) 8%, transparent);
      }
    }

    @media (prefers-reduced-motion: reduce) {
      .menu {
        animation: none;
      }
    }
  `,
})
export class UserMenu {
  readonly signOut = output<void>();

  private readonly auth = inject(AuthService);
  private readonly host = inject<ElementRef<HTMLElement>>(ElementRef);

  private readonly trigger = viewChild.required<ElementRef<HTMLButtonElement>>('trigger');
  private readonly firstItem = viewChild<ElementRef<HTMLAnchorElement>>('firstItem');

  protected readonly open = signal(false);

  protected readonly name = computed(() => {
    const user = this.auth.user();
    return user ? user.display_name || user.email : '';
  });

  protected readonly initial = computed(() => (this.name().charAt(0) || '?').toUpperCase());

  protected readonly avatarUrl = computed(() => this.auth.user()?.avatar_url || null);

  protected readonly isPremium = computed(() =>
    Boolean((this.auth.user() as MaybePremiumUser | null)?.is_premium),
  );

  constructor() {
    // Move focus into the menu when it opens (the viewChild resolves after
    // the conditional content renders, re-running this effect).
    effect(() => {
      const item = this.firstItem();
      if (this.open() && item) {
        item.nativeElement.focus();
      }
    });
  }

  protected toggle(): void {
    this.open.update((v) => !v);
  }

  protected close(): void {
    this.open.set(false);
  }

  protected onEscape(): void {
    if (!this.open()) return;
    this.close();
    this.trigger().nativeElement.focus();
  }

  protected onDocumentClick(event: Event): void {
    if (this.open() && !this.host.nativeElement.contains(event.target as Node)) {
      this.close();
    }
  }

  protected onMenuKeydown(event: KeyboardEvent): void {
    if (event.key !== 'ArrowDown' && event.key !== 'ArrowUp') return;
    event.preventDefault();
    const items = Array.from(
      this.host.nativeElement.querySelectorAll<HTMLElement>('[role="menuitem"]'),
    );
    if (items.length === 0) return;
    const current = items.indexOf(document.activeElement as HTMLElement);
    const delta = event.key === 'ArrowDown' ? 1 : -1;
    const next = (current + delta + items.length) % items.length;
    items[next].focus();
  }

  protected onSignOut(): void {
    this.close();
    this.signOut.emit();
  }
}
