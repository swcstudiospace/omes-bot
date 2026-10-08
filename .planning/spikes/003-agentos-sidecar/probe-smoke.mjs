// Smoke probe: does the documented embedded API boot and run on this host?
// Run: node probe-smoke.mjs
import { AgentOs } from "@rivet-dev/agentos-core";

const t0 = performance.now();
const vm = await AgentOs.create();
const tBoot = performance.now();
console.log(`create(): ${(tBoot - t0).toFixed(0)} ms`);
try {
	await vm.filesystem.writeFile("/tmp/hello.txt", "hello\n");
	const r = await vm.process.exec("cat /tmp/hello.txt", { output: { capture: "all" } });
	console.log("process.exec:", JSON.stringify(r));
	const j = await vm.javascript.execute(`console.log("js", 1+1)`, { output: { capture: "all" } });
	console.log("javascript.execute:", JSON.stringify(j));
	const t1 = performance.now();
	const c = await vm.typescript.check(`const total: number = "nope";`, { filePath: "x.ts" });
	console.log(`typescript.check (${(performance.now() - t1).toFixed(0)} ms):`, JSON.stringify(c));
} finally {
	await vm.dispose();
}
console.log(`total: ${(performance.now() - t0).toFixed(0)} ms`);
