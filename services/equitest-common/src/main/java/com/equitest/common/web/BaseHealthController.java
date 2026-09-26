package com.equitest.common.web;

import com.equitest.common.dto.HealthResponse;
import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.ResponseBody;

public abstract class BaseHealthController {

    @GetMapping(value = "/health", produces = MediaType.APPLICATION_JSON_VALUE)
    @ResponseBody
    public HealthResponse health() {
        return HealthResponse.ok();
    }

    @GetMapping(value = "/api/v1/health", produces = MediaType.APPLICATION_JSON_VALUE)
    @ResponseBody
    public HealthResponse apiV1Health() {
        return HealthResponse.ok();
    }
}
