// k6 read-path load test: hammer the public catalog through the nginx LB.
// Shows off the full caching stack — nginx micro-cache absorbs most of it,
// Redis cache-aside covers the misses, Django only sees the trickle.
//
//   k6 run catalog-read.js                    # local compose (port 8080)
//   k6 run -e BASE_URL=https://... catalog-read.js
import http from 'k6/http';
import { check, sleep } from 'k6';
import { Counter } from 'k6/metrics';

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8080';

const servedBy = new Counter('served_by_instances');

export const options = {
  stages: [
    { duration: '30s', target: 50 },   // ramp up
    { duration: '1m', target: 200 },   // sustained read load
    { duration: '30s', target: 500 },  // spike
    { duration: '30s', target: 0 },    // drain
  ],
  thresholds: {
    http_req_failed: ['rate<0.01'],
    http_req_duration: ['p(95)<300', 'p(99)<800'],
  },
};

export default function () {
  const catalog = http.get(`${BASE_URL}/api/v1/courses/`);
  check(catalog, {
    'catalog 200': (r) => r.status === 200,
    'catalog has results': (r) => JSON.parse(r.body).results !== undefined,
  });
  if (catalog.headers['X-Served-By']) {
    servedBy.add(1, { instance: catalog.headers['X-Served-By'] });
  }

  const health = http.get(`${BASE_URL}/api/v1/health/`);
  check(health, { 'health 200': (r) => r.status === 200 });

  sleep(Math.random() * 2);
}
