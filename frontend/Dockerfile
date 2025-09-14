# Multi-stage Dockerfile for NoteMesh frontend

# Development stage
FROM nginx:1.24-alpine as development

# Copy frontend files
COPY . /usr/share/nginx/html

# Development nginx configuration will be mounted from docker-compose

# Create necessary directories
RUN mkdir -p /var/log/nginx

# Expose port
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost/health || exit 1

# Production stage
FROM nginx:1.24-alpine as production

# Copy frontend files
COPY . /usr/share/nginx/html

# Production nginx configuration will be mounted from docker-compose

# Set production permissions
RUN chown -R nginx:nginx /usr/share/nginx/html && \
    chmod -R 755 /usr/share/nginx/html

# Remove unnecessary files for production
RUN rm -rf /usr/share/nginx/html/Dockerfile /usr/share/nginx/html/README.md

# Create necessary directories
RUN mkdir -p /var/log/nginx && \
    chown nginx:nginx /var/log/nginx

# Health check
HEALTHCHECK --interval=60s --timeout=30s --start-period=30s --retries=3 \
    CMD curl -f http://localhost/health || exit 1

# Expose port
EXPOSE 80