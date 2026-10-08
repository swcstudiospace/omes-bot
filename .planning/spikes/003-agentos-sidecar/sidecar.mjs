// Spike 003: minimal AgentOS sidecar that Omega (Python) calls over HTTP.
//
// One embedded AgentOS VM is created at boot and reused for every request.
// The server binds 127.0.0.1 on a random free port and prints exactly one
// line `READY {json}` to stdout once the VM and the listener are up.
//
//   GET  /health     -> versions, cold-start timings, memory
//   POST /exec       -> {command} via vm.process.exec (bash command line)
//                       {code, language?} via vm.javascript|typescript.execute
//                       optional files:[{path,content}] written first via vm.filesystem.writeFile
//   POST /typecheck  -> {source, filePath?, compilerOptions?} via vm.typescript.check
//   POST /shutdown   -> disposes the VM and exits
//
// API reference: @rivet-dev/agentos-core 0.2.22 (dist/agent-os.d.ts, dist/language-execution.d.ts)
// and https://rivet.dev/agentos/docs/ (javascript, processes, permissions, resource-limits).
import { readFileSync } from "node:fs";
import http from "node:http";
import { AgentOs } from "@rivet-dev/agentos-core";

const MAX_BODY_BYTES = 1024 * 1024;
const DEFAULT_TIMEOUT_MS = 10_000;
const MAX_TIMEOUT_MS = 60_000;
// Backstop beyond the AgentOS wall-clock deadline: if the library ever fails to
// honour timeoutMs, the HTTP layer aborts the operation and answers 504.
const BACKSTOP_GRACE_MS = 15_000;

const t0 = performance.now();

function pkgVersion(name) {
	try {
		const url = new URL(`./node_modules/${name}/package.json`, import.meta.url);
		return JSON.parse(readFileSync(url, "utf8")).version;
	} catch {
		return null;
	}
}

const versions = {
	node: process.version,
	"@rivet-dev/agentos-core": pkgVersion("@rivet-dev/agentos-core"),
	"@rivet-dev/agentos-sidecar": pkgVersion("@rivet-dev/agentos-sidecar"),
	"@rivet-dev/agentos-runtime-core": pkgVersion("@rivet-dev/agentos-runtime-core"),
	"@agentos-software/common": pkgVersion("@agentos-software/common"),
};

// Default permissions on purpose: per AgentOsOptions.permissions the guest
// filesystem, processes, env, listeners and loopback work while external
// network access is denied. Omega's sidecar must not open egress.
const vm = await AgentOs.create();
const tVm = performance.now();

let disposing = null;
async function shutdown(code) {
	if (!disposing) {
		disposing = (async () => {
			server.close();
			try {
				await vm.dispose();
			} catch (err) {
				console.error("dispose failed:", err);
				code = 1;
			}
			process.exit(code);
		})();
	}
	return disposing;
}

function clampTimeout(value) {
	if (value === undefined) return DEFAULT_TIMEOUT_MS;
	if (!Number.isInteger(value) || value <= 0) throw new BadRequest("timeoutMs must be a positive integer");
	return Math.min(value, MAX_TIMEOUT_MS);
}

class BadRequest extends Error {}

function readJson(req) {
	return new Promise((resolve, reject) => {
		const chunks = [];
		let size = 0;
		req.on("data", (chunk) => {
			size += chunk.length;
			if (size > MAX_BODY_BYTES) {
				reject(new BadRequest(`body exceeds ${MAX_BODY_BYTES} bytes`));
				req.destroy();
				return;
			}
			chunks.push(chunk);
		});
		req.on("end", () => {
			try {
				resolve(chunks.length ? JSON.parse(Buffer.concat(chunks).toString("utf8")) : {});
			} catch {
				reject(new BadRequest("body is not valid JSON"));
			}
		});
		req.on("error", reject);
	});
}

function send(res, status, body) {
	const payload = JSON.stringify(body);
	res.writeHead(status, { "content-type": "application/json", "content-length": Buffer.byteLength(payload) });
	res.end(payload);
}

// Runs `op(signal)` with the library deadline plus an HTTP backstop.
async function withBackstop(timeoutMs, op) {
	const controller = new AbortController();
	let timer;
	const backstop = new Promise((resolve) => {
		timer = setTimeout(() => {
			controller.abort();
			resolve({ backstop: true });
		}, timeoutMs + BACKSTOP_GRACE_MS);
	});
	try {
		return await Promise.race([op(controller.signal).then((value) => ({ value })), backstop]);
	} finally {
		clearTimeout(timer);
	}
}

