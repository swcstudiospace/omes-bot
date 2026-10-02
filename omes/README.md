# Omes

The single programming bot. Prompts point at `skills/`, `contracts/tool-rosters/omes.yaml`, and `prompts/`. The Grok template in `grokbot/templates/OMES.md` lists a skill or routine only when that file exists.

Assemble the seat prompt:

```bash
omes/scripts/assemble-prompts.sh
omes/scripts/assemble-prompts.sh --check
```

From the repository root:

```bash
python3 -m pytest omes/tests
```

`agent/`, `tools/`, and `cron/` are where later phases land the Hermes loop, the tool registry, and the scheduler. They are empty until those phases.
