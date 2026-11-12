package com.limpador.controller;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;
import java.util.Set;

/** Blocks browser DNS-rebinding requests addressed to the loopback API using an attacker host. */
@Component
public class LocalApiRequestFilter extends OncePerRequestFilter {
    private static final Set<String> ALLOWED_AUTHORITIES = Set.of("localhost:8080", "127.0.0.1:8080");
    private static final Set<String> ALLOWED_ORIGINS = Set.of("http://localhost:8080", "http://127.0.0.1:8080");

    @Override
    protected boolean shouldNotFilter(HttpServletRequest request) {
        return !request.getRequestURI().startsWith("/api/");
    }

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain chain)
            throws ServletException, IOException {
        String authority = request.getHeader("Host");
        String origin = request.getHeader("Origin");
        if (authority == null || !ALLOWED_AUTHORITIES.contains(authority.toLowerCase())
                || (origin != null && !ALLOWED_ORIGINS.contains(origin))) {
            response.sendError(HttpServletResponse.SC_FORBIDDEN, "Origem local inválida.");
            return;
        }
        chain.doFilter(request, response);
    }
}
