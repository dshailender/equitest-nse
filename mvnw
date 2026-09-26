#!/usr/bin/env bash
# Maven Wrapper for EquiTest NSE
set -e

# Detect or default JAVA_HOME to Java 27
if [ -z "$JAVA_HOME" ] || [ ! -x "$JAVA_HOME/bin/java" ]; then
    if [ -d "$HOME/.sdkman/candidates/java/27.0.0+35-open" ]; then
        export JAVA_HOME="$HOME/.sdkman/candidates/java/27.0.0+35-open"
    elif [ -d "$HOME/.sdkman/candidates/java/current" ]; then
        export JAVA_HOME="$HOME/.sdkman/candidates/java/current"
    fi
fi

if [ -n "$JAVA_HOME" ]; then
    export PATH="$JAVA_HOME/bin:$PATH"
fi

# Locate Maven binary
MVN_BIN=""
if [ -x "$HOME/.sdkman/candidates/maven/current/bin/mvn" ]; then
    MVN_BIN="$HOME/.sdkman/candidates/maven/current/bin/mvn"
elif command -v mvn >/dev/null 2>&1; then
    MVN_BIN="$(command -v mvn)"
elif [ -x "$HOME/.m2/wrapper/dists/apache-maven-3.9.10/e5402a93/bin/mvn" ]; then
    MVN_BIN="$HOME/.m2/wrapper/dists/apache-maven-3.9.10/e5402a93/bin/mvn"
fi

if [ -z "$MVN_BIN" ]; then
    echo "ERROR: Maven binary not found. Please install Maven or ensure SDKMAN is configured." >&2
    exit 1
fi

exec "$MVN_BIN" "$@"
