export interface User {
  id: number;
  email: string;
  display_name: string;
  avatar_url: string;
  roles: string[];
  date_joined: string;
}

export interface Lesson {
  id: number;
  course: number;
  title: string;
  content: string;
  video_url: string | null;
  order: number;
  is_published: boolean;
  created_at: string;
  updated_at: string;
}

export interface QuizQuestion {
  id: number;
  quiz: number;
  text: string;
  options: string[];
  order: number;
  /** Only present for instructors/staff — the API strips it for students. */
  correct_option_index?: number;
}

export interface Quiz {
  id: number;
  course: number;
  lesson: number | null;
  title: string;
  description: string;
  /** Minutes allowed for the attempt — null/absent means untimed. */
  time_limit_minutes?: number | null;
  questions: QuizQuestion[];
  created_at: string;
  updated_at: string;
}

export interface Course {
  id: number;
  title: string;
  slug: string;
  description: string;
  instructor: number;
  instructor_name: string;
  is_published: boolean;
  lessons: Lesson[];
  quizzes: Quiz[];
  created_at: string;
  updated_at: string;
}

/** Per-question outcome on a graded attempt — never reveals the right answer. */
export interface QuizAttemptAnswer {
  selected: number | null;
  correct: boolean;
  topic: string;
}

export interface QuizAttempt {
  id: number;
  enrollment: number;
  quiz: number;
  quiz_title: string;
  score: number;
  total_questions: number;
  correct_answers: number;
  completed_at: string;
  /** Keyed by question id; present on fresh submit responses. */
  answers?: Record<number, QuizAttemptAnswer>;
}

export interface Enrollment {
  id: number;
  student: number;
  student_email: string;
  student_name: string;
  course: number;
  course_title: string;
  enrolled_at: string;
  completed_lessons: number[];
  progress_percentage: number;
  quiz_attempts: QuizAttempt[];
}

export interface Paginated<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}