function shapeExecution(result, durationMs) {
	return {
		outcome: result.outcome,
		exitCode: result.exitCode ?? null,
		stdout: result.stdout ?? "",
		stderr: result.stderr ?? "",
		stdoutTruncated: result.stdoutTruncated ?? false,
		stderrTruncated: result.stderrTruncated ?? false,
		error: result.error ?? null,
		durationMs,
	};
}

async function handleExec(body) {
	const hasCommand = typeof body.command === "string";
	const hasCode = typeof body.code === "string";
	if (hasCommand === hasCode) throw new BadRequest("send exactly one of `command` or `code` (string)");
	const language = body.language ?? "javascript";
	if (!["javascript", "typescript"].includes(language)) throw new BadRequest("language must be javascript or typescript");
	const timeoutMs = clampTimeout(body.timeoutMs);
	const files = body.files ?? [];
	if (!Array.isArray(files)) throw new BadRequest("files must be an array of {path, content}");

	const started = performance.now();
	for (const file of files) {
		if (typeof file?.path !== "string" || typeof file?.content !== "string") {
			throw new BadRequest("each file needs string `path` and `content`");
		}
		await vm.filesystem.writeFile(file.path, file.content);
	}
	const options = { timeoutMs, output: { capture: "all" } };
	if (typeof body.cwd === "string") options.cwd = body.cwd;
	if (typeof body.stdin === "string") options.stdin = body.stdin;

	const raced = await withBackstop(timeoutMs, (signal) => {
		const opts = { ...options, signal };
		if (hasCommand) return vm.process.exec(body.command, opts);
		return language === "typescript" ? vm.typescript.execute(body.code, opts) : vm.javascript.execute(body.code, opts);
	});
	const durationMs = Math.round(performance.now() - started);
	if (raced.backstop) return [504, { outcome: "backstop_timeout", durationMs, error: { code: "backstop_timeout", message: `no result ${BACKSTOP_GRACE_MS} ms after timeoutMs` } }];
	return [200, shapeExecution(raced.value, durationMs)];
}

async function handleTypecheck(body) {
	if (typeof body.source !== "string") throw new BadRequest("`source` (string) is required");
	const timeoutMs = clampTimeout(body.timeoutMs);
	const options = { filePath: typeof body.filePath === "string" ? body.filePath : "input.ts", timeoutMs };
	if (body.compilerOptions && typeof body.compilerOptions === "object") options.compilerOptions = body.compilerOptions;

	const started = performance.now();
	const raced = await withBackstop(timeoutMs, (signal) => vm.typescript.check(body.source, { ...options, signal }));
	const durationMs = Math.round(performance.now() - started);
	if (raced.backstop) return [504, { outcome: "backstop_timeout", durationMs, diagnostics: [] }];
	const result = raced.value;
	return [
		200,
		{
			outcome: result.outcome,
			hasErrors: result.hasErrors ?? null,
			diagnostics: result.diagnostics ?? [],
			error: result.error ?? null,
			durationMs,
		},
	];
}

const server = http.createServer(async (req, res) => {
	try {
		if (req.method === "GET" && req.url === "/health") {
			return send(res, 200, {
				status: disposing ? "stopping" : "ok",
				pid: process.pid,
				versions,
				coldStart: { vmCreateMs: Math.round(tVm - t0), readyMs: Math.round(tReady - t0) },
				memory: process.memoryUsage(),
			});
		}
		if (req.method !== "POST") return send(res, 405, { error: "method not allowed" });
		if (req.url === "/shutdown") {
			send(res, 202, { status: "stopping" });
			setImmediate(() => shutdown(0));
			return;
		}
		if (disposing) return send(res, 503, { error: "stopping" });
		const body = await readJson(req);
		if (req.url === "/exec") return send(res, ...(await handleExec(body)));
		if (req.url === "/typecheck") return send(res, ...(await handleTypecheck(body)));
		return send(res, 404, { error: "not found" });
	} catch (err) {
		if (err instanceof BadRequest) return send(res, 400, { error: err.message });
		// AgentOS rejects (rather than resolving with an outcome) for VM-level
		// failures; surface its typed fields so the caller can decide.
		return send(res, 500, { error: { name: err?.name, code: err?.code, message: String(err?.message ?? err) } });
	}
});

let tReady = 0;
server.listen(0, "127.0.0.1", () => {
	tReady = performance.now();
	const { port } = server.address();
	process.stdout.write(
		`READY ${JSON.stringify({ port, pid: process.pid, vmCreateMs: Math.round(tVm - t0), readyMs: Math.round(tReady - t0) })}\n`,
	);
});

process.on("SIGTERM", () => shutdown(0));
process.on("SIGINT", () => shutdown(0));
