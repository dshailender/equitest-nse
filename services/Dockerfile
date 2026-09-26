# ====================================================================
# Multi-Stage Dockerfile for EquiTest Spring Boot Microservices
# Java 27 / Spring Boot 4.1.1
# ====================================================================

# Stage 1: Build & Package
FROM bellsoft/liberica-openjdk-alpine:27 AS builder

ARG SERVICE
WORKDIR /workspace

# Install Maven in alpine
RUN apk add --no-cache maven

# Copy POM files first for dependency caching
COPY pom.xml ./
COPY services/equitest-common/pom.xml services/equitest-common/pom.xml
COPY services/equitest-data-service/pom.xml services/equitest-data-service/pom.xml
COPY services/equitest-engine-service/pom.xml services/equitest-engine-service/pom.xml
COPY services/equitest-sweep-service/pom.xml services/equitest-sweep-service/pom.xml
COPY services/equitest-reports-service/pom.xml services/equitest-reports-service/pom.xml
COPY services/equitest-validation-service/pom.xml services/equitest-validation-service/pom.xml
COPY services/equitest-gateway/pom.xml services/equitest-gateway/pom.xml

# Copy service sources
COPY services/ services/

# Package target service and its dependencies
RUN mvn clean package -pl services/${SERVICE} -am -DskipTests

# Stage 2: Minimal Production Runtime
FROM bellsoft/liberica-openjre-alpine:27 AS runtime

ARG SERVICE
ARG PORT=8080
ENV PORT=${PORT}
ENV JAVA_TOOL_OPTIONS="-Xmx256m -Xms64m -XX:+UseG1GC"

RUN apk add --no-cache wget curl && \
    addgroup -g 1001 appgroup && \
    adduser -u 1001 -G appgroup -s /bin/sh -D appuser

WORKDIR /app

COPY --from=builder /workspace/services/${SERVICE}/target/*.jar /app/app.jar
RUN chown -R appuser:appgroup /app

USER appuser:appgroup
EXPOSE ${PORT}

HEALTHCHECK --interval=10s --timeout=5s --start-period=10s --retries=3 \
    CMD wget -q -O- http://localhost:${PORT}/health || exit 1

ENTRYPOINT ["sh", "-c", "java $JAVA_TOOL_OPTIONS -jar /app/app.jar"]
