import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { firstValueFrom } from 'rxjs';

import { AuthService } from './auth';
import { Course, Enrollment, Lesson, Paginated, Quiz, QuizQuestion } from './models';

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

  deleteQuiz(id: number): Promise<void> {
    return firstValueFrom(this.http.delete<void>(`/api/v1/quizzes/${id}/`));
  }

  createQuestion(data: Partial<QuizQuestion>): Promise<QuizQuestion> {
    return firstValueFrom(this.http.post<QuizQuestion>('/api/v1/questions/', data));
  }

  deleteQuestion(id: number): Promise<void> {
    return firstValueFrom(this.http.delete<void>(`/api/v1/questions/${id}/`));
  }
}
