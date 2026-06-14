# Generic builder for a secondary Angular app (instructor-studio / admin-console)
# served under a sub-path by Caddy. Parameterised by PROJECT + BASE_HREF.
#
#   build:
#     context: ../frontend
#     dockerfile: ../deploy/frontend-app.Dockerfile
#     args: { PROJECT: instructor-studio, BASE_HREF: /studio/ }
#
# The SPA uses same-origin /api (root-relative), so Caddy's /api route reaches
# the backend regardless of base-href. handle_path strips the prefix, so nginx
# serves from / with try_files → index.html (which carries the base-href).
FROM node:24-alpine AS build
ARG PROJECT
ARG BASE_HREF=/
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npx ng build ${PROJECT} --configuration production --base-href ${BASE_HREF}
RUN cp -r dist/${PROJECT}/browser /site

FROM nginx:1.27-alpine
COPY --from=build /site /usr/share/nginx/html
RUN printf 'server {\n  listen 80;\n  root /usr/share/nginx/html;\n  location / { try_files $uri /index.html; }\n}\n' > /etc/nginx/conf.d/default.conf
EXPOSE 80
