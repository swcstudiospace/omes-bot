# SEC-NET 2.2.0 — durable kernel-egress accounting contract (PROPOSAL)

**Status: PROPOSAL, not accepted; implementation release is blocked pending independent plan and security review of this exact revision/digest.** This architecture correction supersedes the interrupted, unaccepted 2.1.1 and rejected 2.1.0/2.0.0/1.1.0 proposals. `security_design_accepted=false`, `product_security_closed=false`, `matrix_closed=false`. These are status statements, not fabricated gate records.

D-01/D-04 require BOTH T-46-08 and T-46-12 remediation, functional allowed browsing, and mandatory kernel egress. Deleting that control is not a finding resolution. D-03 preserves completed 46-01/LAND-02 and dirty Phase52 work. D-05/D-07 assign all execution, gates and publication to Main using native GSD; original `.swarm/` reports remain immutable. D-02/D-06 retain real interpreter/matching-head CI and publication/audit ordering.

## 1. Selected architecture and evidence limits

One design: **private bubblewrap/no-external-route boundary, native Chromium sandbox, mandatory descendant-cgroup TCP/other-connect and UDP-send/IP-packet denial with durable non-evicting kernel accounting, scalar seccomp under every-syscall supervision, policy-admitted pinned host HTTP**. Uniform inert INET create/bind/UDP association and private NETLINK metadata do not supply page networking; connected UDP remains packet-denied. Prohibited hooks commit BEFORE denial/drop, scalar attempts before resume, received notifications before ID_VALID; USER_NOTIF is not history. Owned native-DNS-disabled/UTS/NSS profile keeps resolution/HTTP host-mediated. One bounded owned CDP pipe, no imported host Internet socket/proxy/tree/credential. No route hook, empty queue, freeze or no-route substitutes for this conjunction; not a replacement exploit sandbox. Publication is terminal-only.

Use raw `Fetch.requestPaused`/`Fetch.fulfillRequest` on the owned pipe, not Playwright `context.route`. The installed driver synthesizes permissive preflight responses before the route callback (`coreBundle.js:36224-36240`) and has internal continue paths (`36183-36185`, `36243-36258`). Copying that behavior violates native CORS and fresh-hop admission.

Evidence actually read, not new verification:

| Evidence | Established fact | Does not establish |
|---|---|---|
| `local://phase46-native-sandbox-capability.json` | Main rendered `chrome://sandbox` in bwrap with uid/gid 1000, dropped capabilities, private namespaces; namespace sandbox, Seccomp-BPF and TSYNC reported active. | Its read-only bind of `/` is diagnostic ONLY, prohibited in the product. No product manifest/filter/drain proof. |
| `local://phase46-cookie-capability.json` | Main's installed Chromium 153/Playwright 1.63 fulfil-only primitive returned two independent cookies on a subsequent native request, hid HttpOnly from JS, and emitted a PNG signature. | No transport TLS/peer, SameSite matrix, partition, worker, redirect or production-boundary acceptance. |
| `local://phase46-cdp-capability.json` | Main observed those cookies directly in `Fetch.requestPaused.request.headers`; a real cross-origin non-simple request produced OPTIONS; fulfilment with 403 caused native CORS denial and no POST event. | No positive credentialed preflight, complete body/redirect/target proof, or production/R12 receipt. |
| Installed `playwright/sync_api/_generated.py:338-414,16799-16800` | `Request.headers` is documented incomplete for security headers; `all_headers()` is documented complete. Chromium sandbox option defaults to **false**. | An ordinary `chromium.launch(headless=True)` is NOT sandbox-enabled. |
| Installed `_impl/_network.py:309-334`; driver `coreBundle.js:36277-36278,36473-36530` | `all_headers()` obtains raw headers; for intercepted Chromium requests those are seeded from `Fetch.requestPaused.request.headers`. Fulfilment uses native Fetch and distinct response-header entries. | ExtraInfo is neither required nor guaranteed for a fulfilled request. |
| Installed `driver/package/types/protocol.d.ts:8136-8375,18988-19018`; bwrap manual; `/usr/include/linux/seccomp.h` | Request-stage Fetch, repeated/binary response headers, recursive flattened attach-before-resume, bwrap isolation/lifetime options and notification UAPI exist. | Compatibility of the complete selected profile still requires Main's real proof. |
| Installed `/usr/include/linux/ptrace.h`, `ptrace(2)` syscall-stop, auto-child, syscall-info and death sections | PTRACE_SYSCALL stops before syscall execution; GET_SYSCALL_INFO supplies tagged arch/number/IP/arguments; auto-traced children stop; EXITKILL kills tracees on tracer exit. SIGKILL can kill without an exit-stop; exec can change TIDs. | No claim that a stop survives death, that ESRCH means clean death, or that Chromium is compatible with the complete profile. |
| Linux v6.8 `kernel/bpf/cgroup.c`, IPv4/IPv6 `af_inet`, `udp`, `ip_output`, `net/core/filter.c`, `net/bpf/test_run.c`, `kernel/sched/membarrier.c`; installed Linux BPF UAPI (read) | Actual cgroup operations precede traffic; UDP send hooks omit connected fast paths and packet hooks require full INET sockets. INET_SOCK_RELEASE precedes protocol close; IPv6 final destruction calls inet_sock_destruct. Cgroup program execution uses RCU; SCHED_CLS supports synthetic test-run; BTF spinlocks and GLOBAL's RCU/nohz_full constraints are specified. | Source is not local verifier/coverage/retirement/full-profile proof. Do not equate file release with final socket destruction or assume tracing programs can take the ledger spinlock. |
| Linux v6.8 `kernel/entry/common.c:syscall_trace_enter`; `kernel/seccomp.c:seccomp_do_user_notification` (upstream source read) | Ptrace entry handling precedes seccomp. USER_NOTIF can be removed on interruption; queue emptiness cannot recover it. | Source ordering is not a running-kernel/product receipt. Full supervised ownership remains required. |
| Main-supplied host facts | `capsh` Current `=ep`, bounding includes BPF/PERFMON/SYS_ADMIN/SYS_PTRACE; cgroup2 is rw/nsdelegate with cpu,memory,pids controllers; tracefs exists, but no seccomp event directory. | These facts prove neither ptrace authorization across the selected user/PID namespaces nor eBPF attach, cgroup delegation to the selected leaf, native compatibility or accounting correctness. This design does not assume a seccomp tracepoint. |
| `local://phase46-ptrace-native-capability.json` (Main diagnostic) | Native Chrome exited 0; namespace/Seccomp-BPF/TSYNC were reported active with all resumes PTRACE_SYSCALL; 162 observed tasks were reaped after 82,381 entries in about 4.15 s. | Overall probe exited 1 / `passed=false`: wrong expected namespace label and one teardown PTRACE_SYSCALL ESRCH. Many IPv4/IPv6 datagram creation entries occurred. No full flags/filter/manifest/cgroup, clean accounting, EXITKILL fault-injection or positive HTTP proof. This is not an accepted protocol receipt. |
| `local://phase46-bpf-feature-capability.json`; `local://phase46-bpf-hook-capability.json` | Main's feature probe reports selected types/helpers; a BTF spinlock ARRAY loaded, but MAP_FREEZE returned errno524/ENOTSUPP; owned FDs were closed. | Feature availability is not combination proof; unsupported freeze is not the selected construction and never counts as acceptance. |
| `local://phase46-bpf-readonly-capability.json` | Main created a BTF spinlock ARRAY readonly to syscalls (BPF_F_RDONLY8); userspace update EPERM, locked lookup and never-attached SCHED_CLS test-run write succeeded. Ten hook types loaded/linked/queryable; IPv4/IPv6 UDP create succeeded and connect/sendto returned EPERM; final primitive counter9, detach queries0, GLOBAL API returned0 and no cleanup errors. | Primitive capability only: no product ledger schema/ACK/lifetime/overflow, final socket-object/RCU correctness, full sealed native-browser startup, HTTP or R01–R12 proof. |
| `local://phase46-fixed-flag-native-sockets.json` (Main diagnostic) | With all declared background switches and active native namespace/Seccomp-BPF/TSYNC, actual AF_INET6/AF_INET DGRAM creations and NETLINK_KOBJECT_UEVENT creation returned nonnegative FDs. | These are native-ALLOW, NOT earlier-native-denied probes. The diagnostic lacks sealed manifest/cgroup/outer filter/CDP/product accounting, observes only selected socket lines, and proves no clean product receipt. It requires architecture correction rather than erasing startup refusals. |
| `local://phase46-bpf-lifetime-btf.json`, `local://phase46-bpf-cookie-btf.json`, `local://phase46-bpf-lifetime-capability.json` | Main identified actual kernel BTF void(sock*) destructor/cookie layout, loaded/linked typed FEXIT, readonly HASH+atomic ARRAY and normal IPv4/IPv6 UDP finalization created/destructed[2,2], empty inventory. Explicit fexit BPF_LINK_DETACH returned95/EOPNOTSUPP; sole owned FD was closed. | IDs/offsets are kernel-specific, never portable constants. This is not full DEAD/CLOSE/queues, races/faults, lifetime quiescence/schema or browser acceptance; tracing link release is not cgroup detach2. |
| `local://phase46-native-classic-cgroup-capability.json` (primitive stages) | Main observed all ten classic BPF_PROG_ATTACH(flags0), query1, identical program IDs retained after program-FD close, matched-FD detach2/query0 and cleanup. | Initial native attempt never ran (driver callback missing); overall receipt then false. Neither those primitive stages nor a subsequently corrected diagnostic substitutes for full production startup/browser/accounting. |
| `local://phase46-native-persistent-hook-startup.json`; `local://phase46-native-resource-capability.json` | Combined ten-hook/resource diagnostic timed out35 s without timeout output/counters (cause unknown). Resource-only fixed-flag run WITHOUT outer hooks/seccomp timed out15 s: pids128 max3/pthread EAGAIN/zygote fork failure, memory max/oom/kill0, cleanup exit-9. | Not impossibility/full-profile proof. Actual nproc8, not many-CPU fact. pids128 incompatible here; finite256 replaces it without affinity/counter reset. Later diagnostic proves selected resource contribution only. |
| `local://phase46-native-guarded-pids256.json`; `local://phase46-native-guard-refusal-trace.json` | pids256/native sandbox startup exited0 with no pids/oom event but strict-connect primitive counters65; traced variant74, actual UDP IPv6 reachability and host-resolver DNS connects. | These are genuine NONCLEAN previous-profile denials, not earlier-native ERRNO/inert reclassification/ignored startup. Host-root resolver view differs from sealed product; no full manifest/trace/CDP/HTTP proof. |
| `local://phase46-native-dns-disabled-capability.json`; `local://phase46-native-dns-disabled-refusal-trace.json` | Fixed nativeDNSrule reduces denials to1; traced run shows2 actual IPv6 DGRAM connects to2001:4860:4860::8888:443 returning EPERM. | Both NONCLEAN; scheduling counts differ, exact remaining kind observed. Suppression is not exercised DNS denial or permission for later data. Uniform association/payload distinction requires revised profile. |
| `local://phase46-native-udp-metadata-capability.json` | Ten classic guards/readonly primitive ARRAY, selected type2+UDP17+INET family/user-family predicate, own hostname/hosts/NSS/resolv/nativeDNSrule, pids256: Chromeexit0 in0.821 s, native namespace/Seccomp/TSYNC Yes, pids/oom0; primitive metadata2/association1/refusal0 without reset. Real IPv4/6 connected send/write/sendfile and TCP connect EPERM; cork queued17/flush0, receivers empty; cumulative refusal10, detach query0/cleanup. | Selected uniform association/resource/native startup and these payload primitives observed, NOT product acceptance. Diagnostic host-root mount/extra dump-dom switches/env differ; no sealed manifest/outer scalar filter/ptrace/full three-map ledger/ACK/FEXIT/drain/rawCDP/allowed HTTP. Primitive passed=true is never R11/security gate. |

Paths beginning `playwright/` above are under `.venv/lib/python3.12/site-packages/`; driver paths are under that package. No command or runtime probe was run by this correction author. Previous P46SecurityGate/P46PlanAndCIReview interruption is not a verdict.

Revision scope includes F1/F2 in `local://phase46-security-gate-21.txt` and all three blockers/two warnings in `local://phase46-plan-gate-21.txt`: durable loss-aware accounting; direct terminal-only publication; registered pre-dispatch root binding through preview/browser/decode; the single typed decoder; native GSD object records; parent-only execution overrides; fresh keyless host verification. Plan-level corrections belong to P46PlansResume; §8–§11 pin their obligations. Main's successful native socket entries invalidate the interrupted all-INET-creation ban as a demonstrated clean-startup solution. This 2.2.0 correction replaces that design choice with real kernel operation/packet denial; it does NOT relax D-01/D-04 or grant startup/background exemptions. GET_FILTER/earlier-ERRNO witnesses cannot relabel that diagnostic. Readonly-from-construction replaces unsupported MAP_FREEZE. This author ran no command/probe/test/lint/build/formatter/CI/Git and changed no product code. The measured primitives are not full-profile or protocol acceptance.

Playwright remains a declared dependency for its existing operator browser provisioning and trusted executable discovery (`sync_playwright().chromium.executable_path`); close that discovery handle before launching the guarded browser. There is no simultaneously attached Playwright driver. An explicit host executable selects the observed `/opt/google/chrome/chrome` build; no unvalidated executable fallback is permitted.

## 2. Exact transport types and ownership

Declarations specify new INTERNAL interfaces, not existing product code. Use postponed annotations for forward references; Protocol/Literal/frozen dataclasses/Callable/Path/SSLContext/SeatPolicy/stdlib have usual meanings. Mutable handles expose stated methods only. Opaque identities/private constructors/owning registries grant authority; copied strings/fields/PIDs/booleans never do. Bounded private authenticated helper messages carry registered references, never publicly transferable authority. Binary map/committer layout is pinned in §5.2b.

