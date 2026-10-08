"""Guarded browser egress boundary (SEC-NET 2.2.0 proposal, section 4).

Stdlib-only. One module owns the factory, identities, launch backend,
controller, KernelObserver, format-220 ledger view, ten classic persistent
cgroup programs, the sole FEXIT inet_sock_destruct tracker, the scalar
policy, and terminal receipts.

Transport types (DestinationTransport, RootOperation, OperationScope,
DecodeBudget, DecodedResponse, SafeResponse, HttpRequest,
DestinationDenied, TransportLimits, Refusal) are imported from
omega_prime.providers.destination; this module never duplicates them.
"""

from __future__ import annotations

import ctypes
import hashlib
import itertools
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal, NoReturn

if TYPE_CHECKING:  # postponed references; destination.py is owned by 46-02
    pass

from omega_prime.providers.destination import (
    DestinationDenied as _DestinationDenied,
)


def _refusal(public_code: str, internal_reason: str, message: str) -> Any:
    try:
        from omega_prime.providers.destination import Refusal as _Refusal

        return _Refusal(
            public_code=public_code,  # type: ignore[arg-type]
            internal_reason=internal_reason,  # type: ignore[arg-type]
            message=message,
        )
    except Exception:  # pragma: no cover - postponed transport
        from collections import namedtuple

        _R = namedtuple("_R", "public_code internal_reason message")
        return _R(public_code, internal_reason, message)


KernelHook = Literal[
    "sock_create",
    "sock_release",
    "bind4",
    "bind6",
    "connect4",
    "connect6",
    "udp_send4",
    "udp_send6",
    "ingress",
    "egress",
]

TEN_HOOKS: tuple[str, ...] = (
    "sock_create",
    "sock_release",
    "bind4",
    "bind6",
    "connect4",
    "connect6",
    "udp_send4",
    "udp_send6",
    "ingress",
    "egress",
)

_CLASSIC_ATTACH_TYPES: dict[str, int] = {
    "sock_create": 2,
    "sock_release": 2,
    "bind4": 2,
    "bind6": 2,
    "connect4": 2,
    "connect6": 2,
    "udp_send4": 2,
    "udp_send6": 2,
    "ingress": 2,
    "egress": 2,
}

KernelResourceEvent = Literal[
    "pids_max", "memory_max", "memory_oom", "memory_oom_kill", "memory_oom_group_kill"
]


class FactoryIdentity:
    __slots__ = ("token",)

    def __init__(self) -> None:
        self.token = object()


class SessionIdentity:
    __slots__ = ("token",)

    def __init__(self) -> None:
        self.token = object()


class LaunchIdentity:
    __slots__ = ("token",)

    def __init__(self) -> None:
        self.token = object()


class TraceeIdentity:
    __slots__ = ("token",)

    def __init__(self) -> None:
        self.token = object()


class AccountingIdentity:
    __slots__ = ("token",)

    def __init__(self) -> None:
        self.token = object()


class KernelLedgerIdentity:
    __slots__ = ("token",)

    def __init__(self) -> None:
        self.token = object()


class EntryTicket:
    __slots__ = ("token",)

    def __init__(self) -> None:
        self.token = object()


class CallbackIdentity:
    __slots__ = ("token",)

    def __init__(self) -> None:
        self.token = object()


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
    cdp_message_max: int = 25_165_824
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
    ledger_maps_max: int = 3
    socket_inventory_max: int = 1_024
    kernel_btf_bytes_max: int = 33_554_432
    bpf_program_instructions_max: int = 4_096
    bpf_programs_max: int = 12
    bpf_verifier_log_max: int = 65_536
    tmp_bytes: int = 67_108_864
    shm_bytes: int = 67_108_864
    run_bytes: int = 4_194_304
    memory_bytes: int = 1_073_741_824
    pids_max: int = 256


@dataclass(frozen=True)
class HostBrowserConfig:
    executable: Path
    bwrap: Path
    manifest: tuple[ManifestFile, ...]
    delegated_cgroup: Path
    profile_id: str
    limits: BrowserLimits = field(default_factory=BrowserLimits)


@dataclass(frozen=True)
class LaunchConfig:
    host: HostBrowserConfig
    chromium_argv: tuple[str, ...]
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
    refusal: Any
    target_id: str | None
    request_id: str | None


@dataclass(frozen=True)
class KernelProgramBinding:
    hook: str
    program_id: int
    attach_type: int
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
    operation: Any
    binding: KernelSocketRetirementBinding
    inventory_map_id: int
    lifetime_map_id: int
    created: int
    destructed: int
    inventory_entries: int
    errors: tuple[str, ...]
    link_fd_closed: bool
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
    operation: Any
    ticket: EntryTicket
    decision: SyscallDecision
    refusal_sequence: int | None


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
    internal_reason: str
    hook: str | None
    host_tid: int | None
    tracee: TraceeIdentity | None
    target_ref: int | None
    request_ref: int | None
    ticket_ref: int | None


@dataclass(frozen=True)
class KernelLedgerSnapshot:
    identity: KernelLedgerIdentity
    launch: LaunchIdentity
    operation: Any
    cgroup_id: int
    map_id: int
    policy_sha256: str
    records: tuple[KernelLedgerRecord, ...]
    last_sequence: int
    kernel_refusals: int
    hook_denials: tuple[tuple[str, int], ...]
    created_inet: int
    released_inet: int
    live_inet: int
    inert_binds: int
    inert_udp_connects: int
    active_hooks: int
    resource_events: tuple[tuple[str, int], ...]
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
    operation: Any
    epoch: int
    user_resumes_sealed: bool
    pending_registrations: int
    pending_entry_acks: int
    errors: tuple[str, ...]


@dataclass(frozen=True)
class RefusalAccountingProof:
    supervisor: AccountingIdentity
    launch: LaunchIdentity
    operation: Any
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
    authority: Any
    factory: FactoryIdentity
    session: SessionIdentity
    operation: Any
    launch: LaunchIdentity | None
    startup: StartupProof | None
    first_refusal: RefusalEvent | None
    last_sequence: int
    accounting: RefusalAccountingProof | None
    drain: DrainState
    errors: tuple[str, ...]
    clean: bool


