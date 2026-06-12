import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { firstValueFrom } from 'rxjs';

export interface PaperSubject {
  subject_code: string;
  questions: number;
}

export interface PaperQuestion {
  id: string;
  subject_code: string;
  year: number;
  session: string;
  variant: string;
  question_number: number;
  question_markdown: string;
  mark_scheme_markdown?: string;
}

export const SUBJECT_NAMES: Record<string, string> = {
  '0580': 'Mathematics',
  '0625': 'Physics',
  '0620': 'Chemistry',
  '0478': 'Computer Science',
  '0610': 'Biology',
  '0654': 'Combined Science',
};

export function subjectName(code: string): string {
  return SUBJECT_NAMES[code] ?? code;
}

/** Browse/sample the real Cambridge past-paper corpus (ml-service proxy). */
@Injectable({ providedIn: 'root' })
export class PastPapersApi {
  private readonly http = inject(HttpClient);

  subjects() {
    return firstValueFrom(
      this.http.get<{ subjects: PaperSubject[] }>('/api/v1/pastpapers/subjects/'),
    );
  }

  questions(subjectCode: string, page: number) {
    return firstValueFrom(
      this.http.get<{ count: number; page: number; results: PaperQuestion[] }>(
        `/api/v1/pastpapers/questions/?subject_code=${subjectCode}&page=${page}&page_size=1`,
      ),
    );
  }

  reveal(id: string) {
    return firstValueFrom(
      this.http.get<PaperQuestion>(`/api/v1/pastpapers/questions/${id}/`),
    );
  }

  sample(subjectCode: string, count: number) {
    return firstValueFrom(
      this.http.get<{ questions: PaperQuestion[] }>(
        `/api/v1/pastpapers/sample/?subject_code=${subjectCode}&count=${count}`,
      ),
    );
  }
}