```python
HeaderPairs = tuple[tuple[bytes, bytes], ...]
PublicCode = Literal["invalid_url", "forbidden_host", "upstream_error", "not_configured"]
Reason = Literal[
    "url_syntax", "host_policy", "nonpublic_answer", "mixed_answers",
    "resolution_empty", "resolution_failed", "resolution_malformed",
    "foreign_authority", "invalid_permit", "permit_consumed", "peer_mismatch",
    "tls_verification", "request_framing", "response_framing",
    "unsupported_channel", "unsupported_body_metadata", "unsupported_encoding",
    "over_bounds", "deadline_exceeded", "enforcement_attempt",
    "enforcement_channel_failed", "target_attachment_failed", "sandbox_unverified",
    "browser_exited", "cleanup_failed", "cancelled", "owner_died"]

@dataclass(frozen=True)
class Refusal:
    public_code: PublicCode
    internal_reason: Reason
    message: str                       # fixed safe text, never upstream text
class DestinationDenied(Exception):
    def __init__(self, refusal: Refusal) -> None: ...
    refusal: Refusal

@dataclass(frozen=True)
class TransportLimits:
    request_max: int = 8_388_608
    encoded_max: int = 8_388_608
    decoded_max: int = 16_777_216
    ratio_max: int = 16
    header_count_max: int = 100
    header_bytes_max: int = 131_072
    header_line_max: int = 8_192
    request_target_max: int = 8_192
    interim_1xx_max: int = 5
    dns_records_max: int = 64
    dns_message_max: int = 65_536
    resolver_memory_max: int = 134_217_728
    exchange_deadline_s: float = 30.0
    preview_deadline_s: float = 15.0
    preview_sample_max: int = 2_000_000
    io_chunk_max: int = 65_536
    decoder_workspace_max: int = 262_144

class AuthorityHandle: ...              # privately minted by one transport
class ScopeIdentity: ...                # privately minted by one OperationScope
class ConnectionIdentity: ...           # privately registered, never a socket FD
class Clock(Protocol):
    def monotonic(self) -> float: ...
class OperationIdentity: ...           # privately registered by one transport
class AbortSubscription: ...           # privately registered on one AbortHandle
class AbortHandle:
    def abort(self, reason: Reason = "cancelled") -> None: ...
    @property
    def reason(self) -> Reason | None: ...
    def subscribe(self, callback: Callable[[Reason], None]) -> AbortSubscription: ...
    def unsubscribe(self, subscription: AbortSubscription) -> None: ...
@dataclass(frozen=True)
class OperationDrain:
    operation: OperationIdentity
    scopes_closed: int
    pending_scopes: int
    abort_reason: Reason | None
    errors: tuple[str, ...]
    complete: bool
class RootOperation:
    identity: OperationIdentity
    authority: AuthorityHandle
    deadline_at: float                  # absolute, begins before dispatch
    abort_handle: AbortHandle
    @property
    def drain(self) -> OperationDrain | None: ...
    def remaining(self) -> float: ...   # raises on expiry/cancel/finished root
class OperationBinding:
    def __enter__(self) -> RootOperation: ...
    def __exit__(self, exc_type: object, exc: object, tb: object) -> None: ...
class OperationScope:
    identity: ScopeIdentity
    operation: RootOperation
    parent: OperationScope | None
    deadline_at: float                  # no later than root or parent
    abort_handle: AbortHandle           # child handle atomically linked to parent
    def remaining(self) -> float: ...   # raises on expiry/cancel
    def close(self) -> None: ...        # close only this subtree, never cancel parent

@dataclass(frozen=True)
class ParsedURL:
    input_url: str
    browser_url: str
    scheme: Literal["http", "https"]
    host_key: str
    port: int
    http_authority: str
    request_target: str
    tls_identity: str
@dataclass(frozen=True)
class ResolvedAddress:
    family: Literal[2, 10]              # AF_INET, AF_INET6 on selected Linux ABI
    address: str
    port: int
    socktype: Literal[1]                # SOCK_STREAM
    protocol: Literal[6]                # IPPROTO_TCP
    flowinfo: Literal[0] = 0
    scope_id: Literal[0] = 0
@dataclass(frozen=True)
class HttpRequest:
    url: str
    method: str
    headers: HeaderPairs = ()
    body: bytes | None = None           # None absent, b"" explicitly empty
class Resolver(Protocol):
    def resolve(self, host: str, port: int, *,
                scope: OperationScope, limits: TransportLimits) -> tuple[ResolvedAddress, ...]: ...
class ConnectedSocket(Protocol):
    family: int
    def getpeername(self) -> tuple[str, int] | tuple[str, int, int, int]: ...
    def setblocking(self, flag: bool) -> None: ...
    def fileno(self) -> int: ...
    def send(self, data: memoryview) -> int: ...
    def recv_into(self, buffer: memoryview) -> int: ...
    def shutdown(self, how: int) -> None: ...
    def close(self) -> None: ...
class NumericDialer(Protocol):
    def dial(self, endpoint: ResolvedAddress, *,
             scope: OperationScope) -> ConnectedSocket: ...
class TLSVerifier(Protocol):
    def wrap(self, raw: ConnectedSocket, *, identity: str,
             context: SSLContext, scope: OperationScope) -> ConnectedSocket: ...

class DestinationPermit:
    # Read-only fields; only the owning transport may mint/register this object.
    authority: AuthorityHandle
    policy_identity: object             # frozen operation policy binding
    scope_identity: ScopeIdentity
    request: HttpRequest                # the exact immutable request object
    parsed: ParsedURL
    admitted_addresses: tuple[ResolvedAddress, ...]
    selected: ResolvedAddress
    nonce: object                      # unique, registered, consumed before dial
    issued_at: float
    expires_at: float                  # no later than scope.deadline_at
class ValidatedConnection:
    identity: ConnectionIdentity
    authority: AuthorityHandle
    permit: DestinationPermit
    scope_identity: ScopeIdentity
    peer: ResolvedAddress
    tls_identity: str | None
    def abort(self, reason: Reason = "cancelled") -> None: ...
    def close(self) -> None: ...
    def __enter__(self) -> ValidatedConnection: ...
    def __exit__(self, exc_type: object, exc: object, tb: object) -> None: ...
@dataclass(frozen=True)
class SafeResponse:
    url: str
    status: int
    reason: bytes
    headers: HeaderPairs
    body: bytes                        # dechunked, still CONTENT-ENCODED
    content_encoding: Literal["identity", "gzip", "deflate"]
    body_complete: bool
    sample_limit: int | None
    elapsed_ms: float

@dataclass(frozen=True)
class DecodeBudget:
    decoded_max: int
    base64_max: int
    scratch_max: int                    # reserved streaming workspace, not entity output
@dataclass(frozen=True)
class DecodedResponse:
    url: str
    status: int
    reason: bytes
    headers: HeaderPairs
    body: bytes                        # CONTENT-DECODED, or empty for bodyless
    body_kind: Literal["entity", "head", "no_content", "not_modified"]
    body_complete: Literal[True]
    encoded_bytes: int
    decoded_bytes: int
    base64_bytes: int                  # exact 4 * ceil(decoded_bytes / 3)

class DestinationTransport:
    def __init__(self, policy: SeatPolicy | None, *, resolver: Resolver | None = None,
                 dialer: NumericDialer | None = None, tls_verifier: TLSVerifier | None = None,
                 tls_context: SSLContext | None = None, clock: Clock | None = None,
                 limits: TransportLimits = TransportLimits()) -> None: ...
    @property
    def authority(self) -> AuthorityHandle: ...
    @property
    def policy(self) -> SeatPolicy | None: ...
    @property
    def limits(self) -> TransportLimits: ...
    def begin_operation(self, *, deadline_at: float) -> RootOperation: ...
    def bind_operation(self, operation: RootOperation) -> OperationBinding: ...
    def current_operation(self) -> RootOperation | None: ...
    def finish_operation(self, operation: RootOperation, *,
                         deadline_at: float) -> OperationDrain: ...
    def open_scope(self, *, operation: RootOperation, deadline_at: float,
                   parent: OperationScope | None = None) -> OperationScope: ...
    def admit(self, request: HttpRequest, *, scope: OperationScope) -> DestinationPermit: ...
    def connect(self, permit: DestinationPermit, *, scope: OperationScope) -> ValidatedConnection: ...
    def exchange(self, connection: ValidatedConnection, request: HttpRequest, *,
                 scope: OperationScope, sample_limit: int | None = None) -> SafeResponse: ...
    def fetch(self, request: HttpRequest, *, scope: OperationScope,
              sample_limit: int | None = None) -> SafeResponse: ...
    def decode_response(self, response: SafeResponse, *, request: HttpRequest,
                        scope: OperationScope, budget: DecodeBudget) -> DecodedResponse: ...
class SafeFetch:
    def __init__(self, transport: DestinationTransport) -> None: ...
    @property
    def authority(self) -> AuthorityHandle: ...
    def __call__(self, url: str, timeout: float = 15.0, *,
                 operation: RootOperation) -> dict[str, object]: ...
```

Production TLSVerifier uses `ssl.create_default_context`, `CERT_REQUIRED`, hostname checking and HTTP/1.1 ALPN on the already connected socket. Overrides are trusted test/host DI only; production rejects a context that disables verification. A literal IP is verified as an IP SAN, without inventing DNS SNI. The raw FD interface exists solely within trusted transport implementations, never on a browser/factory/tool result.

`DestinationTransport` captures one policy reference with its immutable host-set semantics; config reload constructs a new transport after old scopes drain. It calls the actual `SeatPolicy.allows_host`; it never reconstructs suffix authorization. `None` and empty policy deny before DNS. `admit` validates headers/body/request target BEFORE any dial; the registry ties a permit to that exact immutable request, scheme, authority, effective port, TLS identity, complete admitted answer set, selected peer, scope and expiry. `connect` consumes the registered nonce even on failure. `exchange` verifies identity and can run once only. Foreign/copied/expired/reused permits, requests, connections and scopes refuse. There is no pooling, retry, redirect follow, proxy or second resolution.

Public error mapping is fixed: URL syntax → `invalid_url`; host/nonpublic/mixed admission → `forbidden_host`; absent configuration/foreign authority/unverified startup → `not_configured`; all other listed reasons → `upstream_error`. Detailed reasons live in bounded internal evidence, not private addresses, credentials, cookies, raw exceptions or model-visible logs.

### 2.1 Registered root operation, binding and cleanup