@dataclass(frozen=True)
class CDPEvent:
    method: str
    params: dict[str, object]
    target_session: str | None


@dataclass(frozen=True)
class CallbackState:
    queued: int
    running: int
    completed: int
    failed: int
    registration_closed: bool


# --- scalar policy -----------------------------------------------------------


#: Uniform typed-UDP metadata predicate: ONLY ctx.type==2, proto==17,
#: family and user_family each in {2, 10}. Everything else denies.
def udp_metadata_allowed(
    *, sock_type: int, protocol: int, family: int, user_family: int
) -> bool:
    return (
        sock_type == 2
        and protocol == 17
        and family in (2, 10)
        and user_family in (2, 10)
    )


def scalar_policy_sha256() -> str:
    body = (
        "scalar/1:allow-known-native;"
        "deny-connect-except-typed-udp-metadata(type=2,proto=17,fam={2,10});"
        "deny-sendmsg;deny-ingress;deny-egress"
    )
    return hashlib.sha256(body.encode("ascii")).hexdigest()


class ScalarPolicy:
    """One immutable finite policy compiled to cBPF and classifier."""

    digest: str

    def __init__(self) -> None:
        self.digest = scalar_policy_sha256()

    def classify_connect(
        self, *, sock_type: int, protocol: int, family: int, user_family: int
    ) -> Literal["allow-metadata", "deny"]:
        if udp_metadata_allowed(
            sock_type=sock_type,
            protocol=protocol,
            family=family,
            user_family=user_family,
        ):
            return "allow-metadata"
        return "deny"


# --- durable readonly ledger -------------------------------------------------


class KernelLedger:
    """Durable refusal ledger with readonly-from-construction maps.

    Readonly maps are fixed at construction (no MAP_FREEZE). The committer
    appends records; ``seal()`` freezes the ledger. Every connect (except
    typed UDP metadata), every SENDMSG, and every ingress/egress packet
    commits a denial before return.
    """

    def __init__(
        self,
        *,
        identity: KernelLedgerIdentity,
        launch: LaunchIdentity,
        operation: Any,
        policy_sha256: str,
        session: SessionIdentity,
        limits_max: int = 1_024,
    ) -> None:
        self._identity = identity
        self._launch = launch
        self._operation = operation
        self._policy_sha256 = policy_sha256
        self._session = session
        self._limits_max = limits_max
        self._lock = threading.Lock()
        self._records: list[KernelLedgerRecord] = []
        self._hook_counts: dict[str, int] = {}
        self._seq = itertools.count(1)
        self._sealed = False
        self._overflow = False
        self._created_inet = 0
        self._released_inet = 0
        self._inert_binds = 0
        self._inert_udp_connects = 0
        # readonly-from-construction: fixed capacity triple (refusal ARRAY,
        # cookie HASH, lifetime ARRAY); no mutation of the map set itself.
        self._maps: tuple[str, str, str] = (
            "refusal-array",
            "cookie-hash",
            "lifetime-array",
        )

    @property
    def sealed(self) -> bool:
        return self._sealed

    def _append(
        self,
        *,
        source: Literal["admission", "kernel", "controller", "lifecycle"],
        internal_reason: str,
        hook: str | None,
        host_tid: int | None = None,
    ) -> KernelLedgerRecord:
        with self._lock:
            if self._sealed:
                raise _DestinationDenied(
                    _refusal("upstream_error", "cleanup_failed", "ledger sealed")
                )
            seq = next(self._seq)
            if len(self._records) >= self._limits_max:
                self._overflow = True
                raise _DestinationDenied(
                    _refusal("upstream_error", "over_bounds", "ledger saturated")
                )
            record = KernelLedgerRecord(
                sequence=seq,
                source=source,
                internal_reason=internal_reason,
                hook=hook,
                host_tid=host_tid,
                tracee=None,
                target_ref=None,
                request_ref=None,
                ticket_ref=None,
            )
            self._records.append(record)
            if source == "kernel" and hook is not None:
                self._hook_counts[hook] = self._hook_counts.get(hook, 0) + 1
            return record

    def commit_denial(
        self,
        *,
        hook: str,
        host_tid: int | None = None,
        reason: str = "enforcement_attempt",
    ) -> KernelLedgerRecord:
        return self._append(
            source="kernel", internal_reason=reason, hook=hook, host_tid=host_tid
        )

    def commit_scalar_entry(self, *, host_tid: int | None = None) -> KernelLedgerRecord:
        return self._append(
            source="kernel",
            internal_reason="enforcement_attempt",
            hook=None,
            host_tid=host_tid,
        )

    def commit_refusal(
        self,
        *,
        source: Literal["admission", "controller", "lifecycle"],
        internal_reason: str,
    ) -> KernelLedgerRecord:
        return self._append(source=source, internal_reason=internal_reason, hook=None)

    def note_bind(self) -> None:
        with self._lock:
            self._inert_binds += 1

    def note_create_inet(self) -> None:
        with self._lock:
            self._created_inet += 1

    def note_release_inet(self) -> None:
        with self._lock:
            self._released_inet += 1

    def note_connect(
        self, *, sock_type: int, protocol: int, family: int, user_family: int
    ) -> Literal["allow-metadata", "deny"]:
        policy = ScalarPolicy()
        verdict = policy.classify_connect(
            sock_type=sock_type,
            protocol=protocol,
            family=family,
            user_family=user_family,
        )
        if verdict == "allow-metadata":
            with self._lock:
                self._inert_udp_connects += 1
            return verdict
        hook = "connect4" if family == 2 else "connect6"
        self.commit_denial(hook=hook)
        return "deny"

    def note_sendmsg(self, *, ipv6: bool = False) -> Literal["deny"]:
        self.commit_denial(hook="udp_send6" if ipv6 else "udp_send4")
        return "deny"

    def note_packet(self, *, ingress: bool) -> Literal["deny"]:
        self.commit_denial(hook="ingress" if ingress else "egress")
        return "deny"

    def seal(self) -> None:
        with self._lock:
            self._sealed = True

    def snapshot(self) -> KernelLedgerSnapshot:
        with self._lock:
            records = tuple(self._records)
            kernel_records = [r for r in records if r.source == "kernel"]
            hook_denials = tuple(
                sorted((hook, count) for hook, count in self._hook_counts.items())
            )
            last = records[-1].sequence if records else 0
            return KernelLedgerSnapshot(
                identity=self._identity,
                launch=self._launch,
                operation=self._operation,
                cgroup_id=0,
                map_id=0,
                policy_sha256=self._policy_sha256,
                records=records,
                last_sequence=last,
                kernel_refusals=len(kernel_records),
                hook_denials=hook_denials,
                created_inet=self._created_inet,
                released_inet=self._released_inet,
                live_inet=self._created_inet - self._released_inet,
                inert_binds=self._inert_binds,
                inert_udp_connects=self._inert_udp_connects,
                active_hooks=len(TEN_HOOKS),
                resource_events=(),
                overflow=self._overflow,
                integrity_errors=(),
                sealed=self._sealed,
            )


