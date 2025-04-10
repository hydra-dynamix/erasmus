FROM python:3.10-slim

# Accept build arguments for user and group IDs
ARG USER_ID=1000
ARG GROUP_ID=1000

# Install basic dependencies
RUN apt-get update && apt-get install -y \
    curl \
    git \
    expect \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user with provided UID/GID
RUN groupadd -g $GROUP_ID appuser && \
    useradd -u $USER_ID -g $GROUP_ID -m appuser

# Set working directory and ensure correct permissions
WORKDIR /app
RUN chown -R appuser:appuser /app

# Copy installer script
COPY ../../release/v0.0.1/erasmus_v0.0.1.sh /app/erasmus.sh

# Make the installer executable and set permissions
RUN chmod +x /app/erasmus.sh && \
    chown appuser:appuser /app/erasmus.sh

# Set environment variables
ENV IDE_ENV=CURSOR
ENV OPENAI_API_KEY=sk-1234
ENV OPENAI_MODEL=gpt-4o
ENV OPENAI_URL=https://api.openai.com/v1

# Switch to the non-root user for installation and execution
USER appuser

# Create a .env.example file before running the installer
RUN touch /app/.env.example && \
    echo "IDE_ENV=" > /app/.env.example && \
    echo "GIT_TOKEN=" >> /app/.env.example && \
    echo "OPENAI_API_KEY=" >> /app/.env.example && \
    echo "OPENAI_BASE_URL=" >> /app/.env.example && \
    echo "OPENAI_MODEL=" >> /app/.env.example

# Create an expect script to automate the response to the hash verification prompt
RUN echo '#!/usr/bin/expect -f' > /app/run_installer.exp && \
    echo 'set timeout -1' >> /app/run_installer.exp && \
    echo 'spawn /bin/bash /app/erasmus.sh' >> /app/run_installer.exp && \
    echo 'expect "Do you want to continue anyway? (y/N)"' >> /app/run_installer.exp && \
    echo 'send "y\r"' >> /app/run_installer.exp && \
    echo 'expect eof' >> /app/run_installer.exp && \
    chmod +x /app/run_installer.exp

# Run the installer with expect to handle the prompt
RUN /usr/bin/expect -f /app/run_installer.exp

# Command to run when container starts
CMD ["uv", "run", "erasmus.py", "--watch"] 