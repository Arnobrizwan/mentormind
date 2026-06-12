import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { firstValueFrom } from 'rxjs';

export interface SearchCourseHit {
  slug: string;
  title: string;
  instructor: string;
}

export interface SearchLessonHit {
  id: number;
  title: string;
  course_slug: string;
  course_title: string;
}

export interface SearchResults {
  query: string;
  courses: SearchCourseHit[];
  lessons: SearchLessonHit[];
}

/** Global site search (public endpoint — returns empty arrays under 2 chars). */
@Injectable({ providedIn: 'root' })
export class SearchApi {
  private readonly http = inject(HttpClient);

  search(query: string): Promise<SearchResults> {
    return firstValueFrom(
      this.http.get<SearchResults>('/api/v1/search/', { params: { q: query } }),
    );
  }
}