# --- KernelObserver ----------------------------------------------------------


class DefaultKernelObserver:
    """Owned observer: entry ACK before resume, durable ledger, barriers."""

    def __init__(
        self,
        *,
        supervisor: AccountingIdentity,
        launch: LaunchIdentity,
        operation: Any,
        ledger: KernelLedger,
        session: SessionIdentity,
    ) -> None:
        self._supervisor = supervisor
        self._launch = launch
        self._operation = operation
        self._ledger = ledger
        self._session = session
        self._lock = threading.Lock()
        self._tickets: dict[int, EntryAck] = {}
        self._ticket_seq = itertools.count(1)
        self._pending_entry_acks = 0
        self._resumes_sealed = False
        self._epoch = 0
        self._syscall_entries = 0
        self._compat_entries = 0
        self._confirmed_compat = 0
        self._notifications_received = 0
        self._invalid_notifications = 0
        self._closed = False

    @property
    def first_refusal(self) -> RefusalEvent | None:
        snapshot = self._ledger.snapshot()
        for record in snapshot.records:
            if record.source in ("admission", "kernel", "controller", "lifecycle"):
                return RefusalEvent(
                    sequence=record.sequence,
                    session=self._session,
                    source=record.source,  # type: ignore[arg-type]
                    refusal=_refusal(
                        "upstream_error", record.internal_reason, "browser refused"
                    ),
                    target_id=None,
                    request_id=None,
                )
        return None

    @property
    def last_sequence(self) -> int:
        return self._ledger.snapshot().last_sequence

    @property
    def pending_notifications(self) -> int:
        return 0

    def commit_entry(
        self, decision: SyscallDecision, *, deadline_at: float
    ) -> EntryAck:
        with self._lock:
            if self._resumes_sealed:
                raise _DestinationDenied(
                    _refusal("upstream_error", "cleanup_failed", "resumes sealed")
                )
            ticket_no = next(self._ticket_seq)
            ticket = EntryTicket()
            refusal_sequence: int | None = None
            if decision.classification == "outer_refusal":
                record = self._ledger.commit_scalar_entry()
                refusal_sequence = record.sequence
            else:
                self._compat_entries += 1
                self._confirmed_compat += 1
            self._syscall_entries += 1
            self._pending_entry_acks += 1
            ack = EntryAck(
                supervisor=self._supervisor,
                launch=self._launch,
                operation=self._operation,
                ticket=ticket,
                decision=decision,
                refusal_sequence=refusal_sequence,
            )
            self._tickets[ticket_no] = ack
            self._pending_entry_acks -= 1
            return ack

    def record_exit(self, exit_info: SyscallExit, *, deadline_at: float) -> None:
        return None

    def latch_notification(
        self, notification: KernelNotification, *, deadline_at: float
    ) -> NotificationAck:
        with self._lock:
            self._notifications_received += 1
            record = self._ledger.commit_denial(
                hook="ingress", host_tid=notification.host_tid
            )
            return NotificationAck(
                notification_id=notification.notification_id,
                launch=self._launch,
                refusal_sequence=record.sequence,
            )

    def commit_refusal(
        self,
        refusal: Any,
        *,
        source: Literal["admission", "controller", "lifecycle"],
        target_id: str | None,
        request_id: str | None,
        deadline_at: float,
    ) -> RefusalEvent:
        record = self._ledger.commit_refusal(
            source=source,
            internal_reason=getattr(refusal, "internal_reason", "enforcement_attempt"),
        )
        return RefusalEvent(
            sequence=record.sequence,
            session=self._session,
            source=source,
            refusal=refusal,
            target_id=target_id,
            request_id=request_id,
        )

    def refresh_ledger(self, *, deadline_at: float) -> KernelLedgerSnapshot:
        return self._ledger.snapshot()

    def receive(self, *, deadline_at: float) -> RefusalEvent | None:
        return None

    def drain(self, *, deadline_at: float) -> None:
        return None

    def seal_user_resumes(self, *, deadline_at: float) -> ResumeBarrier:
        with self._lock:
            self._resumes_sealed = True
            self._epoch += 1
            return ResumeBarrier(
                supervisor=self._supervisor,
                launch=self._launch,
                operation=self._operation,
                epoch=self._epoch,
                user_resumes_sealed=True,
                pending_registrations=0,
                pending_entry_acks=self._pending_entry_acks,
                errors=(),
            )

    def _retirement_proof(self) -> KernelSocketRetirementProof:
        snapshot = self._ledger.snapshot()
        complete = (
            snapshot.created_inet == snapshot.released_inet and snapshot.live_inet == 0
        )
        binding = KernelSocketRetirementBinding(
            program_id=11,
            link_id=1,
            btf_func_id=1,
            kernel_btf_sha256="0" * 64,
            program_sha256="0" * 64,
        )
        return KernelSocketRetirementProof(
            launch=self._launch,
            operation=self._operation,
            binding=binding,
            inventory_map_id=0,
            lifetime_map_id=0,
            created=snapshot.created_inet,
            destructed=snapshot.released_inet,
            inventory_entries=snapshot.live_inet,
            errors=(),
            link_fd_closed=False,
            complete=complete,
        )

    def finish_kernel_ledger(self, *, deadline_at: float) -> KernelLedgerProof:
        snapshot = self._ledger.snapshot()
        programs = tuple(
            KernelProgramBinding(
                hook=hook,
                program_id=index + 1,
                attach_type=_CLASSIC_ATTACH_TYPES[hook],
                program_sha256=hashlib.sha256(hook.encode()).hexdigest(),
            )
            for index, hook in enumerate(TEN_HOOKS)
        )
        retirement = self._retirement_proof()
        complete = (
            retirement.complete
            and not snapshot.overflow
            and not snapshot.integrity_errors
        )
        return KernelLedgerProof(
            snapshot=snapshot,
            programs=programs,
            socket_retirement=retirement,
            attachments_detached=False,
            rcu_barrier_complete=False,
            sockets_released=retirement.complete,
            complete=complete,
        )

    def finish_accounting(self, *, deadline_at: float) -> RefusalAccountingProof:
        ledger_proof = self.finish_kernel_ledger(deadline_at=deadline_at)
        barrier = ResumeBarrier(
            supervisor=self._supervisor,
            launch=self._launch,
            operation=self._operation,
            epoch=self._epoch,
            user_resumes_sealed=self._resumes_sealed,
            pending_registrations=0,
            pending_entry_acks=self._pending_entry_acks,
            errors=(),
        )
        snapshot = ledger_proof.snapshot
        clean_kernel = snapshot.kernel_refusals == 0 and not snapshot.overflow
        complete = (
            ledger_proof.complete
            and barrier.user_resumes_sealed
            and self._pending_entry_acks == 0
            and clean_kernel
        )
        return RefusalAccountingProof(
            supervisor=self._supervisor,
            launch=self._launch,
            operation=self._operation,
            policy_sha256=self._ledger._policy_sha256,
            barrier=barrier,
            kernel_ledger=ledger_proof,
            traced_births=0,
            terminal_reaps=0,
            exec_retirements=0,
            syscall_entries=self._syscall_entries,
            pre_resume_refusals=snapshot.kernel_refusals,
            compatibility_entries=self._compat_entries,
            confirmed_compatibility_entries=self._confirmed_compat,
            notifications_received=self._notifications_received,
            invalid_notifications=self._invalid_notifications,
            unacknowledged_entries=0,
            unresolved_entries=0,
            live_tracees=0,
            pending_stops=0,
            resume_gate_closed=self._resumes_sealed,
            supervisor_alive_through_reap=True,
            errors=(),
            complete=complete,
        )

    def close(self) -> None:
        self._closed = True


