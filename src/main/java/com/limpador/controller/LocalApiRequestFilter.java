package com.limpador.controller;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;
import java.net.URI;

/** Blocks browser DNS-rebinding requests addressed to the loopback API using an attacker host. */
@Component
public class LocalApiRequestFilter extends OncePerRequestFilter {
    @Override
    protected boolean shouldNotFilter(HttpServletRequest request) {
        return !request.getRequestURI().startsWith("/api/");
    }

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain chain)
            throws ServletException, IOException {
        String authority = request.getHeader("Host");
        String origin = request.getHeader("Origin");
        if (!isLocalAuthority(authority, request.getLocalPort())
                || (origin != null && !isSameLocalOrigin(origin, request.getLocalPort()))) {
            response.sendError(HttpServletResponse.SC_FORBIDDEN, "Origem local inválida.");
            return;
        }
        chain.doFilter(request, response);
    }

    private boolean isLocalAuthority(String authority, int expectedPort) {
        try {
            URI uri = URI.create("http://" + authority);
            return uri.getRawUserInfo() == null && uri.getRawPath().isEmpty()
                    && isLoopbackName(uri.getHost()) && uri.getPort() == expectedPort;
        } catch (RuntimeException e) {
            return false;
        }
    }

    private boolean isSameLocalOrigin(String origin, int expectedPort) {
        try {
            URI uri = URI.create(origin);
            return "http".equalsIgnoreCase(uri.getScheme()) && uri.getRawUserInfo() == null
                    && uri.getRawPath().isEmpty() && uri.getRawQuery() == null && uri.getRawFragment() == null
                    && isLoopbackName(uri.getHost()) && uri.getPort() == expectedPort;
        } catch (RuntimeException e) {
            return false;
        }
    }

    private boolean isLoopbackName(String host) {
        return host != null && (host.equalsIgnoreCase("localhost") || host.equals("127.0.0.1"));
    }
}
