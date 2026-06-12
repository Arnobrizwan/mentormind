export interface User {
  id: number;
  email: string;
  display_name: string;
  avatar_url: string;
  roles: string[];
  is_staff: boolean;
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
}

export interface QuizQuestion {
  id: number;
  quiz: number;
  text: string;
  options: string[];
  topic?: string;
  order: number;
  correct_option_index?: number;
}

export interface Quiz {
  id: number;
  course: number;
  lesson: number | null;
  title: string;
  description: string;
  /** Minutes students get for an attempt — null means untimed. */
  time_limit_minutes?: number | null;
  questions: QuizQuestion[];
}

export interface Course {
  id: number;
  title: string;
  slug: string;
  description: string;
  instructor: number;
  instructor_name: string;
  cover_image: string | null;
  is_published: boolean;
  lessons: Lesson[];
  quizzes: Quiz[];
  created_at: string;
}

export interface QuizAttempt {
  id: number;
  quiz: number;
  quiz_title: string;
  score: number;
  total_questions: number;
  correct_answers: number;
  completed_at: string;
}

export interface Enrollment {
  id: number;
  student: number;
  student_email: string;
  student_name: string;
  course: number;
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

export interface ShortAnswerQuestion {
  id: number;
  course: number;
  lesson: number | null;
  prompt: string;
  topic?: string;
  mark_scheme: string;
  max_score: number;
  is_published: boolean;
  order: number;
  created_at: string;
  updated_at: string;
}

export interface ShortAnswerSubmission {
  id: number;
  question: number;
  enrollment: number;
  student_email: string;
  student_name: string;
  answer_text: string;
  score: number;
  max_score: number;
  criteria_met: string[];
  criteria_missing: string[];
  feedback: string;
  engine: 'llm' | 'heuristic';
  created_at: string;
}

export type ProctorVerdict = 'ok' | 'no_face' | 'multiple_faces';

export interface ProctorLog {
  id: number;
  faces: number;
  verdict: ProctorVerdict;
  created_at: string;
}

export interface ProctorSession {
  enrollment: number;
  student_email: string;
  student_name: string;
  violations: number;
  logs: ProctorLog[];
}

export type RiskLevel = 'high' | 'medium';
export type RiskTicketStatus = 'open' | 'contacted' | 'resolved';

export interface RiskFeatures {
  progress_pct: number;
  days_since_last_login: number;
  quiz_avg: number;
  lessons_per_week: number;
  chat_messages: number;
}

export interface RiskTicket {
  id: number;
  student: number;
  student_email: string;
  student_name: string;
  risk: RiskLevel;
  probability: number;
  features: RiskFeatures;
  status: RiskTicketStatus;
  note: string;
  created_at: string;
  updated_at: string;
}

export interface RiskScanQueued {
  queued: boolean;
  task_id: string;
}

export type FlashcardSource = 'llm' | 'heuristic' | 'instructor';

export interface Flashcard {
  id: number;
  course: number;
  course_title: string;
  lesson: number | null;
  topic: string;
  front: string;
  back: string;
  source: FlashcardSource;
  is_published: boolean;
  created_at: string;
  updated_at: string;
}

/** Async generation acknowledgement (202) from /revision/generate/. */
export interface GenerationQueued {
  queued: boolean;
  task_id: string;
}

export interface QuizDraftQuestion {
  text: string;
  options: string[];
  correct_option_index: number;
}

/** Synchronous AI quiz draft from /quizzes/generate-draft/ — nothing is persisted. */
export interface QuizDraft {
  lesson: number;
  course: number;
  suggested_title: string;
  questions: QuizDraftQuestion[];
  engine: 'llm' | 'heuristic';
}

export interface ReadinessComponents {
  progress_pct: number;
  quiz_avg: number;
  practice_volume: number;
  accuracy: number;
}

/** Per-student exam readiness (0-100), sorted weakest-first by the API. */
export interface ReadinessRow {
  enrollment: number;
  student_email: string;
  student_name: string;
  readiness: number;
  components: ReadinessComponents;
}
