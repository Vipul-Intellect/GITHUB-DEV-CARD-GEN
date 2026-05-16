FROM nginx:alpine

# Copy the frontend file
COPY index.html /usr/share/nginx/html/index.html.template

# Install envsubst (comes with gettext in alpine)
RUN apk add --no-cache gettext

# Create a startup script to replace the environment variable
RUN echo '#!/bin/sh' > /docker-entrypoint.d/40-subst-env.sh && \
    echo 'envsubst "\$BACKEND_URL" < /usr/share/nginx/html/index.html.template > /usr/share/nginx/html/index.html' >> /docker-entrypoint.d/40-subst-env.sh && \
    chmod +x /docker-entrypoint.d/40-subst-env.sh

EXPOSE 80