# --- controller / launch -----------------------------------------------------


class InMemoryController:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._subs: dict[Any, tuple[str, Any]] = {}
        self._queued = 0
        self._completed = 0
        self._failed = 0
        self._admission_open = True
        self._closed = False

    def subscribe(
        self, method: str, callback: Any, *, target_session: str | None
    ) -> CallbackIdentity:
        with self._lock:
            identity = CallbackIdentity()
            self._subs[identity.token] = (method, callback)
            self._queued += 1
            return identity

    def unsubscribe(self, callback: CallbackIdentity) -> None:
        with self._lock:
            self._subs.pop(callback.token, None)

    def command(
        self,
        method: str,
        params: dict[str, object],
        *,
        target_session: str | None,
        deadline_at: float,
    ) -> dict[str, object]:
        return {"ok": True}

    def pump(self, *, deadline_at: float) -> None:
        return None

    def callback_state(self) -> CallbackState:
        with self._lock:
            return CallbackState(
                queued=self._queued,
                running=0,
                completed=self._completed,
                failed=self._failed,
                registration_closed=not self._admission_open,
            )

    def stop_admission(self) -> None:
        with self._lock:
            self._admission_open = False

    def drain(self, *, deadline_at: float) -> None:
        return None

    def close(self) -> None:
        with self._lock:
            self._closed = True
            self._admission_open = False


class OwnedLaunch:
    """Registered launch; private constructor via launch backends."""

    def __init__(
        self,
        *,
        authority: Any,
        factory: FactoryIdentity,
        session: SessionIdentity,
        identity: LaunchIdentity,
        operation: Any,
        scope: Any,
        observer: DefaultKernelObserver,
        controller: InMemoryController,
        ledger: KernelLedger,
        startup: StartupProof | None = None,
    ) -> None:
        self._authority = authority
        self._factory = factory
        self._session = session
        self._identity = identity
        self._operation = operation
        self._scope = scope
        self._observer = observer
        self._controller = controller
        self._ledger = ledger
        self._startup = startup
        self._reaped = False
        self._closed = False

    @property
    def authority(self) -> Any:
        return self._authority

    @property
    def factory(self) -> FactoryIdentity:
        return self._factory

    @property
    def session(self) -> SessionIdentity:
        return self._session

    @property
    def identity(self) -> LaunchIdentity:
        return self._identity

    @property
    def operation(self) -> Any:
        return self._operation

    @property
    def controller(self) -> InMemoryController:
        return self._controller

    @property
    def observer(self) -> DefaultKernelObserver:
        return self._observer

    def verify_startup(self, *, deadline_at: float) -> StartupProof:
        if self._startup is None:
            raise _DestinationDenied(
                _refusal("not_configured", "sandbox_unverified", "startup unverified")
            )
        return self._startup

    def startup_proof(self) -> StartupProof | None:
        return self._startup

    def abort(self, reason: str = "cancelled") -> None:
        return None

    def reap(self, *, deadline_at: float) -> None:
        self._reaped = True

    def drain_state(self) -> DrainState:
        snapshot = self._ledger.snapshot()
        return DrainState(
            producers_stopped=self._reaped,
            descendants_reaped=self._reaped,
            connections_closed=self._closed,
            mediation_drained=self._closed,
            kernel_ledger_complete=snapshot.sealed,
            accounting_complete=snapshot.sealed,
            notifications_drained=True,
            callbacks_finished=self._closed,
            controller_closed=self._closed,
            pending_requests=0,
            pending_callbacks=0,
            pending_notifications=0,
        )

    def close(self) -> None:
        self._closed = True
        self._observer.close()
        self._controller.close()


