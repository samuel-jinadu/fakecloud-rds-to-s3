FROM alpine:latest

RUN apk add --no-cache \
    bash \
    aws-cli \
    jq \
    postgresql-client \
    && rm -rf /var/cache/apk/*

WORKDIR /app

COPY ./ /app

# Make the script executable
RUN chmod +x /app/setup-rds-s3.sh

# Set the default command to run your script
# The script expects the env file as the first argument
ENTRYPOINT ["/app/setup-rds-s3.sh"]