`destination.py` owns every definition above, the root/scope/connection registries and the single explicit operation ContextVar. `begin_operation` validates a finite future absolute deadline (at most the caller's 15 s preview/snapshot or 60 s review/navigation cap) and creates/registers the root plus its live abort handle atomically BEFORE returning. It opens no network resource. Constructors for roots, scopes, handles and subscriptions are private. `bind_operation` verifies exact authority/registry identity, installs that root on entry and resets the token on exit; binding does not finish the root. A different nested root/authority is refused. `current_operation` exposes only the bound, registered root, never an implicit new handle. Bind inside the actual synchronous dispatch worker: executor submission does not implicitly copy a ContextVar.

`open_scope` checks registered root and optional same-root live parent under the ownership lock, takes `min(requested deadline, root deadline, parent deadline)`, registers the child and its cancellation subscription in the same critical section, and refuses a cancelled/finished parent before any IO. Cancellation cannot fall between checking the parent and linking the child. `AbortHandle.abort` is first-reason-wins; subscription after abort immediately receives that reason. Callbacks run outside the registry lock, are bounded wakeups (not blocking cleanup), and signal the child's wakeup FD/supervisor. Unsubscribe waits for any callback using that subscription to retire before its FD can be recycled. Root abort reaches all scopes, resolver helpers, sockets, session supervisors and descendants; child close/abort never cancels a healthy parent or sibling. No standalone, unbound cancellation token is permitted.

`finish_operation` is idempotent for the exact registered root and returns the SAME frozen OperationDrain on repetition. The first finisher closes scope registration, stops remaining owned work, closes/reaps registered resources and waits for cancellation callbacks. The root creator still owns its dispatch registration/slot; a consumer may idempotently finish that root before publication or vision, but may not create a replacement root or release the creator's slot. `complete=true` means zero pending scopes and all owned IO/helpers/launches reaped; it does not mean an aborted operation succeeded. Unregister active work only after complete drain, retaining terminal identity/outcome records for browser receipts/snapshots. Failed cleanup returns `complete=false`, retains outside ownership, poisons admission and never releases an unsafe slot. The first cleanup records one absolute deadline, no later than five seconds after close/cancel starts; subsequent callers may shorten it, never reset/extend it. The root abort handle remains live until publication retires. An abort arriving after drain cannot mutate the frozen drain: every publisher must ALSO check the current handle reason and original work deadline. `remaining()` and new IO refuse on a finished root; post-finish publication uses those explicit fields, not `remaining()`.

SafeFetch requires the explicit root; its preview scope ends at `min(root.deadline_at, now + min(timeout,15))`. Review passes the SAME root through its initial preview and later factory/session, rather than starting another 60 seconds after preview. Session lifecycle scopes parent every browser request scope. Every IO/decode/launch entry checks `remaining()`, including before expensive allocation and after wakeup; root cancellation during the very first DNS/connect/TLS/body wait must reach the actual resource owner before a browser exists.

### 2.2 One decoder and exact encoded/decoded handoff

`DestinationTransport.decode_response` is the ONLY encoded-to-decoded implementation. It checks the exact registered response/request/scope exchange association and live scope/root, and consumes that exchange's decode authorization once, including on failure. `SafeResponse` stays immutable and CONTENT-ENCODED. Any `sample_limit is not None` OR `body_complete=false` refuses `response_framing`; a preview sample is never eligible for browser fulfilment, even when its sampled-mode read reached EOF. SafeFetch does not decode: the encoded prefix still supplies its legacy byte count/hash. Scope retirement removes active exchange/decode ownership without turning copied dataclasses into capabilities.

BrowserSafety reserves aggregate storage BEFORE fetch: encoded maximum, decoded maximum, `4*((decoded_max+2)//3)` base64 bytes, `decoder_workspace_max`, outbound CDP/header framing and any simultaneously retained serialization copy must all fit `inflight_bytes_max`. Release reservations only after fulfilment buffers retire. Pass the reserved decoded/base64/scratch ceilings as DecodeBudget; scratch must cover the bounded streaming workspace independently of output. The decoder rejects noninteger/negative/oversized budgets, intersects output ceilings with TransportLimits, requires the fixed workspace reservation, rechecks deadline/abort per `io_chunk_max` chunk, and refuses `over_bounds` before exceeding encoded/decoded/16x-ratio/base64 bounds. Never retain output from a failed deflate candidate alongside an unbudgeted retry. No unbounded intermediate, all-at-once decompression or concatenation is permitted. Result `base64_bytes` is an exact allocation bound, not an already-encoded second body. BrowserSafety alone performs bounded base64/JSON serialization against it; no second decompressor.

For an entity, decode identity/gzip/wrapped or valid raw deflate with bounded zlib `max_length`, complete stream/trailer validation and no unexplained trailing bytes. Any candidate raw-deflate fallback starts afresh within the SAME total deadline/storage/output budget; an invalid/truncated candidate never becomes a successful prefix. Malformed/truncated data is `response_framing`, unsupported coding is `unsupported_encoding`, limit excess is `over_bounds`; deadline/cancel preserves its own reason. All failures raise DestinationDenied; no decoded result is returned.

The result copies URL/status/reason and preserves ordered distinct end-to-end fields, particularly Set-Cookie, Location and CORS. Strip hop-by-hop/Connection-nominated/proxy and transfer-framing fields. For an ordinary entity remove Content-Encoding and old Content-Length, append ONE exact decoded Content-Length. For HEAD and 304 return empty body, zero decoded/base64 sizes and `head`/`not_modified`, but preserve valid representation Content-Length/Content-Encoding verbatim rather than claiming a zero-length representation; do not attempt to decompress absent bytes. For 204 return empty `no_content`, no synthesized representation length, and refuse prohibited Content-Length or Transfer-Encoding. Actual bytes on any bodyless response or inconsistent framing refuse. BrowserSafety consumes these headers/body directly in Fetch.fulfillRequest. R05/R06 own decoder unit cases; R11 owns real browser consumption, not a second decoder.

## 3. Admission, wire fidelity and pre-allocation bounds

1. Accept HTTP(S) only, port 1..65535. Reject userinfo, whitespace/control/backslash/percent escapes in authority, malformed brackets/ports, trailing-dot or Unicode aliases, IPv6 zones and malformed numeric-looking names before DNS. IPv4 must be canonical four-part decimal (no integers, hex, octal, shortened or leading-zero forms). IPv6 must be bracketed canonical lowercase compressed spelling; policy key is unbracketed. Explicit ASCII punycode is valid. Preserve path/query semantics in percent-encoded origin-form beginning `/`; reject CTL/SP/non-ASCII and oversized serialized target before dial. Browser-normalized requests still receive fresh admission; no claim to recover pre-normalization page spellings.
2. Resolver uses `getaddrinfo(AF_UNSPEC, SOCK_STREAM, IPPROTO_TCP, flags=0)`, no `AI_ADDRCONFIG` or first-answer shortcut. Normalize and classify EVERY returned record before selecting the first admitted endpoint in resolver order. Wrong family/port/protocol/scope, empty/error/malformed sets and any disallowed member refuse with zero dial. All-public mixed A/AAAA is allowed.
3. Require global unicast AND explicit conservative exclusions: IPv4 `0/8,10/8,100.64/10,127/8,169.254/16,172.16/12,192.0.0/24,192.0.2/24,192.88.99/24,192.168/16,198.18/15,198.51.100/24,203.0.113/24,224/4,240/4`; IPv6 `::/96,::ffff:0:0/96,::ffff:0:0:0/96,64:ff9b::/96,64:ff9b:1::/48,2001::/23,2002::/16`, other mapped/compatible/translated forms, ULA/link-local/multicast/documentation/unspecified/loopback and nonglobal/special-use destinations. Test the real 3.12/3.13/3.14 address tables.
4. Dial the selected numeric sockaddr exactly once. Compare raw family/address/port before TLS or HTTP bytes, verify original-host TLS, then re-check the wrapped peer before HTTP. Public-but-different is a mismatch. Ambient uppercase/lowercase proxy variables never participate.
5. Header pairs are ordered bytes, ASCII token names, values without NUL/CR/LF; duplicate fields remain distinct. Reject multiple/inconsistent Host, duplicate/conflicting Content-Length, CL+TE, malformed chunks and unsupported upgrades. Generate Host from ParsedURL (IPv6 brackets, explicit/nondefault port), preserve native method and complete form/JSON/binary entity bytes, strip hop-by-hop and Connection-nominated fields and all proxy credentials. No body text reconstruction.
6. Response parser incrementally bounds line/count/aggregate headers before appending; consumes at most five interim 1xx (101 refuses); handles HEAD/204/304 as bodyless with valid representation metadata (do not change a HEAD representation length to zero); refuses incompatible multiple Location, CL/TE ambiguity, malformed/incomplete entities. All five redirects return original status/Location. Browser follows natively, with a new permit per hop; transport never follows.
7. `SafeResponse.body` is transfer-decoded but content-encoded. Preview alone may stop at 2,000,000 bytes with `body_complete=false` and `sample_limit=2_000_000`; close immediately, never advertise that sample as a complete browser entity. Keep preview `User-Agent: omes-bot/preview-check`, `Accept-Encoding: identity`, `Accept: */*`, `Connection: close`, lowercase last-value preview header dict and existing hash/bytes semantics. Do not replace the existing User-Agent with a new identity.
8. Browser origins are offered only `gzip, deflate, identity`. Use the sole typed decoder in §2.2 on complete responses, including its bounded output/trailer/ratio/budget and bodyless-header rules. Fulfil decoded bytes; preserve separate Set-Cookie, Location and CORS fields. Preview remains encoded and sampled as §3.7 specifies.
9. No unbounded `read()`, `readline()`, body concatenation, `decompress()`, JSON parse, base64 decode or queue insert followed by a late length check. Read at most remaining+1 bytes into capped chunks; count every interim/header/chunk/trailer against bounds. Early known Content-Length/body/message sizes are checked before allocation. Overflow refuses, never truncates to successful browser content. SSE, multipart mixed-replace and open-ended 206 refuse; long-poll/trickling responses hit the absolute deadline.
10. DNS must not wedge the owner or allocate unbounded host memory: perform libc resolution in an owned short-lived helper with the memory cap applied before resolution; bound emitted records/bytes BEFORE serialization and host parse. Deadline/cancel kills and reaps the helper. The helper uses the host resolver configuration but no browser credentials. This is an ordinary owned subprocess, not another agent or service. No claim that cancelling an executor Future interrupts libc.
11. Scope deadline covers DNS + connect + TLS + send + receive + decode, not per-read idle time. Use nonblocking socket/TLS operations, selectors with remaining time and an abort wakeup FD. Cancellation can wake the IO owner and shutdown the registered connection from a separate supervisor; descriptor registration/close is locked to prevent fd-reuse races. All partial-connect/wrap/error paths close raw/wrapped ownership exactly once. The caller cannot increase an inherited deadline.

## 4. Exact browser/session types and configuration

BrowserSafety owns definitions in `omes/tools/browser_egress.py`; the lifecycle adapter stays in `omes/tools/playwright_browser.py`. Shared transport definitions belong only in `destination.py`; BrowserSafety consumes this accepted protocol in parallel, not a duplicate local transport implementation.

```python
class FactoryIdentity: ...
class SessionIdentity: ...
class LaunchIdentity: ...
@dataclass(frozen=True)
class ManifestFile:
    source: Path
    destination: str
    sha256: str
    size: int
    executable: bool
@dataclass(frozen=True)
class BrowserLimits:
    startup_s: float = 15.0
    navigation_s: float = 30.0
    lifecycle_s: float = 60.0
    drain_s: float = 5.0
    cdp_message_max: int = 25_165_824     # accommodates capped decoded/base64 entity
    cdp_read_chunk_max: int = 65_536
    json_depth_max: int = 64
    paused_requests_max: int = 16
    targets_max: int = 32
    callbacks_max: int = 128
    inflight_bytes_max: int = 100_663_296
    logs_max: int = 1_048_576
    notifications_max: int = 1_024
    refusal_entries_max: int = 1_024
    screenshot_max: int = 8_388_608
    ledger_records_max: int = 1_024
    ledger_bytes_max: int = 262_144
    kernel_counter_max: int = 1_048_576
    ledger_maps_max: int = 3            # refusal ARRAY, cookie HASH, lifetime ARRAY
    socket_inventory_max: int = 1_024
    kernel_btf_bytes_max: int = 33_554_432
    bpf_program_instructions_max: int = 4_096
    bpf_programs_max: int = 12          # ten cgroup hooks + destructor + committer
    bpf_verifier_log_max: int = 65_536
    tmp_bytes: int = 67_108_864
    shm_bytes: int = 67_108_864
    run_bytes: int = 4_194_304
    memory_bytes: int = 1_073_741_824
    pids_max: int = 256
@dataclass(frozen=True)
class HostBrowserConfig:
    executable: Path                    # resolved immutable native ELF, not a shell
    bwrap: Path
    manifest: tuple[ManifestFile, ...]
    delegated_cgroup: Path              # operator-delegated, never tool input
    profile_id: str                     # computed config/filter/BTF/manifest/resource identity
    limits: BrowserLimits = BrowserLimits()
@dataclass(frozen=True)
class LaunchConfig:
    host: HostBrowserConfig
    chromium_argv: tuple[str, ...]       # EXACT list below, no ambient/default args
    environment: tuple[tuple[str, str], ...]
    viewport: tuple[int, int] = (1280, 720)
    native_sandbox_required: Literal[True] = True
@dataclass(frozen=True)
class StartupProof:
    launch: LaunchIdentity
    profile_id: str
    executable_sha256: str
    chromium_version: str
    namespace_ids: tuple[tuple[str, int], ...]
    outer_filter_active: bool
    listener_owned: bool
    sandbox_namespace: bool
    syscall_supervision_active: bool
    accounting_policy_sha256: str
    ptrace_options: int
    kernel_ledger_ready: bool
    cgroup_hooks: tuple[KernelProgramBinding, ...]
    socket_retirement: KernelSocketRetirementBinding
    sandbox_seccomp_bpf: bool
    sandbox_tsync: bool
    configuration_verified: bool
@dataclass(frozen=True)
class RefusalEvent:
    sequence: int
    session: SessionIdentity
    source: Literal["admission", "kernel", "controller", "lifecycle"]
    refusal: Refusal
    target_id: str | None
    request_id: str | None
class TraceeIdentity: ...               # registered birth token, not numeric TID authority
class AccountingIdentity: ...           # registered outside supervisor identity
class KernelLedgerIdentity: ...         # private launch/map/committer registry
class EntryTicket: ...                  # one registered stop decision
KernelHook = Literal["sock_create", "sock_release", "bind4", "bind6",
                     "connect4", "connect6", "udp_send4", "udp_send6",
                     "ingress", "egress"]
KernelResourceEvent = Literal["pids_max", "memory_max", "memory_oom",
                              "memory_oom_kill", "memory_oom_group_kill"]
@dataclass(frozen=True)
class KernelProgramBinding:
    hook: KernelHook
    program_id: int
    attach_type: int                   # classic cgroup attachment, NOT a BPF link
    program_sha256: str
@dataclass(frozen=True)
class KernelSocketRetirementBinding:
    program_id: int
    link_id: int
    btf_func_id: int
    kernel_btf_sha256: str
    program_sha256: str
@dataclass(frozen=True)
class KernelSocketRetirementProof:
    launch: LaunchIdentity
    operation: OperationIdentity
    binding: KernelSocketRetirementBinding
    inventory_map_id: int
    lifetime_map_id: int
    created: int
    destructed: int
    inventory_entries: int
    errors: tuple[str, ...]
    link_fd_closed: bool               # sole tracing link owner released; no DETACH opcode
    complete: bool
@dataclass(frozen=True)
class SyscallEntry:
    tracee: TraceeIdentity
    ordinal: int
    arch: int
    number: int
    instruction_pointer: int
    args: tuple[int, int, int, int, int, int]
@dataclass(frozen=True)
class SyscallExit:
    tracee: TraceeIdentity
    entry_ordinal: int
    return_value: int
    is_error: bool
@dataclass(frozen=True)
class SyscallDecision:
    entry: SyscallEntry
    classification: Literal["outer_refusal", "compat_enosys"]
@dataclass(frozen=True)
class EntryAck:
    supervisor: AccountingIdentity
    launch: LaunchIdentity
    operation: OperationIdentity
    ticket: EntryTicket
    decision: SyscallDecision
    refusal_sequence: int | None        # populated ONLY for outer_refusal
@dataclass(frozen=True)
class KernelNotification:
    notification_id: int
    host_tid: int
    flags: int
    arch: int
    number: int
    instruction_pointer: int
    args: tuple[int, int, int, int, int, int]
@dataclass(frozen=True)
class NotificationAck:
    notification_id: int
    launch: LaunchIdentity
    refusal_sequence: int
@dataclass(frozen=True)
class KernelLedgerRecord:
    sequence: int
    source: Literal["admission", "kernel", "controller", "lifecycle"]
    internal_reason: Reason
    hook: KernelHook | None
    host_tid: int | None                # packet context may have no originating TID
    tracee: TraceeIdentity | None
    target_ref: int | None              # bounded owner-registry references, not URL data
    request_ref: int | None
    ticket_ref: int | None
@dataclass(frozen=True)
class KernelLedgerSnapshot:
    identity: KernelLedgerIdentity
    launch: LaunchIdentity
    operation: OperationIdentity
    cgroup_id: int
    map_id: int
    policy_sha256: str
    records: tuple[KernelLedgerRecord, ...]
    last_sequence: int
    kernel_refusals: int                # ALL source-kernel attempts, including entry/unknown RECV commits
    hook_denials: tuple[tuple[KernelHook, int], ...]  # actual hooks ONLY; known notification dedupe adds neither
    # Healthy nonoverflow snapshots: kernel_refusals == number of source-kernel records;
    # sum(hook_denials) == number of source-kernel records with a hook. Failure never claims equality.
    created_inet: int
    released_inet: int
    live_inet: int
    inert_binds: int
    inert_udp_connects: int
    active_hooks: int
    resource_events: tuple[tuple[KernelResourceEvent, int], ...]
    overflow: bool
    integrity_errors: tuple[str, ...]
    sealed: bool
@dataclass(frozen=True)
class KernelLedgerProof:
    snapshot: KernelLedgerSnapshot
    programs: tuple[KernelProgramBinding, ...]
    socket_retirement: KernelSocketRetirementProof
    attachments_detached: bool
    rcu_barrier_complete: bool
    sockets_released: bool
    complete: bool
@dataclass(frozen=True)
class ResumeBarrier:
    supervisor: AccountingIdentity
    launch: LaunchIdentity
    operation: OperationIdentity
    epoch: int
    user_resumes_sealed: bool
    pending_registrations: int
    pending_entry_acks: int
    errors: tuple[str, ...]
@dataclass(frozen=True)
class RefusalAccountingProof:
    supervisor: AccountingIdentity
    launch: LaunchIdentity
    operation: OperationIdentity
    policy_sha256: str
    barrier: ResumeBarrier
    kernel_ledger: KernelLedgerProof
    traced_births: int
    terminal_reaps: int
    exec_retirements: int
    syscall_entries: int
    pre_resume_refusals: int
    compatibility_entries: int
    confirmed_compatibility_entries: int
    notifications_received: int
    invalid_notifications: int
    unacknowledged_entries: int
    unresolved_entries: int
    live_tracees: int
    pending_stops: int
    resume_gate_closed: bool
    supervisor_alive_through_reap: bool
    errors: tuple[str, ...]
    complete: bool
@dataclass(frozen=True)
class DrainState:
    producers_stopped: bool
    descendants_reaped: bool
    connections_closed: bool
    mediation_drained: bool
    kernel_ledger_complete: bool
    accounting_complete: bool
    notifications_drained: bool
    callbacks_finished: bool
    controller_closed: bool
    pending_requests: int
    pending_callbacks: int
    pending_notifications: int
@dataclass(frozen=True)
class CloseReceipt:
    authority: AuthorityHandle
    factory: FactoryIdentity
    session: SessionIdentity
    operation: OperationIdentity
    launch: LaunchIdentity | None        # None only for a failed pre-exec start
    startup: StartupProof | None
    first_refusal: RefusalEvent | None
    last_sequence: int
    accounting: RefusalAccountingProof | None
    drain: DrainState
    errors: tuple[str, ...]              # safe fixed text
    clean: bool
class GuardedBrowserFactory:
    def __init__(self, transport: DestinationTransport, *,
                 config: HostBrowserConfig | None) -> None: ...
    @property
    def authority(self) -> AuthorityHandle: ...
    @property
    def identity(self) -> FactoryIdentity: ...
    @property
    def transport(self) -> DestinationTransport: ...
    def create_session(self, *, operation: RootOperation) -> PlaywrightBrowser: ...
    def owns(self, session: PlaywrightBrowser, receipt: CloseReceipt | None = None) -> bool: ...
class PlaywrightBrowser:
    # Only factory.create_session constructs/registers; no public launch callback.
    authority: AuthorityHandle
    factory_identity: FactoryIdentity
    session_identity: SessionIdentity
    operation_identity: OperationIdentity
    scope: OperationScope
    abort_handle: AbortHandle
    def start(self) -> dict[str, object]: ...
    def navigate(self, url: str) -> dict[str, object]: ...
    def snapshot(self) -> dict[str, object]: ...
    def screenshot(self, path: str | Path) -> dict[str, object]: ...
    def denial(self) -> RefusalEvent | None: ...
    def close(self) -> dict[str, object]: ...
    @property
    def receipt(self) -> CloseReceipt | None: ...
class CallbackIdentity: ...          # private constructor; controller-owned
@dataclass(frozen=True)
class CDPEvent:
    method: str
    params: dict[str, object]        # already bounded, validated CDP input
    target_session: str | None
@dataclass(frozen=True)
class CallbackState:
    queued: int
    running: int
    completed: int
    failed: int
    registration_closed: bool
class EventCallback(Protocol):
    def __call__(self, event: CDPEvent) -> None: ...
class KernelObserver(Protocol):
    def commit_entry(self, decision: SyscallDecision, *,
                     deadline_at: float) -> EntryAck: ...
    def record_exit(self, exit_info: SyscallExit, *, deadline_at: float) -> None: ...
    def latch_notification(self, notification: KernelNotification, *,
                           deadline_at: float) -> NotificationAck: ...
    def commit_refusal(self, refusal: Refusal, *,
                       source: Literal["admission", "controller", "lifecycle"],
                       target_id: str | None, request_id: str | None,
                       deadline_at: float) -> RefusalEvent: ...
    def refresh_ledger(self, *, deadline_at: float) -> KernelLedgerSnapshot: ...
    def receive(self, *, deadline_at: float) -> RefusalEvent | None: ...
    def drain(self, *, deadline_at: float) -> None: ...
    def seal_user_resumes(self, *, deadline_at: float) -> ResumeBarrier: ...
    def finish_kernel_ledger(self, *, deadline_at: float) -> KernelLedgerProof: ...
    def finish_accounting(self, *, deadline_at: float) -> RefusalAccountingProof: ...
    @property
    def first_refusal(self) -> RefusalEvent | None: ...
    @property
    def last_sequence(self) -> int: ...
    @property
    def pending_notifications(self) -> int: ...
    def close(self) -> None: ...
class BoundedController(Protocol):
    def subscribe(self, method: str, callback: EventCallback, *,
                  target_session: str | None) -> CallbackIdentity: ...
    def unsubscribe(self, callback: CallbackIdentity) -> None: ...
    def command(self, method: str, params: dict[str, object], *,
                target_session: str | None, deadline_at: float) -> dict[str, object]: ...
    def pump(self, *, deadline_at: float) -> None: ...
    def callback_state(self) -> CallbackState: ...
    def stop_admission(self) -> None: ...
    def drain(self, *, deadline_at: float) -> None: ...
    def close(self) -> None: ...
class OwnedLaunch:
    @property
    def authority(self) -> AuthorityHandle: ...
    @property
    def factory(self) -> FactoryIdentity: ...
    @property
    def session(self) -> SessionIdentity: ...
    @property
    def identity(self) -> LaunchIdentity: ...
    @property
    def operation(self) -> OperationIdentity: ...
    @property
    def controller(self) -> BoundedController: ...
    @property
    def observer(self) -> KernelObserver: ...
    def verify_startup(self, *, deadline_at: float) -> StartupProof: ...
    def startup_proof(self) -> StartupProof | None: ...
    def abort(self, reason: Reason = "cancelled") -> None: ...
    def reap(self, *, deadline_at: float) -> None: ...
    def drain_state(self) -> DrainState: ...
    def close(self) -> None: ...
class LaunchBackend(Protocol):
    def launch(self, config: LaunchConfig, *, authority: AuthorityHandle,
               factory: FactoryIdentity, session: SessionIdentity,
               scope: OperationScope) -> OwnedLaunch: ...
```

`OwnedLaunch` has a private constructor and owns child/pidfds/cgroup, every BPF map/program/link/committer FD, CDP/log pipe ends, notification FD, syscall-stop supervisor and lifelines. It registers authority/root/factory/session/launch before exposing controller/observer; LaunchBackend receives the registered lifecycle scope, not a free abort handle. No BPF FD, cgroup FD, executable callback or ledger capability enters Chromium or a tool result. `verify_startup` runs AFTER trusted native exec and BEFORE untrusted navigation; failure raises DestinationDenied and aborts. `reap` returns only after every descendant/helper and kernel-proven exec retirement is reconciled and producers cannot restart. Kernel socket/link/RCU retirement remains the observer's separate mandatory barrier. Deadline failure retains watchdog/ledger ownership and poisons dispatch; `close` cannot convert an incomplete proof into a clean receipt.

`GuardedBrowserFactory._for_test(transport: DestinationTransport, *, config: HostBrowserConfig, launcher: LaunchBackend) -> GuardedBrowserFactory` is the only private trusted test constructor. It still registers/matches exact typed launch ownership; no tuple/object/boolean is accepted as a guarded launch. Production `__init__` never accepts a launcher. It resolves host config once in `default_registry` from `OMES_CHROMIUM_EXECUTABLE` (or Playwright executable discovery), `OMES_BROWSER_CGROUP_ROOT`, installed bwrap, and the manifest rule below. Model args cannot set any field.

Callbacks execute on the single controller owner with pre-insertion entry/byte reservations and running/completed/failed accounting. Command acknowledgement pumping may queue events but never re-enter a callback. Exceptions commit a controller refusal; unsubscribe never discards queued/running work. `stop_admission` stops new user commands/subscriptions, aborts network work and retains drain subscriptions. KernelObserver refreshes the locked durable ledger before returning adapter data, before/after every callback/command acknowledgement and during close; its independently runnable bounded receiver also monitors it. All admission/controller/lifecycle refusals use `commit_refusal`, not a second sequence counter. Notification drain only retires its channel. `seal_user_resumes`, `finish_kernel_ledger`, and `finish_accounting` implement §5.2a/b; no post-death notification or ring emptiness claim is permitted. Receipt freezing requires retired requests/callbacks/notifications/stops, closed controller, exact registered complete kernel and trace proofs, and the ledger's final sequence.

`close()` preserves public `{ok:true}` or `{ok:false,errors:[...]}`; internal immutable `receipt` carries identity, drain and accounting proof. `start` retains `{ok:true,open:true}`, navigate `{title,url,status}`, snapshot `{title,url}`, screenshot `{path,bytes}`; errors remain top-level safe `error`. These adapter values are INTERNAL/provisional until terminal close. Neither review_page nor direct BrowserSession may publish them as success without its own registered clean terminal receipt. Repeated close returns the same outcome and the same registered receipt object. Direct snapshot follow-up uses finalized cached data, never a live provisional adapter (§7.2).

## 5. Mandatory boundary, exact launch and startup order

### 5.1 Filesystem, environment, IPC and lifetime

Use bwrap with `--unshare-user --unshare-pid --unshare-net --unshare-ipc --unshare-uts --hostname omes-browser --unshare-cgroup --uid 1000 --gid 1000 --cap-drop ALL --die-with-parent --new-session --clearenv`. Fresh empty mount root, launch-owned fixed UTS hostname. No try/share/veth/external route/inherited namespace FD/host resolver socket/TCP debugging/proxy. Native networking never supplies a page. Inert socket/bind/UDP association differs from transmission; real kernel send/packet guards, not no-route alone, block payload including loopback.

Build a manifest of **individual regular files**, never a bind of `/`, `/usr`, the repo, home, host `/tmp`, `/run`, `/proc` or a mutable dependency directory. Allowed inputs are the selected Chromium distribution's executable/resources/locales, transitive ELF interpreter/DT_NEEDED libraries, minimal font/fontconfig files, and the selected Python bootstrap interpreter/stdlib plus the one installed boundary module. Derive ELF dependencies by reading ELF metadata, not executing `ldd` on supplied binaries. Resolve symlinks to canonical approved roots; reject escapes and socket/FIFO/device inodes recursively, writable group/world trees and changes between open/fstat/hash/copy. Copy the accepted bytes to sealed read-only memfds and use per-file `--ro-bind-data`; never expose a mutable source tree after verification. Cap manifest at 4096 files/512 MiB total before copying. Do not copy site credentials, NSS databases, browser profiles, host passwd/group, SSH/DBus/Docker/Wayland/X11 sockets or environment files.

Only owned PID-namespace `/proc`; minimal new `/dev` null/zero/random/urandom/fd symlinks, bounded private tmpfs `/tmp`/`dev/shm`/`run`, sealed generated passwd/group/config; no host sysfs/cgroup. Generate/seal `/etc/hosts` EXACTLY `127.0.0.1 localhost omes-browser` newline `::1 localhost omes-browser` newline; `/etc/nsswitch.conf` EXACTLY `passwd: files`, `group: files`, `hosts: files`, `networks: files`, each newline. `/etc/resolv.conf` only `# Native DNS disabled; HTTP resolution is host mediated.` newline, no nameserver/search/options. No host NSS/resolver content/proxy. Dependency root readonly/nosuid/nodev; fresh profile/home/cache. No host writes; PNG pipe output goes to validated host artifact path.

Exec environment is EXACTLY `HOME=/tmp/home`, `TMPDIR=/tmp`, `XDG_CONFIG_HOME=/tmp/config`, `XDG_CACHE_HOME=/tmp/cache`, `LANG=C.UTF-8`, `LC_ALL=C.UTF-8`, `TZ=UTC`, `PATH=/usr/bin:/bin`, `PWD=/tmp`. Pass explicitly at bootstrap, bwrap and Chromium exec; never inherit proxies, tokens, DBus/SSH/DISPLAY/XDG_RUNTIME_DIR, `PYTHON*`, `LD_*` or Playwright environment. A credential canary must be absent from every descendant. Python bootstrap uses isolated mode and only its copied stdlib/module; browser discovery happens outside, before this environment is constructed.

Before FIRST child/bwrap exec create delegated cgroup-v2 leaf: memory.max1073741824/swap.max0/pids.max256/cpu.max200000 100000 (two CPU equivalents). Isolated128 failure justified finite256; no affinity/cpuset. Revised nativeDNS argv is explicitly §5.3, not an undisclosed flag change. All birth bounds use256. Verify ten classic guards/three readonly maps/committer/FEXIT BEFORE stopped sanitized child enters leaf; no imported INET socket/cgroupfs/join/management FD/external broker/host capability. RLIMIT_NOFILE256/core0/files64MiB/bounded tmpfs retained. Exact prerequisites safely refuse, never reconfigure host policy; primitive compatibility is not full-profile approval.

**Exact outside ownership:** a dedicated registered accounting/watchdog process owns delegated leaf, three readonly-user map FDs, ten classic program handles, committer and SOLE FEXIT link FD. A different stable ptrace process/thread owns all stops/restarts; a third independent reader owns the listener. Main/controller holds only registered private proxies/lifeline, not transferable authority. Register every helper birth/pidfd/channel before launch; authenticate bounded root/launch/ticket messages against those exact peers. Controller or ptrace death wakes the independently runnable accountant to commit owner_died/kill/reap while classic guards/FEXIT remain. Tracer death still forbids complete trace proof. Accountant death loses tracking/ACK authority, permanently nonclean; persistent classic guards remain and surviving outside owner kills, retaining poisoned ownership rather than unsafe detach/fake drain. No duplicated/pinned/passed tracing link, no dead-owner finally dependency.

Chromium exec FD map: 0 readonly /dev/null, 1/2 bounded logs, 3 CDP read, 4 CDP write; close/type-check ALL others including duplicate/unconnected INET and directory/namespace FDs. Trusted bootstrap alone gets FD5 private Unix seqpacket for bounded ready/attach ACK and exactly ONE listener SCM_RIGHTS transfer. Outside accounting receiver validates SCM_CREDENTIALS/host birth/pidfd/cgroup/ns and transfers listener only to registered reader; payload PID never authority. Close bootstrap5/listener copy before exec. Owner lifeline is outside-only, no numbered FD6/management handle enters bootstrap/Chromium. Later boundary channels byte-only/no SCM_RIGHTS; UNIX filesystem/abstract namespace private, in-group FD passing cannot import host descriptors.

Use bwrap's real PID1 reaper (not `--as-pid-1`). A stable trusted outside supervisor PROCESS owns all ptrace operations/waits for the tracees, and a separately runnable watchdog owns lifeline/pidfd/cgroup teardown. They are bounded ordinary helper processes, not additional agents/services. Main-owner EOF/HUP, tracer/reader loss, deadlines or failed close kill/reap the owned namespace; PTRACE_O_EXITKILL independently kills tracees on tracer death. Bwrap's parent-death chain is additional enforcement, not a dead parent's `finally`. Account for PR_SET_PDEATHSIG's creating-thread lifetime. No success on unconfirmed death: cgroup-empty, pidfd/process wait completion and the exec/thread reconciliation in §5.2a are required. No detached/new-session/double-fork descendant may escape this owned group.

### 5.2 Scalar kernel filter and exact classifier

Install inherited cBPF in single-threaded post-bwrap bootstrap AFTER outside SEIZE/INTERRUPT ownership and BEFORE Chromium exec. Pinned UAPI/stdlib bindings, no package/compiler install. Transfer ONE NEW_LISTENER to registered outside reader, require ACK and close bootstrap copies/channel; ten mandatory persistent cgroup attachments already active. Every successful prohibited RECV permanently latches FIRST regardless ID_VALID/death/correlation; NotificationAck precedes validity/reply. Valid ID sends error=-EPERM,val0,flags0; invalid/withdrawn/failed reply retains refusal and uncertainty. No CONTINUE/ADDFD; empty listener queue proves no history.

The immutable policy compiles to both cBPF and the synchronous scalar classifier. Pin audit arch `AUDIT_ARCH_X86_64=0xc000003e`, x32 bit `0x40000000`, and the read x86_64 UAPI inventory: known numbers0–334 and424–461 only. Other arch/x32/i386/socketcall, negative/noncanonical or out-of-inventory numbers refuse, never native fallthrough. For integer arguments use the kernel's low-32-bit signed/unsigned casts identically in both representations; clone/unshare masks use the full native unsigned long. Preserve the six raw 64-bit arguments and IP in SyscallEntry. No mutable tracee pointer is dereferenced for a permission decision. Default **ALLOW applies only to other known native syscalls**, because retained Chromium remains the exploit-containment layer.

| Class / native number | Exact decision |
|---|---|
| `socket(41)` | Allow AF_UNIX(1) STREAM(1)/DGRAM(2)/SEQPACKET(5), protocol0; AF_INET(2)/AF_INET6(10) STREAM with protocol0/TCP6 or DGRAM with protocol0/UDP17; AF_NETLINK(16) RAW(3)/DGRAM with NETLINK_ROUTE0 or NETLINK_KOBJECT_UEVENT15. All allow only type flags NONBLOCK0x800/CLOEXEC0x80000. INET create/bind is uniformly inert metadata under mandatory cgroup operation/packet denial, not a per-role/startup exemption. Every other family/type/protocol, especially raw INET/AF_PACKET/AF_VSOCK, notifies/refuses. |
| `socketpair(53)` | Only the same AF_UNIX matrix/protocol0/flags; every other family, including NETLINK and INET, notifies/refuses. |
| Imports/alternate execution | `ptrace101`, `name_to_handle_at303`, `open_by_handle_at304`, `setns308`, `process_vm_readv310/writev311`, `bpf321`, `io_uring_setup425/enter426/register427`, `pidfd_getfd438` notify/refuse. No inherited host socket or external broker is permitted. |
| Native nested sandbox | `clone56` permits CSIGNAL, VM, FS, FILES, SIGHAND, THREAD, SYSVSEM, SETTLS, PARENT_SETTID, CHILD_SETTID, CHILD_CLEARTID, VFORK, PARENT and NEWUSER/NEWPID/NEWNET/NEWNS/NEWIPC/NEWUTS only. Deny all other bits, including CLONE_UNTRACED/CLONE_PTRACE/NEWCGROUP. `unshare272` permits only those namespace bits plus FILES/FS/SYSVSEM. `chroot161` stays within the private root. |
| Mount/join surfaces | `pivot_root155`, `mount165`, `umount2 166`, `open_tree428`, `move_mount429`, `fsopen430`, `fsconfig431`, `fsmount432`, `fspick433`, `mount_setattr442` notify/refuse after trusted bwrap setup. New namespace capabilities cannot regain host views/cgroups/routes. |
| Compatibility | `clone3 435` returns `SECCOMP_RET_ERRNO|ENOSYS(38)` with separately counted/confirmed compatibility entries, never an egress-refusal exemption. Its pointer is not inspected. |
| Nested seccomp | `seccomp317`: SET_MODE_FILTER1 permits flags0/TSYNC1, or TSYNC1 with TSYNC_ESRCH16; GET_ACTION_AVAIL2/GET_NOTIF_SIZES3 permit flags0. Other operations/flags, especially NEW_LISTENER8, notify/refuse. `prctl157` PR_SET_SECCOMP22 permits FILTER2 only; PR_SET_SYSCALL_USER_DISPATCH59 notifies/refuses so no earlier syscall-dispatch stage bypasses tracing. |
| Unneeded surfaces | `add_key248`, `request_key249`, `keyctl250`, `userfaultfd323` notify/refuse. `personality135` allows low-32-bit query0xffffffff only; changes notify/refuse. |

Kernel-invalid combinations fail normally; neither classifier invents permission from failure. Native ERRNO/TRAP/KILL may suppress outer notification; scalar-prohibited entry still commits refusal forever. Native denial of outer-allowed operation is not exercised cgroup refusal. Uniform INET create/bind/UDP association applies to EVERY tracee; no inner-filter extraction explains away actual successful sockets. Prohibited TCP/other connect/UDP send/IP packet denials always count during startup/background work. No sandbox weakening, historical reinterpretation, ignored denial/reset or relaxed second profile. Only the explicitly revised immutable profile, independently re-reviewed and actually exercised, can establish compatibility.

### 5.2a Loss-aware owned syscall-stop protocol

**Selected mechanism:** outside synchronous ownership before every tracee syscall; scalar refusal commit/ACK precedes any resume. The durable cgroup ledger independently accounts actual IP denial (§5.2b). No sys_enter tracepoint, audit log, ring/perf queue, stop surviving death or postmortem reconstruction is assumed.

1. **Attach before producers.** The trusted single-threaded post-bwrap bootstrap waits on its private channel without executing Chromium. Verify kernel SCM_CREDENTIALS, host process/namespace/cgroup membership and process pidfd, then PTRACE_SEIZE with exactly `TRACESYSGOOD|TRACEFORK|TRACEVFORK|TRACECLONE|TRACEEXEC|TRACEEXIT|EXITKILL` (`1048671`). PTRACE_INTERRUPT and own its PTRACE_EVENT_STOP before resuming any bootstrap step. Only this stage installs the acknowledged outer listener; seal that stage before native exec. No attach-to-running-browser fallback.
2. **One owner, exact ABI.** One stable supervisor process/OS thread owns ptrace and `waitpid(-1,__WALL)` statuses. Use SIGCHLD/abort pipe wakeups, WNOHANG+__WALL and the inherited absolute deadline, not an unbounded wait loop. At SIGTRAP|0x80 zero a fixed native ptrace_syscall_info buffer, call GET_SYSCALL_INFO, and require tagged ENTRY/EXIT shape/available bytes (ENTRY through args, EXIT through is_error), matching arch/registered task state. Preserve ENTRY IP/nr/six arguments. Never infer alternation or synthesize a missing exit.
   **Wire ABI:** PTRACE_SEIZE0x4206/INTERRUPT0x4207/GET_SYSCALL_INFO0x420e/SYSCALL24/GETEVENTMSG0x4201/GETSIGINFO0x4202; options1048671, __WALL0x40000000/WNOHANG1. Native syscall-info buffer88 bytes: op u8 at0, padding3, arch u32 at4, IP/SP u64 at8/16; ENTRY1 nr u64 at24/args6 at32 (kernel available>=80); EXIT2 signed retval at24/is_error u8 at32 (>=33). NONE0/unexpected SECCOMP3/short/foreign state is nonclean, not alternation. seccomp_data64 bytes nr signed32/archu32/IPu64/args6; notif80=id u64/PID u32/flags u32/data64, response24=id u64/val s64/error s32/flags u32. Query actual GET_NOTIF_SIZES, zero fixed bounded buffers, validate selected UAPI/endian/zero unknown flags; cap advertised notif/response/data at256/64/128 before allocation. Invalid size/ABI never truncates into valid authority.
3. **Task identity/state.** Mint a private birth token only from the automatically owned bootstrap/child stop and parent GETEVENTMSG; corroborate host TID/TGID/starttime/NSpid/cgroup while stopped. A numeric TID is not authority and cannot be recycled before its terminal/exec record reconciles. Linux6.8 process pidfds bind TGIDs; per-thread coverage is owned per-TID waits/birth tokens, not an assumed thread-pidfd feature. Bound active/pending births to pids_max and one active entry per tracee.
4. **Commit before resume.** For outer_refusal reserve a fixed ticket, retain the exact SyscallEntry, and send a bounded typed decision over the private nonblocking outside channel. `commit_entry` appends source=kernel/reason=enforcement_attempt through the §5.2b committer, refreshes the kernel-ordered first refusal, registers ticket→sequence, then returns EntryAck. Validate supervisor/root/launch/tracee/ordinal/ticket/decision/sequence before PTRACE_SYSCALL; failure leaves it stopped and tears down. Refusal is already committed before USER_NOTIF enqueue/withdrawal/RECV/ID_VALID/death. compat_enosys also obtains a registered ACK, but no refusal record; tagged EXIT must confirm -38/is_error before clean retirement.
5. **Stop/resume table.** Tagged ENTRY is classified before restart; tagged EXIT retires only its known entry. FORK/VFORK/CLONE GETEVENTMSG registers parent and initially stopped child before either resumes; arrival order may differ but pending/unknown children never resume. EXEC uses former TID from GETEVENTMSG plus kernel de-thread semantics to reconcile the surviving birth and retired siblings; each birth becomes exactly one terminal reap or proven exec retirement. EXIT GETEVENTMSG records irreversible kernel exit; only that exit may restart to completion. Initial/owned INTERRUPT PTRACE_EVENT_STOP is synthetic/signal0; sealing interrupts are held. Signal-delivery-stop requires GETSIGINFO matching wait signal and reinjects only that signal via PTRACE_SYSCALL. Group/job-control stops are held and fail the operation, never LISTEN/CONT. Unknown stop/op/size/transition is nonclean and cannot resume.
6. **No escape restart.** Every user-executable restart is PTRACE_SYSCALL, signal0 except verified signal delivery. Never CONT/DETACH/SYSEMU/SINGLESTEP, register rewrite or SUSPEND_SECCOMP. Clone tracing/untraced flags are denied; nested PID namespaces, setsid/double-fork, exec and FD sharing never detach tracer/cgroup ownership.
7. **Independent reader.** A registered outside reader in the host PID namespace owns RECV; polling does not eliminate blocking after withdrawal. It sends fixed bounded KernelNotification records, obtains NotificationAck BEFORE ID_VALID/SEND, and never stalls ptrace/cleanup. Correlation checks listener/launch, TID birth/active ordinal and complete seccomp_data; recycled PID alone is forbidden. Every received prohibited record latches even if invalid/unmatched/foreign-looking/from a dead task; uncertainty adds enforcement_channel_failed. Map/ACK failure preserves the received record and sticky local failure, authorizes no resume/reply and forbids complete/clean proof. Never discard an unanswerable record.
8. **Bounds/loss.** Reserve ticket/notification/pipe capacity before insertion. uint64 birth/ticket/ordinal counters check saturation; ledger sequence is separately bounded. Full buffers, malformed/duplicate/foreign ACKs, failed syscall-info, unclassified ESRCH, unknown births, inconsistent counters or owner/reader/tracer death are nonclean. All waits use registered abort wakeups and one work/drain deadline. Watchdog kill/reap remains independently runnable; EXITKILL independently kills on tracer death. Dead-owner finally is not enforcement.
9. **Death is not absence evidence.** SIGKILL may remove an unread stop; an unapproved entry never passed the pre-seccomp gate, and a resumed prohibited entry already committed refusal. Unexplained disappearance/loss remains nonclean even if later cgroup-empty. Avoid restart on a retired/killed task. Terminal ESRCH reconciles only a previously observed irreversible EXIT or recorded exec retirement/owned kill, matching kernel terminal evidence and no possible user-returning resume. ESRCH alone never supplies those facts. Main's teardown ESRCH lacks that receipt and remains failed.
10. **Seal/reap barrier.** Graceful close stays supervised. `seal_user_resumes` atomically closes the resume gate, increments a registered epoch, interrupts live tasks and reconciles child/exec/stop/ACK registrations. No user-returning restart after seal; positively identified irreversible EXIT may drain, while survivors receive SIGKILL/cgroup.kill. Keep supervisor/observer/reader/watchdog/ledger through task/process/cgroup reconciliation. Reap a blocked reader only after producers are terminal, drain its outside pipe to EOF and retire all ACKs/received records. Authorized reader retirement is not historical queue-emptiness proof.
11. **Final trace proof.** `finish_accounting` returns one registered immutable proof for exact root/launch/policy/ResumeBarrier and COMPLETE KernelLedgerProof. Complete requires healthy ownership through reap, sealed resumes, zero unacknowledged/unresolved entries/live tracees/pending stops/registrations, confirmed compatibility counts, no integrity errors, and traced_births=terminal_reaps+exec_retirements. Notification counts do NOT equal attempted syscalls. Clean additionally requires pre_resume_refusals=notifications_received=invalid_notifications=0, ledger kernel_refusals=0/records empty, no session refusal/errors and every DrainState condition. Notifications_drained means only channel/users retired; withdrawal cannot alter a durable commit.

**Ptrace prerequisites:** selected x86_64 Linux ordering/UAPI, SEIZE/INTERRUPT/GET_SYSCALL_INFO/automatic child/exec/exit stops/EXITKILL, readable identities/pidfds and authorized tracing across post-bwrap uid/user/PID namespaces through native sandbox transitions. Where credentials do not suffice, effective CAP_SYS_PTRACE in the proper ancestor user namespace and permitting Yama/AppArmor/LSM policy are required. No product host-policy relaxation. Diagnostic bounding bits/tracefs/Chrome exit0 are not protocol proof.

### 5.2b Mandatory operation/packet hooks and durable kernel ledger

Replace incompatible bans on inert INET create/bind/UDP association, NOT mandatory egress. One uniform matrix for every process/address/request class, no startup/PID whitelist. UDP association may cache source/peer/route without transmitting a datagram. TCP/other connects and all UDP-send/IP-packet hooks commit/deny; connected UDP is guarded at real output despite SENDMSG fast-path omission. Genuine denial invalidates the session including startup. Page HTTP(S) stays fresh-admitted pinned host transport.

| Hook / expected attach type | Program / fixed decision |
|---|---|
| sock_create / BPF_CGROUP_INET_SOCK_CREATE2 | CGROUP_SOCK9. Only scalar matrix INET STREAM/TCP or DGRAM/UDP; register cookie/lifetime then lock increment created/live, return1. Full/bad metadata/inventory commits denial/error, return0. |
| sock_release / BPF_CGROUP_INET_SOCK_RELEASE34 | CGROUP_SOCK9. Under lock decrement live_inet/increment released_inet for kernel socket release; underflow/unknown lifecycle marks integrity failure. Return1 so release cannot be prevented. |
| bind4/bind6 / BPF_CGROUP_INET4_BIND8/INET6_BIND9 | CGROUP_SOCK_ADDR18. Uniform inert_binds lock increment, return1 only healthy/below cap; exhausted/bad header commits denial/error, return0. No role/address exemption. |
| connect4/connect6 / BPF_CGROUP_INET4_CONNECT10/INET6_CONNECT11 | CGROUP_SOCK_ADDR18. ALLOW ONLY ctx.type=SOCK_DGRAM2 AND ctx.protocol=UDP17 AND ctx.family in{AF_INET2,AF_INET6 10} AND ctx.user_family independently in{2,10}; lock increment inert_udp_connects before return1. No per-hook equality: dual-stack/mapped association allowed; invalid pairs fail natively. STREAM/TCP/other/malformed/exhausted commits enforcement_attempt/error, return0. No sockaddr rewrite/role/address exception. |
| udp_send4/udp_send6 / BPF_CGROUP_UDP4_SENDMSG14/UDP6_SENDMSG15 | CGROUP_SOCK_ADDR18. Commit then return0 unconditionally; actual unconnected sendto/sendmsg/sendmmsg paths cannot send DNS/STUN/QUIC/UDP payload. |
| ingress/egress / BPF_CGROUP_INET_INGRESS0/INET_EGRESS1 | CGROUP_SKB8. Commit then return0 unconditionally, including loopback. Program return0 is DROP, not the kernel wrapper's NET_XMIT_SUCCESS value. |

Attach all ten with BPF_PROG_ATTACH command8, target_fd=owned leaf, attach_bpf_fd=owned program, expected attach_type, attach_flags0 (no override/multi/replace). Use CLASSIC kernel-persistent attachments, NOT FD-lifetime BPF_LINKs: kernel cgroup references retain programs/maps if any/all user FDs die, so owner loss cannot transiently remove IP denial before watchdog/EXITKILL. Verify BPF_PROG_QUERY effective type/IDs plus program INFO/maps/tags against exact leaf/policy registry; reject conflicting/missing ancestor/leaf controls before first child. No bpffs pins or host-global network change. Keep program/map/fexit-link/committer FDs private outside. No tracee migration/control/import capability; never remove/rmdir leaf before all producers retire. Sole outside tracing link FD is unpinned/unpassed/unduplicated; all launch/helper FD sanitation prevents persistent inheritance. Loss of tracker/reader/committer still makes proof nonclean even though kernel guards remain.

**Exact coverage.** IPv4/6 UDP association is peer/source/route only, no handshake/data. AF_UNSPEC disconnect normally bypasses pre-connect; unexpected hook delivery fails predicate. UDP send4/6 omits connected fast paths: those hit full-INET skb egress BEFORE IPv4/6 finish-output/fragment/neighbor transmission; return0 drops even if send reports bytes. Ingress denies delivery. No imported socket/raw/other family/io_uring/external route; no socketless-kernel/AF_PACKET/host coverage claim. R09/R10 exercise connected/unconnected IPv4/6 loopback/public/private/mapped UDP, send/sendto/sendmsg/sendmmsg/write/writev/cork/GSO/sendfile/splice/dup/descendant and TCP/TFO where supported: actual hook/drop AND zero forbidden packets/HTTP. Invalid/native-denied/unavailable/route-failed is not exercised denial. Guard queued sk/data refs through actual destruction.

**One durable refusal ledger/sequence.** Before producers create ONE non-evicting ARRAY key0, map_flags=BPF_F_RDONLY8, NOT RDONLY_PROG; all three accounting maps readonly to userspace from construction, no RW FD/mmap/pin/exposure, program writes enabled. Top BTF spinlock protects fixed refusal header/counters plus ≤1024 fixed96-byte records; all declared values/inventory≤ledger_bytes_max, maps≤3/programs≤12/instructions≤4096/log≤65536/BTF≤kernel_btf_bytes_max. Unsupported MAP_FREEZE is NOT used. INIT sets immutable launch/root/policy/map association only at uninitialized/all-counts-zero BEFORE child; subsequent INIT permanently rejects, never resets. Ten classic bindings match leaf/header/map ownership. No replacement/reset/delete/LRU/ring/perf refusal history.

#### Shared binary accounting ABI (format220)

Flatten header members into the TOP-LEVEL map-value BTF struct so offset0 bpf_spin_lock is discoverable; do not hide it inside nested Header BTF. Records may be a nested fixed-array type. Bounds/endian/BTF verification precede producers.

Pin x86_64 little-endian, exact lengths, zero reserved bytes, BTF member offsets and aligned stack/map accesses. Emit/read the same schema once in the boundary module; no second permissive decoder. The syscall-RO ARRAY has key u32 zero, one value of 98,560 bytes: 256-byte header then 1,024 records of 96 bytes. Spinlock covers EVERY refusal/header mutation except the lock itself. Userspace snapshots use BPF_F_LOCK4 and validate the entire fixed value before decoding. Unknown bits/enums/lengths or non-dense sequence are sticky errors.

| Header byte offset | Field / exact type |
|---|---|
| 0 / 4 | BTF bpf_spin_lock u32 / format u32=220 |
| 8 / 24 | launch nonce[16] / operation nonce[16], private registry associations, not transferable authority |
| 40 / 72 | policy SHA256[32] / owned leaf cgroup ID u64 |
| 80 / 88 / 92 | last_sequence u64 / record_count u32 / capacity u32=1024 |
| 96 | flags u64: overflow1, integrity2, sealed4, initialized8; all other bits forbidden |
| 104 / 112 / 120 / 128 | kernel_refusals / created_inet / released_inet / live_inet, each u64 |
| 136 / 144 / 152 | inert_binds / inert_udp_connects / active_hooks, each u64 |
| 160..239 | ten u64 hook-denial counts in KernelHook declaration order |
| 240 / 244 / 248 / 252 | header_bytes u32=256 / record_bytes u32=96 / counter_max u32=1048576 / reserved u32=0 |

Each record offsets: sequence u64 at0; source/reason/hook/presence u32 at8/12/16/20; host TGID/TID u32 at24/28; registered tracee/target/request/ticket refs u64 at32/40/48/56; socket cookie/time_ns/cgroup_id u64 at64/72/80; reserved u64 zero at88. Source IDs1..4 are admission/kernel/controller/lifecycle; reason IDs1..27 are EXACT Reason declaration order, including over_bounds18/enforcement_attempt20. Hook IDs1..10 are KernelHook order; zero means absent. Presence bits1/2/4/8/16/32/64/128 respectively mark TGID,TID,tracee,target,request,ticket,cookie,time; absent fields zero, unknown bits invalid. Cgroup ID ALWAYS matches header. Private refs resolved only by owning registry, never inferred from arbitrary integers. Kernel IRQ packets may lack TID/tracee; hook/attachment/map binding remains exact. Dense immutable records are1..last_sequence=record_count; all unused records zero. kernel_refusals counts source-kernel records/attempts, hook counts only matching real hook denials; saturation/full history is explicitly nonclean, never hidden by an equality.

Inventory HASH has u64 nonzero-cookie key, 32-byte value: launch_ref/operation_ref/state/reserved u64 at0/8/16/24. Live state1, atomically claimed retired state2; zero reserved; BPF_NOEXIST insertion, never replacement/LRU. Separate one-entry syscall-RO lifetime ARRAY value256: format u32=220/reserved u32=0 at0/4; launch/operation nonces[16] at8/24; cgroup u64 at40; created/destructed/error_bits u64 at48/56/64; bytes72..255 zero. Atomic count increments use bounded sixteen-attempt CAS, cap1048576; overflow/contention/unknown state sets permanent lifetime error. FEXIT cannot use spinlocks. Combined declared map values98,560+32,768+256=131,584 bytes within ledger_bytes_max262144; keys/internal kernel allocator overhead additionally bounded by fixed capacities and verified map metadata. No mutable user descriptor ever exists for any map.

Private SCHED_CLS committer input/output is EXACT174 bytes: fourteen-byte Ethernet header (zero MACs, EtherType88b5) plus160-byte command; Linux6.8 SCHED_CLS TEST_RUN restores L2 before execution, no real send. Command offsets0/4 are format220/opcode u32 (INIT1,APPEND2,SEAL3); launch/operation nonces[16] at8/24; cgroup u64 at40; observed_sequence_floor/assigned_sequence u64 at48/56; fixed body96 at64. Input assigned_sequence zero. INIT body is policy SHA256[32], followed capacity/counter_max/ledger_value_bytes/inventory_capacity/inventory_value_bytes/lifetime_value_bytes/program_count u32=1024/1048576/98560/1024/32/256/12, then36 zero bytes. One-shot INIT before attachments initializes both ARRAY identities/constants; fresh HASH empty. APPEND body is exact record template with sequence zero; validate enums/refs/identity before private dispatch, kernel checks nonce/cgroup/format/reserved again. Current sequence must be >= observed floor; concurrent kernel records take precedence, so APPEND assigns current+1, not expected floor+1. SEAL body zero and current==floor/active_hooks==0/live_inet==0 plus independently proved retired creators/objects/controller required.

TEST_RUN uses repeat1/flags0/cpu0/batch_size0/no supplied ctx, fixed174-byte buffers. Load bounded packet fields into aligned stack BEFORE map spinlock; no helper under lock. Record/sequence publication under lock; after unlock store assigned sequence into output. Syscall success AND program retval0 AND exact output/header AND locked matching immutable record are required for APPEND ACK; otherwise sticky uncertainty, no resume/success. Protocol error retval2 sets permanent integrity when possible, sequence zero; valid INIT/SEAL ACK additionally validated locked state. INIT/SEAL emit no refusal/reset; all later INIT/after-seal APPEND fail. Only private owner invokes committer; no packet/context/string/model-controlled opcode. Kernel source via committer restricted to authenticated syscall-entry/notification messages; ordinary public commit_refusal source remains admission/controller/lifecycle. Match/deduplicate notification ticket to its already-committed entry without assigning a second event; unknown receipt still commits then errors, never drops it.


active_hooks is in-flight CGROUP callbacks, NOT attachment count or invented composite. After key0 lookup, lock/increment before context/cookie/lifetime helpers; unlock, gather fixed data; final lock publishes counters/record and decrements, unlock, return. Every increment has paired decrement on all branches; no helper/subprogram under lock. Missing admission/transmission lookup denies; release always return1 for cleanup and nonclean failure. Permanent errors survive missing identity/readability/overflow. Packet TID optional, exact hook/attachment/map binds launch. A locked zero active count alone is NOT retirement: pre-lock callbacks can exist, so ten exact detach/query0 AND GLOBAL RCU remain mandatory. Lifetime ARRAY separate atomics, never tracing spinlock.

Counters saturate at kernel_counter_max, permanent overflow/integrity. Metadata create/bind/UDP-connect increments only initialized/unsealed/healthy/below cap; otherwise append refusal when room, permanent failure, return0. Full-ledger real denials ALWAYS deny/drop and mark overflow, never pretend lossless clean. Release always return1 for cleanup, saturating/erroring underflow. Metadata counts consume no refusal record and never reset; live_inet=created-released. Constant ARRAY key0/owned lifetime is invariant, not eviction fallback.

resource_events comes from SAME retained cgroup pids.events/memory.events FDs, not invented ARRAY bytes: five enum keys/bounded monotonic uint64/no reset/foreign file. Read startup, before output/host refusal, terminal barrier. pids_max or memory OOM/kill/group-kill permanently invalidates clean and coalesces one lifecycle over_bounds record; retain exact growing counts. Import via private committer, not recursive commit_refusal/refresh. Disappearance/decrease/unknown chronology adds accounting error: no retrospective first-refusal certainty. memory_max reclaim is metadata unless denial; CPU throttling metadata. No failed native allocation/fork silently retried into clean. Final zero-denial resource values supplement kernel ledger.

**Host events share that commit.** Load ONE private BPF_PROG_TYPE_SCHED_CLS3 committer, never attached to a device. BPF_PROG_TEST_RUN repeat1 accepts a bounded synthetic fixed-size Ethernet-envelope payload of registered event/ticket/request refs. Append under lock, copy assigned sequence to bounded data_out after unlock, and validate data_out AND locked immutable record BEFORE ACK/Fetch.failRequest. This executes kernel commit but sends no packet. No socket-filter/tracing helper compatibility is assumed. After one-shot INIT permit append/seal only; never reset/delete and no model/tracee FD access. All admission/controller/lifecycle/reader/pre-resume events share ONE sequence. Hooks commit if observer dies; refresh imports every dense record and preserves first refusal. Failed commit/ACK/read retains sticky local uncertainty, forbidding complete/clean proof.

**Final socket objects, not file-close inference.** INET_SOCK_RELEASE runs BEFORE protocol close and is insufficient for producer retirement. Before the FIRST stopped launch child enters the leaf/bwrap exec, also install a readonly-user non-evicting HASH keyed by nonzero kernel socket cookie (max socket_inventory_max, fixed32-byte state/owned token), readonly-user key0 lifetime ARRAY without spinlock, and ONE BPF_PROG_TYPE_TRACING program linked as BPF_TRACE_FEXIT to selected kernel BTF FUNC inet_sock_destruct. IPv6 calls the same final function after inet6 cleanup. Bounded actual vmlinux BTF supplies/validates function/field/enum offsets and hash; no guessed struct layout/kprobe/tracepoint fallback. Every successful sock_create obtains cookie, inserts BPF_NOEXIST owned LIVE state and mirrors created count BEFORE ALLOW. Failure/full/duplicate/zero cookie marks integrity, commits denial and cannot yield complete proof. Release only tracks file count; no inventory deletion at release.

FEXIT reads nonmutating cookie; foreign/readmiss does NOT allocate cookie/write. Owned unreadable object leaves inventory/count mismatch, hence no complete proof. Match private token then actual BTF final fields: sk_type; __sk_common.skc_state TCP_CLOSE for STREAM; sk_flags SOCK_DEAD bit; skc_refcnt/rmem/wmem ref counters, wmem_queued/forward_alloc and receive/error queue qlen zero. Resolve types/widths/offsets/enums from selected actual BTF, no guessed layouts. Validate before CAS LIVE→RETIRED; delete matching inventory key FIRST, then publish destructed as LAST successful map write, exit with no later mutation. Failed read/state/delete/CAS/counter records permanent error before any completion publication, never fabricates retirement. Accepted keys globally unique/never replaced, one inet_sock_destruct per owned object, create published before visibility; duplicate/unknown ownership cannot clean. Stable equality created=ledger.created_inet=destructed PLUS inventory0/error0/no creators required, not empty HASH alone.

Lifetime error_bits pinned:1 owned final-field read/BTF mismatch;2 zero/duplicate CREATE cookie;4 inventory insert/full;8 token/state mismatch;16 duplicate retirement/CAS;32 final conditions;64 delete failure;128 count overflow;256 sixteen-CAS contention exhaustion. Unknown bits invalid. Unreadable foreign/unknown cookie writes nothing; missing lifetime ARRAY cannot invent error write and prevents retirement/complete owner read. TCP_CLOSE applies ONLY STREAM; UDP state unconstrained, DEAD/queue/memory conditions still mandatory. Real connected/corked IPv4/6 UDP destruction is an unproved runtime oracle. After creators end, require two identical bounded lifetime reads plus full empty HASH enumeration, matched identities/counts/error0. Repetition alone is NOT quiescence: last-write destructor invariant and cgroup detach/GLOBAL/final owner-close provide it.

**Retire, detach, RCU, release, seal.** Keep ten classic guards and destructor tracking through graceful close/sealed-resume kill/all task/exec/thread/process/pidfd/cgroup/helper outcomes. Require no restart, created_inet=released_inet/live_inet0 AND mirrored created=destructed/inventory0/no lifetime error (queued/duplicated/SCM_RIGHTS refs included). Detach each EXACT classic program via BPF_PROG_DETACH command9 with target_fd, matching attach_bpf_fd and attach_type (detach2 form, not an invented DETACH2 command); query effective IDs0. Detach is not quiescence: independently owned bounded helper issues MEMBARRIER_CMD_GLOBAL flags0, QUERY bit/success required; selected Linux6.8's multicore RCU grace period covers prior cgroup execution, uniprocessor has no concurrent other CPU. No EXPEDITED/sleep substitute.

Then close the SOLE owned fexit link FD and permanently invalidate its registered handle; no dup/pin/transfer/persistent helper inheritance. BPF_LINK_DETACH on tracing is unsupported95 and MUST NOT be used/claimed, nor pretend a cgroup query proves tracing unlink. Kernel last-FD release owns tracing unlink; old callbacks may retire asynchronously but every matched callback already published retirement/deleted its key with NO later accounting write, no tracked objects/re-creators remain, and unrelated host callbacks only miss private inventory/read-return. GLOBAL is NOT a tracing-RCU proof: object/dataflow retirement provides its separate no-future-write invariant. Retain program/all-map FDs through proof; actual release failure/unknown extra reference/late writer/timeout/nohz_full is nonclean and retains outside ownership. Normal checks do not re-open/dup the fexit link.

After object/classic-detach/RCU/tracing-owner-release barriers, zero active cgroup hooks and retired host callbacks/reader/refusal writers, private committer SEAL. Locked refusal snapshot plus stable atomic lifetime/inventory state validate exact root/launch/maps/BTF/program/attachment/policy, dense sequence, matching created/destructed/released, no overflow/errors and sealed. Register KernelSocketRetirementProof.link_fd_closed inside KernelLedgerProof.attachments_detached/rcu_barrier_complete; sockets_released is actual object proof, never file count. Post-seal append permanently errors/refuses; actual producer/writer barriers forbid later writes. No clean postmortem/empty-queue/freeze inference. Hold FDs until registered proof/receipt frozen; classic kernel refs protect denial if owner dies before then, but lost observation never becomes clean.

**Measured primitives, unproved product:** Main observed readonly spinlock ARRAY/updateEPERM/locked lookup/SCHED_CLS committer, ten hook types/IPv4+IPv6 UDP operation denial; normal readonly cookie HASH+atomic ARRAY/FEXIT finalization and unsupported tracing explicit detach; classic attachments persist after user program-FD close and detach2/query succeeds. None proves full schema/ACK/overflow/concurrency/DEAD-CLOSE-queue/dataflow retirement/native browser. Require selected UAPI/IPv4+IPv6/RCU/BTF, full verifier/helpers/atomics, authorized CAP_BPF+NET_ADMIN+PERFMON or SYS_ADMIN equivalence, bounded kernel memory, readonly ARRAY/HASH/test-run, exclusive delegated persistent attachment lifecycle, GLOBAL without nohz_full, and bounded actual vmlinux BTF/typed FEXIT/sole-owner release. Emit bounded stdlib eBPF/BTF, no install/compiler/global toolchain. Exact-digest review and full-profile startup/R09–R12 still required; necessary native connect/send/packet refusal requires real profile correction/re-gate, never exemption/reset/relabel/nonfunctional acceptance.

### 5.3 Launch values and ordering

Exact argv after executable: `--headless=new`, `--remote-debugging-pipe`, `--user-data-dir=/tmp/profile`, `--window-size=1280,720`, `--disable-gpu`, `--disable-dev-shm-usage`, `--no-first-run`, `--no-default-browser-check`, `--disable-background-networking`, `--disable-component-update`, `--disable-sync`, `--disable-domain-reliability`, `--disable-quic`, `--no-pings`, `--disable-breakpad`, `--force-webrtc-ip-handling-policy=disable_non_proxied_udp`, `--disable-features=InterestFeedContentSuggestions,SpeculativePrefetch,NetworkTimeService,Prerender2`, `--host-resolver-rules=MAP * ~NOTFOUND`, `about:blank`. Resolver rule is ONE literal argv element, not shell split. Host resolver unaffected. No Playwright defaults/sandbox disabling; trusted Playwright probe chromium_sandbox=True. Uniform native-DNS suppression is not attempted-denial evidence; mediated original URL/origin/HTTP/cookie/CORS remains real.

Reject sandbox-disabling, web-security-disabling, TLS-ignore, user profile/extension, proxy, remote-debugging-port, external protocol and arbitrary extra arguments. Do not add a switch to make a failing positive case pass without contract revision. Background DNS/preconnect/reporting/network-time/DoH attempts are still constrained; a flag is neither enforcement nor proof of attempted denial.

Startup sequence (fixes the impossible “verified before browser exec” requirement):

1. BEFORE first child/bwrap exec: register root/lifecycle scope, validate manifest/config/env/FD/namespace/cgroup/BPF/BTF/ptrace/LSM prerequisites; INIT readonly maps/committer, install ten persistent classic bindings and exact sole-owner FEXIT tracker. Move ONLY stopped FD-sanitized child into leaf before exec, no preexisting INET/import escape. Trusted bwrap isolates namespaces; verify post-bwrap bootstrap pidfd/identity, SEIZE/INTERRUPT synchronous tracing/independent reader/acknowledged scalar filter before native exec. Failure tears down/not_configured, no missing-guard/untraced/untracked alternative.
2. Exec the native browser in that boundary with only trusted `about:blank`. No untrusted URL/content has been supplied. Start the bounded pipe parser; install browser-wide discovery/flattened recursive auto-attach and paused-target handlers.
3. INSIDE the already-running boundary, visit trusted `chrome://sandbox` only for startup verification, obtain namespace/Seccomp-BPF/TSYNC status and corroborate process namespace/capability/filter identities. This is not an arbitrary tool navigation permission. Close that trusted target, discard its context and create the user context. Native sandbox failure after exec means abort/reap and `sandbox_unverified`, not a raw/relaxed relaunch.
4. ACK Fetch/Network/recursive pause/callback registration before user resume. Refresh kernel/resource snapshot; register StartupProof matching root/launch/native sandbox/namespace/filter/ptrace/policy/ten bindings/socket-retirement/maps/committer/owned DNS+UTS and zero refusals/errors/resource denials. Nonzero inert create/bind/UDP-connect counts retained forever. Prohibited bootstrap TCP/other connect/send/packet/scalar/resource refusal invalidates startup; no replaced map/profile for user context.
5. Only now may `start()` succeed and untrusted navigation begin. Positive completion requires actual allowed content, never about:blank, an error page, a failed startup, empty bytes or `not_configured`.

Compute immutable profile/policy from actual sealed executable/manifest, fixed argv/env/namespace topology/UID/caps/FD roles, scalar ABI, verified BPF/BTF semantics/schema and every resource/queue/decoder bound (pids256, uniform UDP predicate/nativeDNS/UTS). Map-FD relocations canonicalized to exact registered map roles; no embedded per-launch nonce/cgroup ID in code. Actual instance nonce/PID/namespace/cgroup/map/program/link IDs are separately verified StartupProof/bindings, not a changeable profile selector. Same selected runtime's R09/R10/R11/R12 use identical immutable profile, no positive-only switch/limit/manifest/guard. Caller string never authority; old128/strict-connect diagnostics grant no acceptance.

## 6. Native HTTP, target coverage and sticky refusal

One pipe/controller owns all CDP IDs and target sessions. Use bounded NUL-delimited framing, check byte cap and JSON nesting before materialization, restrict known message shapes and command IDs, and cap target/request/callback/notification queues before insertion. Outbound fulfilment size accounts for base64 plus headers/JSON; input/output caps are consistent with `decoded_max`, not an impossible 8 MiB message cap on a 16 MiB entity. Log overflow latches a resource refusal and terminates, rather than blocking a writer or retaining unlimited output.

On browser attach and recursively on each page/iframe/OOPIF/dedicated worker/shared worker/prerender target: `Target.setAutoAttach(autoAttach=true,waitForDebuggerOnStart=true,flatten=true)`; `Fetch.enable(patterns=[{urlPattern:"*",requestStage:"Request"}],handleAuthRequests=true)`; Network events and bounded callbacks registered; only then `Runtime.runIfWaitingForDebugger`. Unknown/foreign/service-worker targets are refused before resume. No native network continue fallback for missing networkId/frameId, redirects, preflight, worker or unknown target. Disabled prerender is not proof of interception; an available prerender target must either be covered before resume or produce explicit refusal.

`Fetch.requestPaused.request.headers` is the sole outbound native Cookie/Authorization source. This is the primitive behind the documented `all_headers()` that Main measured; do NOT use the documented-incomplete `Request.headers` convenience property. Convert CDP map newline-separated repeated fields to validated ordered pairs; it does not prove original cross-name wire order. Absent Cookie means send none, never query the cookie store to manufacture a header. ExtraInfo is diagnostic-only. Preserve native credentials mode, SameSite/Secure/HttpOnly/domain/path and partition decisions; positive/negative runtime cases below are mandatory, not inferred from two cookies.

Every paused HTTP(S) request builds a bounded complete HttpRequest and calls `transport.open_scope(operation=session.scope.operation,parent=session.scope,deadline_at=min(navigation_deadline,exchange_deadline))`, then a fresh permit/connection on that same authority. With aggregate storage reserved, fetch a complete encoded SafeResponse and call `transport.decode_response(response,request=request,scope=scope,budget=reserved_decode_budget)`; fulfil only its DecodedResponse. A failure first latches and then fails the request. Decode every `postDataEntries.bytes` item exactly; if `hasPostData` requires data and any entry is missing/file-backed/unavailable, refuse `unsupported_body_metadata`. No filtering away missing entries or substituting text. No Fetch.continueRequest, Playwright route/fetch, browser-native retry, local decompressor or raw transport.

Fulfil with separate `responseHeaders` entries (or CDP binaryResponseHeaders for non-UTF8 values), never comma-joined Set-Cookie. Native Chromium handles cookies, original/final URL, document origin, redirects, method transitions and CORS. Preflight is an ordinary real mediated OPTIONS exchange; return the origin's real response without manufactured ACAO/ACAC. Positive credentialed CORS and denied CORS must both be exercised. No URL rewriting to a local service and no TLS-ignore: original-host certificate validation and actual peer verification happen at the host transport before any HTTPS response is given to Chromium.

HTTP auth prompts/cache and client certificates are not supported: pass through 401/WWW-Authenticate, supply no host credentials, answer any Fetch auth challenge CancelAuth. Explicit native Authorization in a request is preserved to that request only; never carry it or Cookie over to the next origin manually.

Bypass enforcement and visibility:

| Channel/path | Mandatory control and non-clean oracle |
|---|---|
| Redirect/frame/resource/XHR/fetch/meta/popup/later navigation/worker/preflight | Fresh admission/actual peer on each request; failure event sequenced before Fetch.failRequest. Missing attachment/interception is an enforcement failure, not blank success. |
| WebSocket/WSS, CONNECT, 101/upgrades, WebTransport and other protocols | Refuse at observed request/Network event; actual connect/send/packet hooks prevent missed native traffic; durable refusal survives page catches. |
| QUIC/UDP, WebRTC/STUN, DoH/native DNS, preconnect/missed Fetch | Uniform native DNS disabled; observed HTTP still same admission. TCP/other connect, UDP send and connected-UDP packet output commit/deny independently of CDP. Earlier-native-denied/suppressed/unavailable distinct from exercised hook. Inert create/bind/UDP association is metadata, not denial/startup exemption. |
| Service worker registration/foreign target | Observe target/registration events, latch and terminate before resume; merely setting service_workers=block or swallowing an exception is insufficient. |
| Prefetch, Reporting/NEL, beacon/keepalive, network-time/component/variations traffic | Same fresh admission when observed; genuine native connect/send/packet denial commits and invalidates session. Pinned suppression is not exercised enforcement; no benign-class waiver or count reset. |
| Inherited FD, outside Unix/SCM_RIGHTS, ABI/import/io_uring or namespace escape | FD sanitation, sealed private files/private abstract IPC, no join/mount/import, scalar filter/pre-resume ledger and descendant ownership; independent R10 evidence. |


The outside owner imports ONE kernel-committed sequence, not a parallel userspace lock/counter. Every host event commits through the private committer before reply; scalar tickets precede resume, notification latches precede ID_VALID, actual hooks commit before denial returns. First refusal is write-once at the lowest sequence. Refresh before adapter output, every acknowledgement and final receipt so delayed imports cannot change attribution. Later failures append bounded safe errors. Invalid/unanswerable received notification, unexplained ESRCH/loss, map/tracer/reader/producer failure or ownership uncertainty can never become clean. Successful screenshot, page catches, detach, close and repeated close cannot clear history.

## 7. Lifecycle, abort, terminal receipt and composition

States: NEW → STARTING → READY → CLOSING → CLOSED; any failure commits refusal and proceeds to CLOSING. One synchronous worker owns adapter operations; separate tracer/observer/watchdog/abort signaling stay runnable while it is blocked. A registered review/navigation root begins BEFORE dispatch with an absolute60 s cap, preview/snapshot-only roots with15 s. Startup15 s/navigation30 s are additional caps, never extensions. Each request inherits parents/root abort. Expiration/cancellation starts one fixed maximum5 s cleanup deadline; retries/repeated close/finish cannot reset it. No new work uses cleanup time, and normal scope retirement is not root cancellation.

Close is active, not suppressed finally: stop admission/user work, abort/close request scopes/connections/resolvers, fail pending requests and preserve supervision/observer/callback pumping for bounded graceful shutdown. Seal resumes, kill survivors, reconcile/reap all descendants/exec identities, retire reader/pipe/notifications/ACKs/callbacks and close controller (commit any error BEFORE ledger seal). Keep ten kernel guards/destructor tracking through actual object retirement; finish_kernel_ledger obtains §5.2b object/attachment/RCU/host-writer/seal proof, then finish_accounting and freeze registered receipt. last_sequence is final durable sequence, not quiet time. Clean requires ALL DrainState booleans INCLUDING accounting_complete/kernel_ledger_complete, zero pending counts, exact root/startup/launch/trace/kernel proofs, zero-refusal counters/records and no errors. Process death, queues empty or file-release count alone is insufficient.

If kernel task/socket-object retirement or bounded RCU/reap cannot be confirmed by the drain deadline, report cleanup_failed, retain ledger/watchdog/admission/dispatch-slot ownership and escalate to Main. Never release an unsafe slot or fabricate clean proof. Cooperative/forced cases must finish within lifecycle/deadline +5 s with ≤1 s scheduling tolerance. Owner death produces independently observed teardown, never a postmortem clean receipt.

Composition types: WebContext retains root/vercel/vision/artifacts_dir and adds `policy: SeatPolicy | None`, `transport: DestinationTransport | None`, `fetch: SafeFetch | None`, `browser_factory: GuardedBrowserFactory | None`. Construction checks same policy/transport/authority object identity, including factory registry membership. `default_registry` builds one transport, SafeFetch and factory from host config. None policy cannot be replaced by an injected permissive fetch or factory. Missing config errors must occur without a network attempt.


`review_page`: resolve ONE registered root → preview with that root → factory.create_session(operation=root)/start → admitted render → staged real PNG → ALWAYS close → validate own exact factory/session/root/authority/startup/receipt/trace/kernel identities and clean drain → finish_operation on that SAME root and require complete/no pending/no errors/no abort drain → directly recheck current abort_handle.reason and the inherited absolute work deadline → vision. Never call remaining() or allocate new scopes after root finish. Recheck current abort/deadline again before final public publication. Refusal/late event/failed cleanup/foreign proof invalidates staged page/PNG, returns top-level error with `{ok:false,errors}` close outcome and calls vision zero times when detected before invocation. Successful keys remain `url,connectivity,page,screenshot,vision`; preview keys remain `url,host,status,expected,matches,ms,content_type,body_sha256,bytes,redirect`.

### 7.1 Exact sync/MCP root binding and caller migration

WebClient internal signatures are `preview_check(self,url,expect_status=200,*,operation:RootOperation|None=None)` and `review_page(self,url,question,expect_status=200,name=None,*,operation:RootOperation|None=None)`; never add operation to tool JSON. Resolve explicit root, else ctx.transport.current_operation(), else native-sync begin_operation; reject foreign/conflicting bound root. Bind native-owned root and always finish it. Preview borrowed by review must NOT finalize between preview/browsing. Review MUST finish its same root, even borrowed/bound, before vision/public success; outer coordinator repeats the identical registered frozen drain. Preview-only external owner finishes before publication. Creator retains dispatch-slot ownership and finalizes idempotently; inner finishing grants no new-work authority.

`mcp_server.py` owns `bind_dispatch_transport(registry:ToolRegistry,transport:DestinationTransport)->None` and private weak registry→serial-coordinator mapping. default_registry binds SAME transport used by WebContext/SafeFetch/factory; trusted hosts/tests injecting BrowserSession bind factory.transport explicitly. Different rebinding refuses. ToolRegistry/platform.py need no source edits. Affected web_preview_check/web_review_page/browser_navigate/browser_snapshot without binding return not_configured before handler; never closure-inspect for authority.

For those affected calls, the coordinator creates/registers the root and records its abort handle on the event-loop side BEFORE executor submission or registry.dispatch; queue wait counts against its absolute deadline (15 s preview/snapshot, 60 s review/navigation). Bound the serial queue to 16 pending operations before allocating another root. Inside the actual worker enter `transport.bind_operation(root)` around existing registry.dispatch; ordinary tool closures then reach the explicitly declared current_operation API. Preserve roster/approval checks and dictionary-error→is_error mapping, including no-roster not widening destination authority. Other tool families are not claimed to acquire this browser/transport containment.


Async cancellation immediately aborts the captured root, including queue wait/initial preview before session creation. Shield/await worker cleanup and finish_operation with the one fixed cleanup deadline before publishing failure or advancing slot; repeated cancellation cannot interrupt/reset cleanup. Normal completion also finishes/unregisters before external success; a worker review/direct wrapper may already have finished that SAME root. Verify exact returned frozen OperationDrain.complete, zero pending_scopes/errors and no saved abort; directly check CURRENT abort_handle.reason and original absolute work deadline immediately before publication, never remaining() on finished root. A cancelled queued root never enters handler/network. Failed cleanup poisons coordinator and retains watchdog/slot ownership. Future.cancel/polling is not registered-work abort wakeup.

### 7.2 Direct BrowserSession terminal publication and snapshot follow-up

`browser.py` owns `BrowserSession(factory:GuardedBrowserFactory|None)`, `browser_navigate(self,url,*,operation:RootOperation|None=None)` and `browser_snapshot(self,*,operation:RootOperation|None=None)`. Factory ownership is mandatory; arbitrary injected page/transport objects are removed. Keep unavailable-default behavior and platform.py's existing delegating closures/tool schemas unchanged. Resolve roots through factory.transport with the same explicit/bound/native-owned rules as §7.1.


Each navigate clears prior cache FIRST, creates a registered session under the resolved root, and stages start → navigate → snapshot privately. ALWAYS close; validate factory.owns(session,receipt), exact root/authority/session/launch/startup/trace/kernel identities, complete proofs/receipt.clean and successful public close. Then finish that SAME operation EVEN borrowed/bound; require its exact registered complete OperationDrain with no pending/error/abort, directly check CURRENT abort reason/original absolute work deadline, and only then return existing `{url:requested_url,page:navigate_result}`. Retain copied immutable title/url plus exact session/receipt/historical root/drain; no live browser. Failure/queued or late refusal/foreign receipt/failed close/cancellation/uncertain cleanup returns top-level error and leaves no cache. Returned-dict mutation cannot alter retained scalars/identity. Coordinator repeats idempotent finish, not a second cleanup/root.

Follow-up snapshot does NO browser operation. Require retained registered clean terminal receipt and matching saved factory/session/historical root, its exact complete retained OperationDrain with no errors/abort, and historical root's CURRENT abort_handle.reason still None. Active-work unregistration is expected; never remaining() on historical finished root, ignore historical elapsed work deadline for cache lookup, and never mint a receipt. Resolve/bind a distinct CURRENT snapshot publication operation, check current cancellation/deadline, then finish it EVEN borrowed/bound before returning cached scalars; require registered complete/error-free/no-pending drain and current abort/deadline check. MCP repeats finish idempotently. Missing/unfinished/failed/mismatched historical cache or current failure returns top-level error. Return unchanged `{page:{title,url}}` only from finalized data; new failed navigation never falls back to old cache. No later live-browser refusal is used to retract a published success.

## 8. Full caller inventory and disjoint implementation DAG

Source-search inventory (not a claim about arbitrary external Python programs):

| Caller/seam | Disposition and owner |
|---|---|
| `webpack.py` `_check_url`, `_default_fetch`, `NoRedirects`, allowed_hosts, preview fallback, bare browser fallback and suppressed close | 46-02/46-04 sole FetchIntegration writer removes these; typed authority/receipt replaces them without shims. |
| `mcp_server.py:145,161,220-243,312-314` | Same writer: exact policy/config construction, serial dispatch/cancel, no-roster cannot change destination authority. Platform browser remains unconfigured by default; do not invent a new integration. |
| `playwright_browser.py:16-43` direct `_default_launch` and `PlaywrightBrowser(launch=...)` | 46-03 BrowserSafety removes unchecked direct constructor/tuple acceptance; only registered factory constructs. This importable direct launch is in scope, not just web_review_page. |
| `browser.py` BrowserSession; `platform.py:27-67` injected direct browser tools | BrowserSafety migrates to owned terminal navigate/close/proof/root-drain publication and immutable finalized snapshot cache; failures are top-level. Unavailable default and delegating schemas stay unchanged; platform.py does not launch. No direct live/provisional session result escapes. |
| `test_web.py` `_ctx`, allowed_hosts, fetch lambdas, launch lambdas and adapter lifecycle assertions | FetchIntegration migrates every legacy test dependency to the accepted typed/factory seam; no permissive compatibility constructor. |
| `test_platform.py:205-231` arbitrary `_Page` BrowserSession injection | BrowserSafety migrates to its private owned-session test fixture and tests direct terminal failure propagation/cached snapshot behavior. |
| `test_growth.py:578`, `test_providers.py:335` WebContext(root=...) registration | Intentionally unchanged: registration-only use remains valid; missing-policy network calls now deny. Main runs these composition suites for LAND-02. |
| `pyproject.toml:28`, `requirements-lock.txt:88` Playwright | Retained for existing provisioning/discovery; no packaging change/install. Module/operator docs must explain raw-pipe runtime vs discovery. |
| `docs/tool-host.md`, `docs/architecture.md`, `SECURITY.md`, `CHANGELOG.md` | 46-05 only, after implementation and observed receipts. Historical planning/.swarm/Phase52 files unchanged. |

| Plan / owner | Wave / needs | Exclusive product/test paths (≤5 per unit) |
|---|---|---|
| 46-02 FetchIntegration | 1, accepted typed contract | `omes/providers/destination.py`, `omes/tools/webpack.py`, `omes/mcp_server.py`, `omes/tests/test_web.py`, `omes/tests/test_mcp_server.py` |
| 46-03 BrowserSafety | 1, same accepted typed contract; parallel with 46-02 | `omes/tools/browser_egress.py`, `omes/tools/playwright_browser.py`, `omes/tools/browser.py`, `omes/tests/test_browser_egress.py`, `omes/tests/test_platform.py` |
| 46-04 FetchIntegration | 2, real 46-02 + 46-03 handoffs | `omes/tools/webpack.py`, `omes/mcp_server.py`, `omes/tests/test_web.py`, `omes/tests/test_mcp_server.py` |
| 46-05 Docs | 3, 46-04 plus Main receipts/independent security disposition | four documentation paths above |

Browser writer may author against postponed shared protocols while destination.py is concurrently written; never create a substitute module or await full transport to start. Each task authors behavioral regressions. D-05/D-07 override native tracer/TDD execution recipes: children author behavior-first production/tests only; no RED/GREEN/test/smoke/lint/format/install/Git commands, task commits, trackers or .swarm changes. Main runs union ONCE after both writers and 46-04 composition land, then independent exact-digest gates. Plan must_haves use native artifact objects with path/provides and key_links with from/to/via/pattern; plan metadata never substitutes for runtime receipts.

## 9. Regression obligations, authoring and executable evidence

All tests are durable cases in the named exclusive files. Hermetic pytest cases run production logic with controlled low-level resolver/socket/clock/controller/kernel-event fixtures: exercise decisions, response bytes, ownership and state transitions, not source text, incidental attribute presence or copied implementation logic. They do not claim real Chromium/TLS/kernel evidence. Separate `--runtime` entrypoints in the SAME test files must implement actual offline isolated fixtures; they are executable tests, not receipt templates. Default pytest never launches a browser or network fixture. Main alone runs either tier after writers stop.

Every row carries `ac`/`check`: **F** = AC-OMEGA-V9-01 / LAND-01/T-46-08-hermetic-transport-regressions; **B** = AC-OMEGA-V9-02 / LAND-01/T-46-12-independent-browser-egress-regressions. These identifiers belong in test parametrization IDs/receipt case IDs, not assertions that metadata exists.

| ID / trace | Sole author / file | Required behavioral oracle |
|---|---|---|
| P46-R01 / F | FetchIntegration / test_web.py; registry subset test_mcp_server.py | None/empty/unlisted/implied-subdomain deny before resolver/dial/browser. Exact mixed-case policy allows; approvals and no-roster never broaden it. |
| P46-R02 / F | FetchIntegration / test_web.py | All-public A/AAAA allowed; every ordering of mixed/nonpublic/special-use/malformed/empty/error rejects before dial. All listed exclusions tested on actual three interpreters. |
| P46-R03 / F | FetchIntegration / test_web.py | All ambiguous numeric/authority spellings and CTL/SP/non-ASCII serialized targets reject; canonical policy-matching DNS/IPv4/IPv6 positives work. |
| P46-R04 / F | FetchIntegration / test_web.py | Changing-second-lookup resolver called once; subsequent request re-admits changed answers; foreign/copied/consumed/expired/scope-mismatched permit rejects; exact raw/wrapped peer/family/port checks. Real numeric sockets complement hermetic faults. |
| P46-R05 / F | FetchIntegration / test_web.py | Original DNS/IP TLS and wrong-host/untrusted cert before HTTP; exact Host/method/form/JSON/NUL bytes; framing conflicts/HEAD/204/304/interims/multiple Location/body metadata/target chars. Real test-only CA, never disabled verification. SAME typed decode_response verifies identity/budgets/deadline, complete-vs-sample refusal even EOF, entity vs HEAD/204/304 semantics, correct encoded/decoded/base64 counts and bounded scratch; foreign/consumed authorization and malformed/truncated/bomb failures. |
| P46-R06 / F | FetchIntegration / test_web.py | Hostile proxy env ignored, zero proxy/redirect-target requests; 301/302/303/307/308 no-follow; unchanged preview headers/hash/bytes/sample; CONNECT/101/upgrade and bad response framing refuse. |
| P46-R07 / F+B | FetchIntegration / test_web.py + test_mcp_server.py (sync/async partition) | Preserve denied preview, foreign/missing session/factory/receipt, partial start, late screenshot/close refusal, observer/controller/supervisor loss, cleanup failure and repeated close. Force pre-submission root registration, queue wait/cancel, initial-preview resolver/socket cancellation before session, decode/start/nav/cleanup cancellation, repeated cancellation and bounded serial dispatch. Same-root idempotent complete drain before vision/external success; no remaining() after finish, current abort/deadline recheck, no premature slot release. Zero vision/is_error for pre-vision failures. |
| P46-R08 / B | BrowserSafety / test_browser_egress.py; direct subset test_platform.py | Real admitted page THEN redirects, iframe/OOPIF, image/script/style/media, XHR/fetch/meta/popup/later/history/script nav, dedicated/shared worker/prerender/attach races. Redirect/resource/meta EACH host_policy/nonpublic-or-mixed/peer_mismatch with correct reason and zero forbidden HTTP. Direct navigate queued/late/close/foreign-proof failure blocks every provisional success/cache; successful finalized owned receipt/root drain enables immutable cached snapshot without live session; historical current abort and current borrowed snapshot root finalization; failed replacement clears cache. |
| P46-R09 / B | BrowserSafety / test_browser_egress.py | Preserve actual alternate/missed/page-caught/late screenshot-close channels, DNS prefetch/preconnect, Reporting/NEL/DoH/beacon/keepalive/speculative/background/preflight. Distinguish suppressed/unavailable/native-earlier-denied from actual kernel hook denial. Force withdrawal/death BEFORE RECV and between RECV/ID_VALID; every received event latches regardless validity. Hold observer while actual hook commits denial and task dies: durable sequence survives. Scalar commit-before-resume/ACK; duplicate/foreign/malformed ACKs, ESRCH/unexplained loss/owner failures, map/record/counter saturation, mixed-source first ordering, failed committer/read, delayed imports and post-seal writers are nonclean. No quiet/empty history claim. |
| P46-R10 / B | BrowserSafety / test_browser_egress.py | Preserve installed ABI/x32/i386/socketcall when available; uniform UNIX/INET-STREAM+DGRAM/NETLINK matrix, raw/other-family/socketpair refusals; IPv4/6 connect/send and applicable write/writev/sendmmsg/sendfile/splice/cork/TFO/mapped/dup/descendant paths with actual outcome/zero forbidden packets. Inherited/duplicate/unconnected FD0..higher, external UNIX/SCM_RIGHTS, io_uring/imports, namespace/capability escape, proc reopen/PID1, keys/userfault/personality/dispatch/clone flags, inner-filter precedence, recursive socket/FIFO/device/symlink manifest, environment canary, owner-kill/double-fork/session ownership/reap. Verify readonly-from-create/INIT-once, kernel guards survive owner loss, cookie inventory registration→release→actual destructor (queued/shared refs), full maps/overflow, exact retirement/attachment removal/RCU, no host reachability and no weakened native sandbox. |
| P46-R11-RENDER / B | BrowserSafety / test_browser_egress.py | Real HTTP and verified HTTPS initial/frame/resource/script/style/image/popup/worker chains, actual final URL/origin/status/title and fixture pixels in a decoded PNG; completely clean immutable receipt under the SAME profile as negative tests. |
| P46-R11-BODY / B | BrowserSafety / test_browser_egress.py | Server-observed native POST form/JSON/binary and another method, exact bytes/content type/Host including IPv6/nondefault port; missing body metadata refuses. Transport halves exclusively R05. |
| P46-R11-COOKIES / B | BrowserSafety / test_browser_egress.py | Duplicate Set-Cookie including comma-bearing Expires; server-observed round trip; HttpOnly JS invisibility; path/domain/Secure/SameSite Lax/Strict/None; credentials omit/same-origin/include, cross-origin Authorization stripping, partitioned cookies under two top-level sites and configured third-party behavior. No hand-built cookie policy. |
| P46-R11-ENCODING / B | BrowserSafety / test_browser_egress.py | Real gzip/wrapped+raw-deflate resources use ONLY reserved DecodeBudget→transport.decode_response→DecodedResponse; correct fulfilment lengths, duplicate headers, HEAD/204/304/interim/Location semantics. Preserve malformed/unsupported/truncated encodings, encoded overflow, gzip/deflate bombs, streaming/open-ended/trickle, oversized CDP/log/queue/PNG; reservation covers encoded+decoded+base64+scratch+outbound/copied retention before allocation. No sampled fulfilment/local decoder. Transport-only decoder/framing cases exclusively R05/R06. |
| P46-R11-REDIRECT / B | BrowserSafety / test_browser_egress.py | GET/HEAD/POST across all five statuses; relative/cross-origin chains; native method/body transitions and independent admission, correct final origin/status. No target hits on denied hops. |
| P46-R11-CORS / B | BrowserSafety / test_browser_egress.py | Real server OPTIONS and original Origin/ACR headers; positive credential-aware preflight/response and native negative cases; denial must suppress actual request where native rules require. No fabricated CORS permissions. |
| P46-R11-BOUNDARY / B | BrowserSafety / test_browser_egress.py | Independent R09/R10 native/FD/import/descendant/withdrawal/real hook/owner-death/destructor on identical config/scalar/cgroup/manifest/executable; separate real clean positive with kernel/trace/root proof, retained inert create/bind/UDP-association counts, sequence0. DNS-disabled typed association primitive only supports feasibility; no relaxed positive profile/reset. |
| P46-R12-FETCH / F | FetchIntegration / test_web.py | Changed production WebClient fetch, exact-policy omega-rebind.example resolving to loopback: private_server_requests=[], private_response_received=false, safe refusal. Pair original BEFORE-FETCH without replay. |
| P46-R12-CHROMIUM / B | BrowserSafety / test_browser_egress.py (imports composed WebClient, no shared test edits) | Complete matched production review pair below. Runs only after 46-04 composition; authoring does not serialize wave 1. |

Deterministic held-response/paused-target/ptrace-ACK/RECV-before-ID_VALID/kernel-commit/observer-import/socket-destructor/RCU barriers replace sleeps. Force EACH withdrawal/death/abort/publication interleaving ≥20 times; a nondeterministic failure invalidates evidence (quarantine is diagnostic, never green). Fake clocks prove deadline arithmetic; actual runtime proves bound +≤1 s scheduling tolerance and host responsiveness. Synthetic BPF test-run/feature probes are not actual packet or full-lifetime evidence.

Runtime uses separate outer private net namespace with synthetic globally classified addresses and real HTTP/TLS servers; host transport there, browser in exact nested isolated no-route namespace WITH mandatory guards/native sandbox/full manifest. Controlled DNS is permitted, never loopback-as-public, patched peer checks or disabled TLS. Record actual socket/syscall/hook/peer/TLS/cgroup/BTF/filter/map/lifetime/receipt/render/body observations. Missing required fixture/ABI/authorization/positive/retirement is unsatisfied prerequisite, not blanket skip/pass.

Main alone runs the following AFTER implementation/composition writers stop. BEFORE any host test/browser/import, Main provisions fresh keyless HOME and XDG_DATA_HOME in distinct mode0700 children of one owned `/root/.hermes/cache/scratch` directory, removes inherited credential/proxy/SSH/DBus/display/provider environment, and records that isolation. Resolve trusted executable/runtime paths during controlled discovery before changing HOME; never reuse operator home/profile or mount scratch into Chromium. Product §5.1's private HOME=/tmp/home remains separate. Entry points below are implementation authoring requirements, not claimed present now; no child runs them:

```sh
.venv/bin/python -m pytest omes/tests/test_web.py omes/tests/test_mcp_server.py omes/tests/test_browser_egress.py omes/tests/test_platform.py -q -p no:cacheprovider
.venv/bin/python -m omes.tests.test_web --runtime P46-R04 P46-R05 P46-R12-FETCH
.venv/bin/python -m omes.tests.test_browser_egress --runtime P46-R08 P46-R09 P46-R10 P46-R11 P46-R12-CHROMIUM
```

The runtime CLI writes redacted structured receipts to stdout and exits nonzero on any violated oracle, omitted required subcase, unsupported required capability, unavailable positive page or unclean positive receipt. It performs actual fixture operations through product paths; no `not_configured`/mock/template success. Main records interpreter and candidate identity, and repeats with actual provisioned 3.13/3.14 interpreters; this document does not invent their paths.

### Exact R12 pairing and receipt fields

Preserve `/root/.omp/agent/sessions/-src-repos-Omes-Bot/2026-10-07T08-07-02-266Z_01a11566-d17a-71fc-9303-d0456a5234f3/local/omega-security-before.md`: BEFORE-FETCH lines 3–13 (JSON line 10), BEFORE-CHROMIUM lines 15–41 (JSON line 33). Fetch previously returned 200 from loopback; browser previously reached `/private-browser-probe` and closed `{ok:true}`. Neither before receipt proves today's profile. Do not rerun them.

R12-CHROMIUM records preview_status=200, initial_refusal=null, guarded_browser_started=true, exact StartupProof and real admitted/rendered public document, then fixture private-meta URL/matching paused request ID. FIRST refusal source=admission with meta request's exact public_code/internal_reason/request_id, sequence after initial admission and NO earlier scalar/hook/background refusal. Require private_server_requests=[], private_destination_reached=false, same first refusal after close, `{ok:false,errors}`, nonclean snapshot/screenshot/review and vision_calls=0. Map cleanup directly to receipt.drain.descendants_reaped/connections_closed/mediation_drained/notifications_drained/callbacks_finished/controller_closed/producers_stopped/accounting_complete/kernel_ledger_complete and all three pending counts0. Include registered complete receipt.accounting + kernel_ledger + socket_retirement proofs and SAME-root complete OperationDrain/pending_scopes0; complete teardown does not imply clean when refusal exists. Record terminal sequence/root/factory/session/authority/profile/map/program/BTF identities, not unrelated booleans.

No initial-page refusal, bootstrap/blank/error page, missing browser, stub PNG, raw launch, different profile, ignored TLS, standalone transport instead of production review, or unrelated background latch satisfies R12. R11 positive rendering must be separately clean on the identical implementation/profile. Main binds both after pairs to actual candidate SHA plus dirty-input identity, contract revision/digest, commands/exits/interpreter/Chrome/kernel/ABI/manifest/FD/capability/observer facts. No invented digest or passing verdict in this proposal.

## 10. Finding-by-finding dispositions (proposed remedies, NOT closure)

All original reports remain unchanged: `.swarm/results/Tutmu-sec-net-recheck.a2.md`, `Tutmu-planning-review.r1.a1.md`, `Tutmu-planning-quality.r1.a1.md`. Their full findings, scope distinctions and evidence limits were read. The following are concrete replacement obligations; independent reviewers decide whether they resolve the exact revised design.

| Finding IDs | Proposed remedy / remaining acceptance |
|---|---|
| Gate21 F1 (security) | §§4–7 synchronous scalar precommit AND kernel pre-return durable hook ledger; ID_VALID-independent received latch, actual object/attachment/RCU/writer barriers; R09/R10 deterministic withdrawal/death/owner loss. Exact revised design remains subject to independent acceptance. |
| Gate21 F2 (security) | §7.2 direct navigate terminal-only registered owned receipt/root drain; immutable cached follow-up with no live browser; R08 direct subset rejects late/queued/foreign/failed-close and stale cache. |
| Gate21 B1 (plan) | §§2/7.1 creator/bind/current/finish root APIs and explicit SafeFetch/factory/scope propagation from BEFORE submission through queue/preview/browser/decode, cancel wakeups and fixed cleanup; R07. |
| Gate21 B2 (plan) | §§2–3 typed DecodeBudget/DecodedResponse/decode_response, complete encoded-vs-sample/HEAD/204/304 and aggregate scratch/base64/deadline authorization; R05/R11-ENCODING. |
| Gate21 B3 (plan) | §8 requires native path/provides artifact and from/to/via/pattern key-link objects; P46PlansResume owns every plan correction, not arbitrary prose arrays. |
| Gate21 W1/W2 (plan) | §8 explicit D-05/D-07 parent-only override of tracer/TDD commands/commits; §9 fresh keyless HOME/XDG_DATA_HOME under approved scratch for Main only. |
| SECNET-A10-IPC-01 | §5 restores private filesystem/abstract IPC, exact socket matrix, closed bootstrap transfer, no imports, owned PID lifetime. R10 re-proves changed profile; prior design acceptance does not transfer automatically. |
| SECNET-A10-LATCH-02 | §§5.2a/b/6–7 shared kernel sequence BEFORE resume/denial/reply, loss-aware received latch and exact socket/task/writer retirement. R07/R09/R10 prove it; post-death empty notifications never evidence. |
| SECNET-A10-TARGET-03 | §6 recursive attach-before-resume and direct Fetch without Playwright auto-continue/preflight synthesis; R08/R11 prove each supported target. |
| SECNET-A10-API-04; REV-P46R1-02; QF-P46R1-01 | §§2/4 give complete typed ownership; §6 native paused headers replaces impossible required ExtraInfo and incorrect property claim. Main's new raw-CDP receipt establishes limited cookie/negative-preflight feasibility; complete cookie/CORS/redirect/worker matrix remains required. |
| SECNET-A10-REDIRECT-05 | §3/6 fresh native hops for 301/302/303/307/308; R06/R11-REDIRECT retain no-follow fetch and method/credential rules. |
| SECNET-A10-BEFORE-06; REV-P46-01 | §9 preserves separate original before anchors and required candidate-bound pairs; no replay or new provenance invention. |
| SECNET-A10-SANDBOX-07; REV-P46R1-01; QF-P46R1-03 | Native namespace/Seccomp/TSYNC + scalar/import guard + TCP/other connect/UDP send/IP packet enforcement retained. Uniform inert create/bind/UDP association and broker-only native DNS correct incompatible choices, not old-denial reset/exemption. All payload/FD/retirement and same-profile real clean browser gates remain; no waiver/innerERRNO speculation. |
| SECNET-A10-BOUNDS-08; REV-P46R1-03; QF-P46R1-02 | §§2–7 specify pre-allocation caps, aggregate cgroup/tmpfs/queue limits, resolver subprocess, nonblocking abortable IO, whole exchange/lifecycle/drain deadlines. R07/R11 hostile-size/time/slot-release cases required. |
| SECNET-A10-ENV-09; REV-P46R1-04; QF-P46R1-04 | §5 exact env at every exec; R10 descendant key-set/canary proof extends privacy to environment, not mounts only. |
| SECNET-A10-MANIFEST-10; REV-P46R1-05; QF-P46R1-10 | §5 per-file sealed copies, recursive inode/symlink/writability/TOCTOU checks, private proc/dev/tmp; R10 socket/FIFO/device planting retained. |
| SECNET-A10-LAUNCH-11; REV-P46R1-05; QF-P46R1-10 | §5 exact fixed argv/env/manifest/native verification and BEFORE-first-child kernel controls/AF_INET inventory; R09/R10 preserve background outcomes. Necessary connect/send denial demands profile correction/re-gate, never benign reclassification or fake clean startup. |
| SECNET-A10-LIFELINE-12; REV-P46R1-05; QF-P46R1-10 | §5 watchdog/lifeline plus actual bwrap parent-death/PID1/cgroup ownership; R10 kills owner and observes teardown. A dead parent's finally is not the mechanism. |
| SECNET-A10-WIRE-13; REV-P46R1-05; QF-P46R1-07 | §3 exact request-target validation, legacy preview header identity, ordered framing and all missing HTTP cases; R05/R06/R11 measure them. |
| QF-P46-01; QF-P46R1-05; QF-SNR1-01 | §9 exact initial→meta refusal attribution/order, consumer-visible failed results and 1:1 receipt/drain fields. Reviewer must reassess, not retain the earlier overbroad adequacy grade. |
| QF-P46-02 | All R11 subcases plus independent R09/R10 and bounds remain required; measured primitive receipt is not full functional closure. |
| REV-P46R1-06 | §8 includes direct launch, platform wrapper, test_web/test_platform and registration-only growth/providers callers plus retained packaging/discovery. No “only mcp/webpack” claim. |
| REV-P46R1-07 | §4 sole factory constructor/registry, one private test launcher seam and explicit host config input; foreign sessions cannot substitute. |
| QF-P46R1-06 | R08 redirect/resource/meta each cover host-policy/nonpublic-answer/actual-peer failures with zero forbidden requests. |
| QF-P46R1-08 | §9 pins each R11/R12 subcase to one author/file; composed R12-CHROMIUM belongs to BrowserSafety after composition. |
| QF-P46R1-09 | §9 deterministic barriers, ≥20 repeats, bounded oracles and no quarantine-as-pass. |
| QF-P46R1-11 | Every §9 row maps F/B to the exact AC/check; LAND-02 retained independently. |
| REV-A10RC-R1-01/02; QF-SNR1-02 | Next assessor must correct its own QA count/citations, distinguish unspecified preemption from absence of a textual cancel instruction, and use exact receipt anchors. Historical reports not rewritten. These are report-precision notes, not product waivers. |

## 11. Source audit, gates and genuinely open prerequisites

| Source | Item | Coverage |
|---|---|---|
| GOAL / ROADMAP Phase46 | Land hardening verified without replay | 46-02/03 implement current gaps; 46-04 composition + Main union; 46-05 receipts/docs. Historical 46-01 stays complete. |
| REQ | LAND-01 | R01–R12 plus independent security and Main gates; not source-only closure. |
| REQ | LAND-02 | Preserve roster/policy/template, empty/order/adjacency/concurrency edges; 46-04 runs existing composition suites via Main, 46-05 documents invariants. |
| RESEARCH | No phase RESEARCH.md exists in discovered phase directory | Installed API/source evidence and supplied Main prerequisites in §1 replace speculation; 46-PATTERNS is an analog, not authority for a boundary. |
| CONTEXT | D-01/D-04 | All transport/browser, mandatory confinement, native semantics and no-waiver tasks in 46-02/03/04. |
| CONTEXT | D-02 | 46-04 verification preserves Phase48 real 3.12/3.13/3.14 and matching-head CI gate; no declarations/simulation substitutes. |
| CONTEXT | D-03 | Every plan is gap_closure; no historical landing/Phase52 rewrites. |
| CONTEXT | D-05/D-07 | Parent-only checks/Git/gates, native independent review; no signed ledger edits or fabricated signatures. |
| CONTEXT | D-06 | Preserve verified prior-branch publication BEFORE Omega rename. Subsequent exact changed-head real final matrix/hosted nine jobs+docs/independent review precede audit/archive/gated main merge; Railway connect/prepare only, no live deploy. |

Independent security AND plan reviewers must accept exact corrected SEC-NET2.2.0 digest BEFORE product dispatch. Partial writing/primitive passed=true never approval. Selected256/nativeDNS/owned metadata/uniform UDP association now has observed native diagnostic compatibility and selected real payload denials; earlier65/74/1/2 denials and ptrace ESRCH remain failed history. OPEN: full sealed manifest/env/FD/native sandbox + outer scalar ptrace/listener + delegated guard/lifetime/format220/174-byte committer under exact production profile; verifier/ACK/overflow/concurrency/fault/queued-object/GSO/splice/TFO/retirement/death/drain proofs; real mediated allowed HTTP+verifiedHTTPS/cookies/CORS/worker/redirect/body/bounds and exact production R12 pairs. Readonly-from-construction/classic persistence/FEXIT owner-close resolve unsupported freeze/tracing-detach, not full-protocol acceptance. Main later runs real3.12/3.13/3.14 and exact-head hosted nine jobs+docs/review; ordering unchanged. Negative results require correction/re-review, no exemptions/reset/raw launch/TLS ignore/manual cookie/nonfunctional approval.

Scope remains these web/browser consumers, not whole-seat sandboxing. Host kernel/routing/trust roots and trusted configuration/DI are trust boundaries; admitted public services' downstream behavior is not proven. Documentation follows implementation plus observed receipts; no plan, primitive capability, source-only report or document closes security, matrix, release or archive gates.
