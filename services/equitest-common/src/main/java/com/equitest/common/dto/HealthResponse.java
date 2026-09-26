package com.equitest.common.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

public record HealthResponse(
        @JsonProperty("status") String status,
        @JsonProperty("version") String version
) {
    public static HealthResponse ok() {
        return new HealthResponse("ok", "0.1.0");
    }
}