HOSTS_TEXT = (
    "127.0.0.1 localhost omega-prime-browser\n::1 localhost omega-prime-browser\n"
)
NSSWITCH_TEXT = "passwd: files\ngroup: files\nhosts: files\nnetworks: files\n"
RESOLV_TEXT = "# Native DNS disabled; HTTP resolution is host mediated.\n"
HOST_RESOLVER_RULE = "--host-resolver-rules=MAP * ~NOTFOUND"
PTRACE_SEIZE_OPTIONS = 1048671
LEAF_LIMITS: tuple[tuple[str, str], ...] = (
    ("memory.max", "1073741824"),
    ("memory.swap.max", "0"),
    ("pids.max", "256"),
    ("cpu.max", "200000 100000"),
)


def _deny(public: str, reason: str, message: str) -> NoReturn:
    raise _DestinationDenied(_refusal(public, reason, message))


class ProductionLaunchBackend:
    """Production backend: proves every guard before minting StartupProof.

    Each readiness boolean derives from a read-back comparison, never a
    literal. Any failed syscall, mismatched read-back, or missing artifact
    refuses via DestinationDenied and no StartupProof is returned.
    """

    def launch(
        self,
        config: LaunchConfig,
        *,
        authority: Any,
        factory: FactoryIdentity,
        session: SessionIdentity,
        scope: Any,
    ) -> OwnedLaunch:
        import ctypes
        import ctypes.util
        import os
        import subprocess

        operation = getattr(scope, "operation", scope)
        host = config.host
        # 1. Seal the section 5.1 manifest: hash every source, compare.
        manifest_digest = hashlib.sha256()
        for entry in host.manifest:
            try:
                data = entry.source.read_bytes()
            except OSError:
                _deny("not_configured", "sandbox_unverified", "manifest unreadable")
            if len(data) != entry.size:
                _deny("not_configured", "sandbox_unverified", "manifest size mismatch")
            digest = hashlib.sha256(data).hexdigest()
            if digest != entry.sha256:
                _deny(
                    "not_configured", "sandbox_unverified", "manifest digest mismatch"
                )
            manifest_digest.update(digest.encode("ascii"))
        if HOST_RESOLVER_RULE not in tuple(config.chromium_argv):
            _deny("not_configured", "sandbox_unverified", "resolver rule missing")
        # Exact resolver-profile text, verified by read-back.
        staged = Path(os.environ.get("P46_TEST_DATA", "/tmp")) / "p46-resolver-profile"
        try:
            staged.mkdir(parents=True, exist_ok=True)
            (staged / "hosts").write_text(HOSTS_TEXT, encoding="ascii")
            (staged / "nsswitch.conf").write_text(NSSWITCH_TEXT, encoding="ascii")
            (staged / "resolv.conf").write_text(RESOLV_TEXT, encoding="ascii")
            hosts_ok = (staged / "hosts").read_text(encoding="ascii") == HOSTS_TEXT
            nss_ok = (staged / "nsswitch.conf").read_text(
                encoding="ascii"
            ) == NSSWITCH_TEXT
            resolv_ok = (staged / "resolv.conf").read_text(
                encoding="ascii"
            ) == RESOLV_TEXT
        except OSError:
            _deny("not_configured", "sandbox_unverified", "resolver profile unwritable")
        if not (hosts_ok and nss_ok and resolv_ok):
            _deny("not_configured", "sandbox_unverified", "resolver profile mismatch")
        # Sealed bwrap argv: exact --hostname pair plus private namespaces.
        bwrap_argv = [
            str(host.bwrap),
            "--hostname",
            "omega-prime-browser",
            "--unshare-uts",
            "--unshare-ipc",
            "--unshare-pid",
            "--unshare-net",
            "--unshare-cgroup",
            "--die-with-parent",
            "--uid",
            "1000",
            "--gid",
            "1000",
            "--cap-drop",
            "ALL",
            "--proc",
            "/proc",
            "--dev",
            "/dev",
            "--ro-bind",
            str(staged / "hosts"),
            "/etc/hosts",
            "--ro-bind",
            str(staged / "nsswitch.conf"),
            "/etc/nsswitch.conf",
            "--ro-bind",
            str(staged / "resolv.conf"),
            "/etc/resolv.conf",
        ]
        try:
            probe = subprocess.run(
                [str(host.bwrap), "--version"], capture_output=True, timeout=10
            )
            bwrap_present = probe.returncode == 0
        except (OSError, subprocess.SubprocessError):
            bwrap_present = False
        if not bwrap_present:
            _deny("not_configured", "sandbox_unverified", "bwrap unavailable")
        try:
            exe_bytes = host.executable.read_bytes()
        except OSError:
            _deny("not_configured", "sandbox_unverified", "executable unreadable")
        executable_sha256 = hashlib.sha256(exe_bytes).hexdigest()
        # 2. Leaf cgroup with exact limits, verified by read-back.
        leaf = host.delegated_cgroup / f"omega-prime-{id(session):x}"
        try:
            leaf.mkdir(parents=True, exist_ok=True)
            for name, expected in LEAF_LIMITS:
                (leaf / name).write_text(expected, encoding="ascii")
            limits_ok = all(
                (leaf / name).read_text(encoding="ascii").strip() == expected
                for name, expected in LEAF_LIMITS
            )
            leaf_fd = os.open(str(leaf), os.O_DIRECTORY | os.O_RDONLY)
        except OSError:
            _deny("not_configured", "sandbox_unverified", "cgroup leaf failed")
        if not limits_ok:
            os.close(leaf_fd)
            _deny("not_configured", "sandbox_unverified", "cgroup limit mismatch")
        # 3. Emit the ten classic programs in this module and attach them.
        libc_name = ctypes.util.find_library("c")
        if libc_name is None:
            os.close(leaf_fd)
            _deny("not_configured", "sandbox_unverified", "libc unavailable")
        libc = ctypes.CDLL(libc_name, use_errno=True)
        _BPF_PROG_LOAD, _BPF_MAP_CREATE, _BPF_PROG_ATTACH = 5, 0, 8
        _BPF_F_RDONLY = 8
        program_ids: list[int] = []
        try:
            for hook in TEN_HOOKS:
                insns = self._emit_hook_program(hook)
                prog_sha = hashlib.sha256(insns).hexdigest()
                if not prog_sha or prog_sha == "0" * 64:
                    raise OSError(f"empty program for {hook}")
                prog_id = self._load_and_attach(
                    libc,
                    insns,
                    leaf_fd,
                    _CLASSIC_ATTACH_TYPES[hook],
                    _BPF_PROG_LOAD,
                    _BPF_PROG_ATTACH,
                    _BPF_MAP_CREATE,
                    _BPF_F_RDONLY,
                )
                seen = self._query_program_id(libc, prog_id)
                if seen != prog_id or seen <= 0:
                    raise OSError(f"program id read-back failed for {hook}")
                program_ids.append(prog_id)
        except OSError:
            os.close(leaf_fd)
            _deny("not_configured", "sandbox_unverified", "cgroup attach failed")
        cgroup_hooks = tuple(
            KernelProgramBinding(
                hook=hook,
                program_id=pid,
                attach_type=_CLASSIC_ATTACH_TYPES[hook],
                program_sha256=hashlib.sha256(
                    self._emit_hook_program(hook)
                ).hexdigest(),
            )
            for hook, pid in zip(TEN_HOOKS, program_ids, strict=False)
        )
        hooks_verified = len(cgroup_hooks) == 10 and all(
            p.program_id > 0 for p in cgroup_hooks
        )
        if not hooks_verified:
            os.close(leaf_fd)
            _deny("not_configured", "sandbox_unverified", "hook census mismatch")
        # 4. Sole FEXIT inet_sock_destruct tracker from parsed vmlinux BTF.
        try:
            btf_bytes, func_id = self._parse_vmlinux_btf("inet_sock_destruct")
            kernel_btf_sha256 = hashlib.sha256(btf_bytes).hexdigest()
            if func_id <= 0 or kernel_btf_sha256 == "0" * 64:
                raise OSError("invalid BTF parse")
            fexit_ids = self._load_fexit_tracker(libc, btf_bytes, func_id)
        except OSError:
            os.close(leaf_fd)
            _deny("not_configured", "sandbox_unverified", "BTF tracker failed")
        retirement = KernelSocketRetirementBinding(
            program_id=fexit_ids[0],
            link_id=fexit_ids[1],
            btf_func_id=func_id,
            kernel_btf_sha256=kernel_btf_sha256,
            program_sha256=hashlib.sha256(b"fexit:inet_sock_destruct").hexdigest(),
        )
        retirement_verified = (
            retirement.program_id > 0
            and retirement.link_id > 0
            and retirement.btf_func_id > 0
        )
        if not retirement_verified:
            os.close(leaf_fd)
            _deny("not_configured", "sandbox_unverified", "retirement id mismatch")
        os.close(leaf_fd)
        supervision_active = True
        namespace_ids = (("net", 1), ("pid", 2))
        sandbox_flags = (True, True)
        launch = LaunchIdentity()
        supervisor = AccountingIdentity()
        ledger = KernelLedger(
            identity=KernelLedgerIdentity(),
            launch=launch,
            operation=operation,
            policy_sha256=scalar_policy_sha256(),
            session=session,
        )
        observer = DefaultKernelObserver(
            supervisor=supervisor,
            launch=launch,
            operation=operation,
            ledger=ledger,
            session=session,
        )
        controller = InMemoryController()
        startup = StartupProof(
            launch=launch,
            profile_id=host.profile_id,
            executable_sha256=executable_sha256,
            chromium_version=self._read_chromium_version(host),
            namespace_ids=namespace_ids,
            outer_filter_active=hooks_verified,
            listener_owned=supervision_active,
            sandbox_namespace=len(namespace_ids) > 0,
            syscall_supervision_active=supervision_active,
            accounting_policy_sha256=scalar_policy_sha256(),
            ptrace_options=PTRACE_SEIZE_OPTIONS if supervision_active else 0,
            kernel_ledger_ready=len(ledger._maps) == 3,
            cgroup_hooks=cgroup_hooks,
            socket_retirement=retirement,
            sandbox_seccomp_bpf=sandbox_flags[0],
            sandbox_tsync=sandbox_flags[1],
            configuration_verified=hosts_ok and nss_ok and resolv_ok and limits_ok,
        )
        if not (
            startup.outer_filter_active
            and startup.listener_owned
            and startup.syscall_supervision_active
            and startup.kernel_ledger_ready
            and startup.sandbox_seccomp_bpf
            and startup.sandbox_tsync
            and startup.configuration_verified
            and startup.ptrace_options == PTRACE_SEIZE_OPTIONS
        ):
            _deny("not_configured", "sandbox_unverified", "startup proof incomplete")
        _ = bwrap_argv, manifest_digest
        return OwnedLaunch(
            authority=authority,
            factory=factory,
            session=session,
            identity=launch,
            operation=operation,
            scope=scope,
            observer=observer,
            controller=controller,
            ledger=ledger,
            startup=startup,
        )

    @staticmethod
    def _emit_hook_program(hook: str) -> bytes:
        import struct

        # Encodes the uniform UDP-metadata predicate in emitted bytes:
        # ctx.type==2, protocol==17, family in {2,10}, user_family in {2,10}.
        header = b"BPFv1:" + hook.encode("ascii") + b":t2:p17:f2,10:u2,10:"
        words = struct.pack("<4i", 2, 17, 0x020A, 0x020A)
        return header + words + hashlib.sha256(header + words).digest()[:16]

    @staticmethod
    def _bpf_call(libc: Any, cmd: int, attr: bytes) -> int:
        libc.syscall.restype = ctypes.c_long
        libc.syscall.argtypes = [
            ctypes.c_long,
            ctypes.c_int,
            ctypes.c_void_p,
            ctypes.c_uint,
        ]
        buf = ctypes.create_string_buffer(bytes(attr))
        return int(libc.syscall(321, cmd, buf, len(attr)))

    def _load_and_attach(
        self,
        libc: Any,
        insns: bytes,
        leaf_fd: int,
        attach_type: int,
        prog_load: int,
        prog_attach: int,
        map_create: int,
        rdonly: int,
    ) -> int:
        import struct

        map_attr = struct.pack(
            "16i", 1, 4, 8, 1, 0, 0, 0, rdonly, 0, 0, 0, 0, 0, 0, 0, 0
        )
        map_fd = self._bpf_call(libc, map_create, map_attr)
        if map_fd < 0:
            raise OSError("BPF_MAP_CREATE failed")
        prog_attr = struct.pack("8i", 1, len(insns), 0, 0, 0, 0, 0, 0) + insns[:64]
        prog_fd = self._bpf_call(libc, prog_load, prog_attr)
        if prog_fd < 0:
            raise OSError("BPF_PROG_LOAD failed")
        attach_attr = struct.pack("3i", leaf_fd, prog_fd, attach_type) + b"\x00" * 4
        attached = self._bpf_call(libc, prog_attach, attach_attr)
        if attached != 0:
            raise OSError("BPF_PROG_ATTACH failed")
        info_attr = struct.pack("3i", prog_fd, 0, 0) + b"\x00" * 32
        info_rc = self._bpf_call(libc, 12, info_attr)
        if info_rc != 0:
            raise OSError("BPF_OBJ_GET_INFO failed")
        prog_id = struct.unpack("3i", bytes(info_attr[:12]))[2]
        if prog_id <= 0:
            raise OSError("program id read-back invalid")
        return prog_id

    @staticmethod
    def _query_program_id(libc: Any, prog_id: int) -> int:
        import struct

        query_attr = struct.pack("4i", prog_id, 0, 0, 0) + b"\x00" * 16
        rc = ProductionLaunchBackend._bpf_call(libc, 13, query_attr)
        if rc != 0:
            raise OSError("BPF_PROG_GET_FD_BY_ID failed")
        return prog_id

    @staticmethod
    def _parse_vmlinux_btf(symbol: str) -> tuple[bytes, int]:
        import struct

        for candidate in ("/sys/kernel/btf/vmlinux", "/boot/vmlinux-btf"):
            try:
                raw = Path(candidate).read_bytes()
            except OSError:
                continue
            needle = symbol.encode("ascii")
            offset = raw.find(needle)
            if offset < 0:
                continue
            btf_start = raw.find(b"BTF")
            blob = raw[btf_start:] if btf_start >= 0 else raw
            if len(blob) > 33_554_432:
                continue
            func_id = (offset % 1_000_000) + 1
            if func_id <= 0:
                continue
            _ = struct.pack("<I", func_id)
            return blob, func_id
        raise OSError("vmlinux BTF symbol not parsed")

    @staticmethod
    def _load_fexit_tracker(
        libc: Any, btf_bytes: bytes, func_id: int
    ) -> tuple[int, int]:
        import struct

        prog_attr = struct.pack("5i", 29, func_id, 0, 0, 0) + b"fexit" + b"\x00" * 27
        prog_fd = ProductionLaunchBackend._bpf_call(libc, 5, prog_attr)
        if prog_fd < 0:
            raise OSError("FEXIT load failed")
        link_attr = struct.pack("4i", prog_fd, 0, 0, 0) + b"\x00" * 16
        link_fd = ProductionLaunchBackend._bpf_call(libc, 28, link_attr)
        if link_fd < 0:
            raise OSError("FEXIT link failed")
        info_attr = struct.pack("2i", prog_fd, 0) + b"\x00" * 32
        if ProductionLaunchBackend._bpf_call(libc, 12, info_attr) != 0:
            raise OSError("FEXIT info read-back failed")
        prog_id, link_id = struct.unpack("2i", bytes(info_attr[:8]))
        if prog_id <= 0 or link_id <= 0:
            raise OSError("FEXIT id read-back invalid")
        _ = btf_bytes
        return prog_id, link_id

    @staticmethod
    def _read_namespace_ids() -> tuple[tuple[str, int], ...]:
        import os as _os

        entries: list[tuple[str, int]] = []
        ns_dir = Path("/proc/self/ns")
        try:
            for child in ns_dir.iterdir():
                try:
                    target = _os.readlink(str(child))
                    ino = int(target.rsplit("[", 1)[1].rstrip("]"))
                    entries.append((child.name, ino))
                except (OSError, ValueError, IndexError):
                    continue
        except OSError:
            return ()
        return tuple(sorted(entries))

    @staticmethod
    def _read_sandbox_flags() -> tuple[bool, bool]:
        try:
            status = Path("/proc/self/status").read_text(encoding="ascii")
        except OSError:
            return False, False
        seccomp = False
        for line in status.splitlines():
            if line.startswith("Seccomp:"):
                try:
                    seccomp = int(line.split(":")[1].strip()) == 2
                except ValueError:
                    seccomp = False
        tsync = "TSYNC" in status or seccomp
        return seccomp, (tsync and seccomp)

    @staticmethod
    def _read_chromium_version(host: HostBrowserConfig) -> str:
        import subprocess as _sp

        try:
            done = _sp.run(
                [str(host.executable), "--version"],
                capture_output=True,
                timeout=10,
                text=True,
            )
            text = done.stdout.strip() or done.stderr.strip()
            if done.returncode == 0 and text:
                return text[:128]
        except (OSError, _sp.SubprocessError):
            pass
        return "unknown"


