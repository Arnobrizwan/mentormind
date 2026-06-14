# Builds the student-portal SPA and serves it with nginx. Caddy routes the
# domain: /api, /admin, /static, /media, /ws, /metrics -> Django backend;
# everything else -> this SPA. The SPA uses same-origin /api (no API-base
# injection needed), since Caddy serves UI and API on one domain.
#
# Build context is the repo's frontend/ directory:
#   build:
#     context: ../frontend
#     dockerfile: ../deploy/frontend.Dockerfile
FROM node:24-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npx ng build student-portal --configuration production

FROM nginx:1.27-alpine
COPY --from=build /app/dist/student-portal/browser /usr/share/nginx/html
RUN printf 'server {\n  listen 80;\n  root /usr/share/nginx/html;\n  location / { try_files $uri /index.html; }\n}\n' > /etc/nginx/conf.d/default.conf
EXPOSE 80
