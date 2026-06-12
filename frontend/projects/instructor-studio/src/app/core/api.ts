import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { firstValueFrom } from 'rxjs';

import { AuthService } from './auth';
import {
  Course,
  Enrollment,
  Flashcard,
  GenerationQueued,
  Lesson,
  Paginated,
  ProctorSession,
  Quiz,
  QuizDraft,
  QuizQuestion,
  ReadinessRow,
  RiskScanQueued,
  RiskTicket,
  RiskTicketStatus,
  ShortAnswerQuestion,
  ShortAnswerSubmission,
} from './models';

@Injectable({ providedIn: 'root' })
export class StudioApi {
  private readonly http = inject(HttpClient);
  private readonly auth = inject(AuthService);

  /** Courses taught by the signed-in instructor (drafts included). */
  async myCourses(): Promise<Course[]> {
    const me = this.auth.user();
    const page = await firstValueFrom(
      this.http.get<Paginated<Course>>('/api/v1/courses/', { params: { page_size: 100 } }),
    );
    return page.results.filter((c) => c.instructor === me?.id || this.auth.user()?.is_staff);
  }

  getCourse(slug: string): Promise<Course> {
    return firstValueFrom(this.http.get<Course>(`/api/v1/courses/${slug}/`));
  }

  createCourse(data: Partial<Course>): Promise<Course> {
    return firstValueFrom(this.http.post<Course>('/api/v1/courses/', data));
  }

  updateCourse(slug: string, data: Partial<Course>): Promise<Course> {
    return firstValueFrom(this.http.patch<Course>(`/api/v1/courses/${slug}/`, data));
  }

  students(slug: string): Promise<Enrollment[]> {
    return firstValueFrom(this.http.get<Enrollment[]>(`/api/v1/courses/${slug}/students/`));
  }

  /** Per-student exam readiness for a course, sorted weakest-first. */
  readiness(slug: string): Promise<ReadinessRow[]> {
    return firstValueFrom(this.http.get<ReadinessRow[]>(`/api/v1/courses/${slug}/readiness/`));
  }

  createLesson(data: Partial<Lesson>): Promise<Lesson> {
    return firstValueFrom(this.http.post<Lesson>('/api/v1/lessons/', data));
  }

  updateLesson(id: number, data: Partial<Lesson>): Promise<Lesson> {
    return firstValueFrom(this.http.patch<Lesson>(`/api/v1/lessons/${id}/`, data));
  }

  deleteLesson(id: number): Promise<void> {
    return firstValueFrom(this.http.delete<void>(`/api/v1/lessons/${id}/`));
  }

  createQuiz(data: Partial<Quiz>): Promise<Quiz> {
    return firstValueFrom(this.http.post<Quiz>('/api/v1/quizzes/', data));
  }

  updateQuiz(id: number, data: Partial<Quiz>): Promise<Quiz> {
    return firstValueFrom(this.http.patch<Quiz>(`/api/v1/quizzes/${id}/`, data));
  }

  deleteQuiz(id: number): Promise<void> {
    return firstValueFrom(this.http.delete<void>(`/api/v1/quizzes/${id}/`));
  }

  createQuestion(data: Partial<QuizQuestion>): Promise<QuizQuestion> {
    return firstValueFrom(this.http.post<QuizQuestion>('/api/v1/questions/', data));
  }

  deleteQuestion(id: number): Promise<void> {
    return firstValueFrom(this.http.delete<void>(`/api/v1/questions/${id}/`));
  }

  /** Synchronously draft quiz questions from a lesson — may take up to ~90s. */
  generateQuizDraft(lessonId: number): Promise<QuizDraft> {
    return firstValueFrom(
      this.http.post<QuizDraft>('/api/v1/quizzes/generate-draft/', { lesson: lessonId }),
    );
  }

  /** Flashcards for a course (drafts and published). */
  async flashcards(courseId: number): Promise<Flashcard[]> {
    const page = await firstValueFrom(
      this.http.get<Paginated<Flashcard>>('/api/v1/revision/flashcards/', {
        params: { course: courseId, page_size: 100 },
      }),
    );
    return page.results;
  }

  createFlashcard(data: Partial<Flashcard>): Promise<Flashcard> {
    return firstValueFrom(this.http.post<Flashcard>('/api/v1/revision/flashcards/', data));
  }

  updateFlashcard(id: number, data: Partial<Flashcard>): Promise<Flashcard> {
    return firstValueFrom(this.http.patch<Flashcard>(`/api/v1/revision/flashcards/${id}/`, data));
  }

  deleteFlashcard(id: number): Promise<void> {
    return firstValueFrom(this.http.delete<void>(`/api/v1/revision/flashcards/${id}/`));
  }

  /** Queue async AI flashcard generation for a lesson; drafts arrive unpublished. */
  generateFlashcards(lessonId: number): Promise<GenerationQueued> {
    return firstValueFrom(
      this.http.post<GenerationQueued>('/api/v1/revision/generate/', { lesson: lessonId }),
    );
  }

  /** Short-answer questions for a course (mark schemes included for own courses). */
  async shortAnswers(courseId: number): Promise<ShortAnswerQuestion[]> {
    const page = await firstValueFrom(
      this.http.get<Paginated<ShortAnswerQuestion>>('/api/v1/short-answers/', {
        params: { course: courseId, page_size: 100 },
      }),
    );
    return page.results;
  }

  createShortAnswer(data: Partial<ShortAnswerQuestion>): Promise<ShortAnswerQuestion> {
    return firstValueFrom(this.http.post<ShortAnswerQuestion>('/api/v1/short-answers/', data));
  }

  updateShortAnswer(id: number, data: Partial<ShortAnswerQuestion>): Promise<ShortAnswerQuestion> {
    return firstValueFrom(this.http.patch<ShortAnswerQuestion>(`/api/v1/short-answers/${id}/`, data));
  }

  deleteShortAnswer(id: number): Promise<void> {
    return firstValueFrom(this.http.delete<void>(`/api/v1/short-answers/${id}/`));
  }

  shortAnswerSubmissions(id: number): Promise<ShortAnswerSubmission[]> {
    return firstValueFrom(
      this.http.get<ShortAnswerSubmission[]>(`/api/v1/short-answers/${id}/submissions/`),
    );
  }

  /** Per-student proctoring sessions recorded during a quiz. */
  quizProctoring(quizId: number): Promise<ProctorSession[]> {
    return firstValueFrom(this.http.get<ProctorSession[]>(`/api/v1/quizzes/${quizId}/proctoring/`));
  }

  /** Dropout-risk remediation tickets, optionally filtered by status. */
  riskTickets(status?: RiskTicketStatus): Promise<Paginated<RiskTicket>> {
    const params: Record<string, string | number> = { page_size: 100 };
    if (status) params['status'] = status;
    return firstValueFrom(
      this.http.get<Paginated<RiskTicket>>('/api/v1/engagement/risk/tickets/', { params }),
    );
  }

  updateRiskTicket(id: number, data: Partial<Pick<RiskTicket, 'status' | 'note'>>): Promise<RiskTicket> {
    return firstValueFrom(
      this.http.patch<RiskTicket>(`/api/v1/engagement/risk/tickets/${id}/`, data),
    );
  }

  triggerRiskScan(): Promise<RiskScanQueued> {
    return firstValueFrom(
      this.http.post<RiskScanQueued>('/api/v1/engagement/risk/tickets/scan/', {}),
    );
  }
}