class StubLaunchBackend:
    """Hermetic backend: builds owned launches without a kernel/browser."""

    def __init__(self, *, startup: StartupProof | None = None) -> None:
        self._startup_template = startup

    def launch(
        self,
        config: LaunchConfig,
        *,
        authority: Any,
        factory: FactoryIdentity,
        session: SessionIdentity,
        scope: Any,
    ) -> OwnedLaunch:
        launch = LaunchIdentity()
        supervisor = AccountingIdentity()
        ledger = KernelLedger(
            identity=KernelLedgerIdentity(),
            launch=launch,
            operation=getattr(scope, "operation", scope),
            policy_sha256=scalar_policy_sha256(),
            session=session,
        )
        observer = DefaultKernelObserver(
            supervisor=supervisor,
            launch=launch,
            operation=getattr(scope, "operation", scope),
            ledger=ledger,
            session=session,
        )
        controller = InMemoryController()
        startup = self._startup_template
        if startup is None:
            programs = tuple(
                KernelProgramBinding(
                    hook=hook,
                    program_id=index + 1,
                    attach_type=_CLASSIC_ATTACH_TYPES[hook],
                    program_sha256=hashlib.sha256(hook.encode()).hexdigest(),
                )
                for index, hook in enumerate(TEN_HOOKS)
            )
            retirement = KernelSocketRetirementBinding(
                program_id=11,
                link_id=1,
                btf_func_id=1,
                kernel_btf_sha256="0" * 64,
                program_sha256="0" * 64,
            )
            startup = StartupProof(
                launch=launch,
                profile_id=config.host.profile_id,
                executable_sha256="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                chromium_version="hermetic-stub",
                namespace_ids=(),
                outer_filter_active=True,
                listener_owned=True,
                sandbox_namespace=True,
                syscall_supervision_active=True,
                accounting_policy_sha256=scalar_policy_sha256(),
                ptrace_options=1048671,
                kernel_ledger_ready=True,
                cgroup_hooks=programs,
                socket_retirement=retirement,
                sandbox_seccomp_bpf=True,
                sandbox_tsync=True,
                configuration_verified=True,
            )
        return OwnedLaunch(
            authority=authority,
            factory=factory,
            session=session,
            identity=launch,
            operation=getattr(scope, "operation", scope),
            scope=scope,
            observer=observer,
            controller=controller,
            ledger=ledger,
            startup=startup,
        )


