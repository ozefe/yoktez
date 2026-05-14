# Security Policy

`yoktez` is a synchronous HTTP client over the public YOK NTC endpoints. It performs no authentication, stores no credentials, and writes to disk only when explicitly asked to. Most realistic security issues will surface in dependency CVEs rather than in this codebase.

## Supported versions

Only the latest released version is supported. The project is pre-alpha until `1.0`; older releases will not receive backports.

## Reporting a vulnerability

> [!IMPORTANT]
> Do not open a public issue or pull request for a security problem until a fix has shipped.

Email <hi@efe.cv> with:

- A description of the issue.
- A minimal reproduction (Python snippet, captured fixture, or `curl` trace).
- The affected `yoktez` version (`pip show yoktez`).

Valid reports will land a fix in the next patch release, with credit in the release notes unless you prefer to stay anonymous.

## Scope

In scope: code paths in `src/yoktez/` that mishandle untrusted YOK NTC response bytes (parser bombs, redirect loops, unbounded streaming), and documentation that pushes users toward unsafe patterns.

Out of scope: behavior of `tez.yok.gov.tr` itself, vulnerabilities in transitive dependencies (report those upstream), and feature requests framed as security ("would be safer if ...").
