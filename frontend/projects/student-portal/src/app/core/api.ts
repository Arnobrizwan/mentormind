import { HttpClient } from '@angular/common/http';
import { Injectable, inject, signal } from '@angular/core';
import { firstValueFrom } from 'rxjs';

import { AuthService } from './auth';
import { Course, Enrollment, Paginated, QuizAttempt } from './models';

@Injectable({ providedIn: 'root' })
export class LearningApi {
  private readonly http = inject(HttpClient);
  private readonly auth = inject(AuthService);

  /** The signed-in student's enrollments, kept fresh after every mutation. */
  readonly enrollments = signal<Enrollment[]>([]);

  listCourses(): Promise<Course[]> {
    return firstValueFrom(this.http.get<Paginated<Course>>('/api/v1/courses/')).then(
      (page) => page.results,
    );
  }

  getCourse(slug: string): Promise<Course> {
    return firstValueFrom(this.http.get<Course>(`/api/v1/courses/${slug}/`));
  }

  async enroll(slug: string): Promise<Enrollment> {
    const enrollment = await firstValueFrom(
      this.http.post<Enrollment>(`/api/v1/courses/${slug}/enroll/`, {}),
    );
    await this.refreshEnrollments();
    return enrollment;
  }

  async refreshEnrollments(): Promise<void> {
    if (!this.auth.isLoggedIn()) {
      this.enrollments.set([]);
      return;
    }
    const page = await firstValueFrom(
      this.http.get<Paginated<Enrollment>>('/api/v1/enrollments/'),
    );
    this.enrollments.set(page.results);
  }

  enrollmentFor(courseId: number): Enrollment | undefined {
    return this.enrollments().find((e) => e.course === courseId);
  }

  async completeLesson(enrollmentId: number, lessonId: number): Promise<Enrollment> {
    const updated = await firstValueFrom(
      this.http.post<Enrollment>(`/api/v1/enrollments/${enrollmentId}/complete-lesson/`, {
        lesson_id: lessonId,
      }),
    );
    this.enrollments.update((all) => all.map((e) => (e.id === updated.id ? updated : e)));
    return updated;
  }

  async submitQuiz(quizId: number, answers: Record<number, number>): Promise<QuizAttempt> {
    const attempt = await firstValueFrom(
      this.http.post<QuizAttempt>(`/api/v1/quizzes/${quizId}/submit/`, { answers }),
    );
    await this.refreshEnrollments();
    return attempt;
  }
}