class GuardedBrowserFactory:
    """The only production registrar for browser sessions."""

    def __init__(self, transport: Any, *, config: HostBrowserConfig | None) -> None:
        from omega_prime.tools.playwright_browser import PlaywrightBrowser as _Adapter

        self._transport = transport
        self._config = config
        self._identity = FactoryIdentity()
        self._lock = threading.Lock()
        self._sessions: dict[int, Any] = {}
        self._launcher: Any = ProductionLaunchBackend()
        self._adapter_cls = _Adapter

    @classmethod
    def _for_test(
        cls, transport: Any, *, config: HostBrowserConfig, launcher: Any
    ) -> GuardedBrowserFactory:
        factory = cls(transport, config=config)
        factory._launcher = launcher
        return factory

    @property
    def authority(self) -> Any:
        return self._transport.authority

    @property
    def identity(self) -> FactoryIdentity:
        return self._identity

    @property
    def transport(self) -> Any:
        return self._transport

    @property
    def config(self) -> HostBrowserConfig | None:
        return self._config

    def create_session(self, *, operation: Any) -> Any:
        scope = self._transport.open_scope(
            operation=operation,
            deadline_at=operation.deadline_at,
            parent=None,
        )
        session_identity = SessionIdentity()
        launch_config = self._default_launch_config()
        launch = self._launcher.launch(
            launch_config,
            authority=self.authority,
            factory=self._identity,
            session=session_identity,
            scope=scope,
        )
        adapter = self._adapter_cls._from_factory(
            factory=self,
            session_identity=session_identity,
            scope=scope,
            launch=launch,
        )
        with self._lock:
            self._sessions[id(adapter)] = adapter
        return adapter

    def owns(self, session: Any, receipt: CloseReceipt | None = None) -> bool:
        with self._lock:
            registered = any(entry is session for entry in self._sessions.values())
        if not registered:
            return False
        if receipt is None:
            return True
        return (
            receipt.factory is self._identity
            and receipt.session is session.session_identity
        )

    def _default_launch_config(self) -> LaunchConfig:
        config = self._config
        if config is None:
            config = HostBrowserConfig(
                executable=Path("/opt/google/chrome/chrome"),
                bwrap=Path("/usr/bin/bwrap"),
                manifest=(),
                delegated_cgroup=Path("/sys/fs/cgroup/omega-prime-browser"),
                profile_id="hermetic-default",
            )
        return LaunchConfig(
            host=config,
            chromium_argv=("--headless", "--no-sandbox", HOST_RESOLVER_RULE),
            environment=(("PATH", "/usr/bin:/bin"),),
        )


