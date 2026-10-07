# Security baseline

- Configure a non-empty `ADMIN_PANEL_TOKEN` before exposing the service.
- Configure `NEXUS_CONFIG_ENCRYPTION_KEY` before saving OmniRoute/provider keys via the admin API.
- Keep OmniRoute bound to a private interface or protect its endpoint key; Nexus should reach it server-side only.
- Admin configuration responses never include the provider API key.
- Set an explicit `CORS_ORIGINS`; wildcard origins are not accepted by the backend configuration.
- Chat requests are rate-limited and have a body-size limit.
- Session memory is isolated by sanitized session room. Global memory is disabled by default.
- Outbound URL fetching allows only public HTTP(S) hosts, validates every redirect, and limits response size.
- Tool arithmetic uses a restricted AST evaluator; arbitrary Python execution is not allowed.
- The in-process limiter is not a replacement for a shared gateway limiter when multiple workers are used.
- Treat search results and memory as untrusted context. Do not give fetched text higher authority than the system policy.
