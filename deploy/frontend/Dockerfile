FROM node:20-alpine AS build
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM nginx:1.27-alpine
# openssl: generate the bootstrap self-signed cert so :443 can start before the
# API publishes the UI-managed certificate.
RUN apk add --no-cache openssl
COPY deploy/frontend/nginx.conf /etc/nginx/conf.d/default.conf
COPY deploy/frontend/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
COPY --from=build /build/dist /usr/share/nginx/html
EXPOSE 80 443
ENTRYPOINT ["/entrypoint.sh"]
