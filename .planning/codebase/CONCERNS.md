# Concerns and open risks for the v5 port

1. **No existing device/browser-vision tooling.** Desk mobile tools are
   store-release (Play/AppStore tracks), not device control; web has HTTP
   `preview_check`, not rendered review. Interactive review (Appium, adb,
   simctl, scrcpy, Playwright screenshots → vision) is greenfield in both
   repos — the highest-uncertainty work.
2. **Async→sync façade.** Gateway tools are `async def` on `ToolContext`;
   Omega Prime tools are sync. The v4 messaging precedent (`asyncio.run` per call,
   peer created + closed inside) applies, but 61 tools need consistent
   error-shape mapping (`failure(code, reason)` → `{"error"}`).
3. **Upstream credentials.** 8+ credentialed upstreams (Vercel, Play, ASC,
   GitHub, Greptile, Railway, RAGFlow, Supabase…) each need a broker
   provider + policy hosts + fake peers. Land providers lazily per pack.
4. **Scope.** 61 tools + 13 skills + 8 platform + 2 security + 7 gates +
   prompts/contracts/templates. Phased per pack; each phase extends
   roster/policy/evals or the composition tests go red.
5. **Out of scope (do not port):** desk3d UI + node_modules, gateway
   ASGI/server/auth scaffolding, multi-seat channel mechanics, TS/Rust.
6. **Unverified corners:** `web/mcp-unified-lsp/` purpose, `docs/` audit
   details, gateway `tests/` per-tool expectations (read during each pack),
   `contracts/changes` versioning flow (read during quality pack).
7. **Stacking:** v5 branches from unmerged v4 (`PR #1`); rebase if v4 review
   demands changes.
