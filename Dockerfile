FROM python:3.12-slim

WORKDIR /workspace

RUN apt-get update && apt-get install -y \
    curl \
    git \
    bash \
    ca-certificates \
    procps \
    nodejs \
    npm \
    postgresql \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Chromium + its OS libs, so the Playwright end-to-end smoke test can run in-container.
# Deps are listed explicitly: playwright's --with-deps assumes Ubuntu and fails on
# Debian trixie (it looks for ttf-unifont / ttf-ubuntu-font-family, which don't exist here).
RUN apt-get update && apt-get install -y --no-install-recommends \
    libnss3 libnspr4 libatk1.0-0t64 libatk-bridge2.0-0t64 libcups2t64 libdrm2 \
    libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 libxrandr2 libgbm1 \
    libpango-1.0-0 libcairo2 libasound2t64 \
    && rm -rf /var/lib/apt/lists/* \
    && python -m playwright install chromium

# App/DB environment — Postgres runs in this same container, so these are
# fixed at build time rather than pulled from a .env file.
ENV DJANGO_ENV=development \
    SECRET_KEY=dev-insecure-secret-key-change-me \
    DB_NAME=sessionspyre \
    DB_USER=sessionspyre \
    DB_PASSWORD=sessionspyre \
    DB_HOST=localhost \
    DB_PORT=5432

# Install Claude Code
RUN npm install -g @anthropic-ai/claude-code

# Install ngrok
RUN curl -sSL https://ngrok-agent.s3.amazonaws.com/ngrok.asc \
    | tee /etc/apt/trusted.gpg.d/ngrok.asc >/dev/null \
    && echo "deb https://ngrok-agent.s3.amazonaws.com buster main" \
    | tee /etc/apt/sources.list.d/ngrok.list \
    && apt-get update && apt-get install -y ngrok \
    && rm -rf /var/lib/apt/lists/*

# Claude Code configuration: default settings + status line
RUN mkdir -p /root/.claude
COPY settings.json /root/.claude/settings.json
COPY statusline.sh /root/.claude/statusline.sh
RUN sed -i 's/\r$//' /root/.claude/statusline.sh && \
    chmod +x /root/.claude/statusline.sh

# Copy entrypoint script
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN sed -i 's/\r$//' /usr/local/bin/docker-entrypoint.sh && \
    chmod +x /usr/local/bin/docker-entrypoint.sh

# App code
COPY . .

# Student shell quality-of-life improvements
RUN echo 'export PS1="ai-course:\\w# "' >> /root/.bashrc && \
    echo 'alias ll="ls -alF"' >> /root/.bashrc && \
    echo 'alias la="ls -A"' >> /root/.bashrc && \
    echo 'alias l="ls -CF"' >> /root/.bashrc && \
    echo 'alias python="python3"' >> /root/.bashrc && \
    echo 'alias pip="pip3"' >> /root/.bashrc

EXPOSE 8000

ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "SessionSpyre.asgi:application"]