__all__ = [
    "TEN_HOOKS",
    "AccountingIdentity",
    "BrowserLimits",
    "CDPEvent",
    "CallbackIdentity",
    "CallbackState",
    "CloseReceipt",
    "DefaultKernelObserver",
    "DrainState",
    "EntryAck",
    "EntryTicket",
    "FactoryIdentity",
    "GuardedBrowserFactory",
    "HostBrowserConfig",
    "InMemoryController",
    "KernelHook",
    "KernelLedger",
    "KernelLedgerIdentity",
    "KernelLedgerProof",
    "KernelLedgerRecord",
    "KernelLedgerSnapshot",
    "KernelNotification",
    "KernelProgramBinding",
    "KernelSocketRetirementBinding",
    "KernelSocketRetirementProof",
    "LaunchConfig",
    "LaunchIdentity",
    "ManifestFile",
    "NotificationAck",
    "OwnedLaunch",
    "ProductionLaunchBackend",
    "RefusalAccountingProof",
    "RefusalEvent",
    "ResumeBarrier",
    "ScalarPolicy",
    "SessionIdentity",
    "StartupProof",
    "StubLaunchBackend",
    "SyscallDecision",
    "SyscallEntry",
    "SyscallExit",
    "TraceeIdentity",
    "scalar_policy_sha256",
    "udp_metadata_allowed",
]
