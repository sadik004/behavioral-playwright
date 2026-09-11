# Future Development & Extension Guidelines

> **Last Verified Against Commit**: `68a3d1e`
> **Status**: [VERIFIED]

---

## 1. Extension Principles

When contributing or extending Behavioral Playwright, adhere to the following non-negotiable architectural constraints:

1. **Preserve Public API Compatibility**: Never modify or remove existing method signatures on `BP` or the 9 namespaces without maintaining backward-compatible aliases.
2. **Never Reintroduce Simulated Logic**: Do not add fake sleeps, mock response strings, or synthetic delays. Real I/O or explicit failure is mandatory.
3. **Async Cleanliness**: Never use `time.sleep()`, synchronous `requests.get()`, or blocking disk operations inside async methods. Always utilize `await asyncio.sleep()` or `await asyncio.to_thread()`.
4. **Namespace Boundary Discipline**: Place web acquisition logic in `bp.web`, browser logic in `bp.browser`, and diagnostic metrics in `bp.observability`. Do not cross-pollute namespaces.

---

## 2. Recommended Extension Areas

- **Distributed Crawling Cluster**: Implement an async worker pool that pulls URLs from `bp.infrastructure.pop_task()` across multiple machines.
- **Dynamic Semantic LLM Resolver**: Connect the optional `_humanizer.ai_resolver` hook to modern vision-language models (OpenAI, Gemini, Anthropic) for zero-shot selector self-healing.
- **TLS Fingerprint Impersonation**: Integrate custom TLS client hello extensions (e.g. `curl_cffi` or specialized Playwright patches) for advanced Cloudflare turnstile bypass.
