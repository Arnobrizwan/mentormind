// k6 write-path scenario: the full student journey under concurrency.
// register -> login -> browse -> enroll -> read lesson -> submit quiz.
// Exercises JWT auth, the write DB, Celery notification fan-out and the
// leaderboard sorted set in one go.
//
//   k6 run student-journey.js
//   k6 run -e BASE_URL=https://... -e COURSE_SLUG=systems-design-101 student-journey.js
import http from 'k6/http';
import { check, sleep } from 'k6';

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8080';
const COURSE_SLUG = __ENV.COURSE_SLUG || 'systems-design-101';

export const options = {
  stages: [
    { duration: '20s', target: 10 },
    { duration: '1m', target: 40 },
    { duration: '20s', target: 0 },
  ],
  thresholds: {
    http_req_failed: ['rate<0.05'],
    http_req_duration: ['p(95)<1000'],
  },
};

const jsonHeaders = { 'Content-Type': 'application/json' };

export default function () {
  const email = `k6-${__VU}-${__ITER}-${Date.now()}@loadtest.dev`;
  const password = 'K6-load-test-pass!';

  const registered = http.post(
    `${BASE_URL}/api/v1/auth/register/`,
    JSON.stringify({ email, password, display_name: `VU ${__VU}` }),
    { headers: jsonHeaders },
  );
  check(registered, { 'registered 201': (r) => r.status === 201 });

  const login = http.post(
    `${BASE_URL}/api/v1/auth/token/`,
    JSON.stringify({ email, password }),
    { headers: jsonHeaders },
  );
  check(login, { 'login 200': (r) => r.status === 200 });
  const access = JSON.parse(login.body).access;
  const auth = { headers: { ...jsonHeaders, Authorization: `Bearer ${access}` } };

  const course = http.get(`${BASE_URL}/api/v1/courses/${COURSE_SLUG}/`, auth);
  if (
    !check(course, { 'course 200': (r) => r.status === 200 }) ||
    course.status !== 200
  ) {
    return; // seed course missing — skip the rest of the journey
  }
  const courseBody = JSON.parse(course.body);

  const enrolled = http.post(`${BASE_URL}/api/v1/courses/${COURSE_SLUG}/enroll/`, '{}', auth);
  check(enrolled, { 'enrolled 200/201': (r) => r.status === 200 || r.status === 201 });

  sleep(1); // "reading the lesson"

  const quiz = courseBody.quizzes && courseBody.quizzes[0];
  if (quiz && quiz.questions.length > 0) {
    const answers = {};
    for (const q of quiz.questions) {
      answers[q.id] = Math.floor(Math.random() * q.options.length);
    }
    const submitted = http.post(
      `${BASE_URL}/api/v1/quizzes/${quiz.id}/submit/`,
      JSON.stringify({ answers }),
      auth,
    );
    check(submitted, { 'quiz graded 201': (r) => r.status === 201 });

    const leaderboard = http.get(`${BASE_URL}/api/v1/courses/${COURSE_SLUG}/leaderboard/`);
    check(leaderboard, { 'leaderboard 200': (r) => r.status === 200 });
  }

  sleep(Math.random());
}
