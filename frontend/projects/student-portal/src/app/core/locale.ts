import { Injectable, computed, signal } from '@angular/core';

export type LocaleId = 'en' | 'ms';

const STORAGE_KEY = 'mm_locale';

/** UI strings — English + Bahasa Malaysia for DIGITEX / local students. */
const MESSAGES: Record<LocaleId, Record<string, string>> = {
  en: {
    'nav.catalog': 'Catalog',
    'nav.desk': 'My Desk',
    'nav.tutor': 'AI Tutor',
    'nav.revision': 'Revision',
    'nav.planner': 'Planner',
    'nav.profile': 'Profile',
    'nav.alerts': 'Alerts',
    'nav.signIn': 'Sign in',
    'nav.signOut': 'Sign out',
    'offline.banner':
      "You're offline — cached catalog and enrollments still work; chat and quizzes need a connection.",
    'catalog.hero.label': 'Vol. 1 — The Course Catalog',
    'catalog.hero.line1': 'Field notes for the',
    'catalog.hero.line2': 'endlessly curious.',
    'catalog.hero.sub':
      'Every course is a working notebook — lessons, quizzes, and a mentor who has actually done the thing. Pick one up and start scribbling.',
    'profile.language': 'Language',
    'profile.language.hint': 'Bahasa Malaysia for menus and banners. Tutor answers stay in English unless you ask in Malay.',
    'profile.language.en': 'English',
    'profile.language.ms': 'Bahasa Malaysia',
    'tutor.voiceMode': 'Voice tutor — dictate questions and listen to answers',
    'tutor.placeholder': 'Ask your tutor…',
    'tutor.snap': 'Snap',
    'chat.placeholder': 'Message the room…',
    'chat.send': 'Send',
  },
  ms: {
    'nav.catalog': 'Katalog',
    'nav.desk': 'Meja Saya',
    'nav.tutor': 'Tutor AI',
    'nav.revision': 'Ulang Kaji',
    'nav.planner': 'Perancang',
    'nav.profile': 'Profil',
    'nav.alerts': 'Makluman',
    'nav.signIn': 'Log masuk',
    'nav.signOut': 'Log keluar',
    'offline.banner':
      'Anda luar talian — katalog dan pendaftaran cache masih berfungsi; sembang dan kuiz perlukan sambungan.',
    'catalog.hero.label': 'Jilid 1 — Katalog Kursus',
    'catalog.hero.line1': 'Nota lapangan untuk',
    'catalog.hero.line2': 'mereka yang ingin tahu.',
    'catalog.hero.sub':
      'Setiap kursus ialah buku nota — pelajaran, kuiz, dan mentor berpengalaman. Ambil satu dan mula belajar.',
    'profile.language': 'Bahasa',
    'profile.language.hint':
      'Bahasa Malaysia untuk menu. Jawapan tutor kekal dalam bahasa soalan anda.',
    'profile.language.en': 'English',
    'profile.language.ms': 'Bahasa Malaysia',
    'tutor.voiceMode': 'Tutor suara — sebut soalan dan dengar jawapan',
    'tutor.placeholder': 'Tanya tutor anda…',
    'tutor.snap': 'Snap',
    'chat.placeholder': 'Mesej ke bilik…',
    'chat.send': 'Hantar',
  },
};

/** BCP-47 tags for Web Speech API (dictation + read-aloud). */
const SPEECH_LANG: Record<LocaleId, string> = {
  en: 'en-MY',
  ms: 'ms-MY',
};

@Injectable({ providedIn: 'root' })
export class LocaleService {
  readonly id = signal<LocaleId>(readStored());

  readonly speechLang = computed(() => SPEECH_LANG[this.id()]);

  t(key: string): string {
    const lang = this.id();
    return MESSAGES[lang][key] ?? MESSAGES.en[key] ?? key;
  }

  setLocale(next: LocaleId): void {
    this.id.set(next);
    try {
      localStorage.setItem(STORAGE_KEY, next);
    } catch {
      // Private mode — in-memory only.
    }
    if (typeof document !== 'undefined') {
      document.documentElement.lang = next === 'ms' ? 'ms' : 'en';
    }
  }
}

function readStored(): LocaleId {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw === 'ms' || raw === 'en') return raw;
  } catch {
    // ignore
  }
  return 'en';
}
