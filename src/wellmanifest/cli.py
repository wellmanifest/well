from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

import yaml

from .env_contract import load_env_contract, setup_env, sync_env_contract, verify_env_contract
from .governance import (
    FORMAT_PROFILES,
    GovernanceBuilder,
    available_profiles,
    format_semantic_diff,
    lint_policy_document,
    roundtrip_document,
    semantic_diff,
    serialize_profile,
)
from .intent_analysis import analyze_intent_project, todo2code_evidence
from .models import ConversionRequest, Document, DocumentMetadata, ExecuteRequest, RuntimeTarget, ValidationRequest
from .runtime import WellManifestRuntime
from .type_bridge import (
    json_schema_to_python,
    json_schema_to_typed_module,
    json_schema_to_typescript,
    typed_module_to_json_schema,
)
from .version import __version__
from .versions import build_version_registry, load_version_registry, serialize_registry, sync_version_registry


def _read(path: str) -> str:
    if path == "-":
        return sys.stdin.read()
    return Path(path).read_text(encoding="utf-8")


def _load_json(path: str) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _load_data(path: str) -> dict[str, Any]:
    text = Path(path).read_text(encoding="utf-8")
    if Path(path).suffix.lower() in {".yaml", ".yml"}:
        value = yaml.safe_load(text)
    else:
        value = json.loads(text)
    if not isinstance(value, dict):
        raise ValueError(f"Expected an object in {path}")
    return value


def _write_output(text: str, output: str = "-") -> None:
    if output == "-":
        print(text, end="" if text.endswith("\n") else "\n")
    else:
        Path(output).parent.mkdir(parents=True, exist_ok=True)
        Path(output).write_text(text, encoding="utf-8")


def _emit_data(runtime: WellManifestRuntime, data: Any, dialect: str) -> str:
    document = Document(
        metadata=DocumentMetadata(source_dialect="json@rfc8259"),
        data=data,
        ir={"kind": "data", "value": data},
    )
    return runtime.registry.get(dialect).emit(document, projection="data", pretty=True)


def _source_mappings(values: list[str]) -> dict[str, str]:
    mappings: dict[str, str] = {}
    for value in values:
        if "=" not in value:
            raise ValueError(f"Invalid --source-ref {value!r}; expected REF=PATH")
        reference, path = value.split("=", 1)
        if not reference or not path:
            raise ValueError(f"Invalid --source-ref {value!r}; expected REF=PATH")
        mappings[reference] = path
    return mappings


def _print_diagnostics(items: list[Any]) -> None:
    for item in items:
        diagnostic = item.model_dump(mode="json") if hasattr(item, "model_dump") else item
        location = ""
        if diagnostic.get("source"):
            location = str(diagnostic["source"])
            source_range = diagnostic.get("range")
            if source_range:
                location += f":{source_range['start']['line']}:{source_range['start']['column']}"
            location += ": "
        print(
            f"{location}{diagnostic['severity']} {diagnostic['code']}: {diagnostic['message']}",
            file=sys.stderr,
        )


def _has_errors(items: list[Any]) -> bool:
    for item in items:
        severity = item.severity.value if hasattr(item, "severity") else item.get("severity")
        if severity == "ERROR":
            return True
    return False


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="wellm", description="WellManifest protocol and dialect runtime")
    parser.add_argument("--version", action="version", version=f"wellm {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    inspect_parser = subparsers.add_parser("inspect", help="Parse a document and emit full WellManifest IR")
    inspect_parser.add_argument("file")
    inspect_parser.add_argument("--dialect", default="auto")

    run_parser = subparsers.add_parser(
        "run",
        help="Run a shebang-selected dialect and emit its canonical data or IR projection",
    )
    run_parser.add_argument("file")
    run_parser.add_argument("--dialect", default="auto")
    run_parser.add_argument("--projection", choices=["auto", "data", "ir"], default="auto")
    run_parser.add_argument("--to", dest="target_dialect", default="json")
    run_parser.add_argument("--schema")
    run_parser.add_argument("--compact", action="store_true")

    convert_parser = subparsers.add_parser("convert", help="Convert between dialects")
    convert_parser.add_argument("file")
    convert_parser.add_argument("--from", dest="source_dialect", default="auto")
    convert_parser.add_argument("--to", dest="target_dialect", required=True)
    convert_parser.add_argument("--projection", choices=["data", "ir"], default="data")
    convert_parser.add_argument("--schema")
    convert_parser.add_argument("--output", "-o", default="-")
    convert_parser.add_argument("--compact", action="store_true")
    convert_parser.add_argument(
        "--types",
        dest="type_mode",
        choices=["preserve", "schema", "infer", "none"],
        default="preserve",
        help="Type metadata strategy when emitting typed@1.",
    )

    validate_parser = subparsers.add_parser("validate", help="Validate against JSON Schema 2020-12")
    validate_parser.add_argument("file")
    validate_parser.add_argument("--dialect", default="auto")
    validate_parser.add_argument("--schema", required=True)

    fmt_parser = subparsers.add_parser("fmt", help="Format data using a named Wellm format profile")
    fmt_parser.add_argument("file")
    fmt_parser.add_argument("--dialect", default="auto")
    fmt_parser.add_argument("--profile", default="repo-json@1", choices=sorted(FORMAT_PROFILES))
    fmt_parser.add_argument("--schema")
    fmt_parser.add_argument("--output", "-o", default="-")
    fmt_parser.add_argument("--check", action="store_true")

    diff_parser = subparsers.add_parser("semantic-diff", help="Compare two documents by normalized meaning")
    diff_parser.add_argument("left")
    diff_parser.add_argument("right")
    diff_parser.add_argument("--left-dialect", default="auto")
    diff_parser.add_argument("--right-dialect", default="auto")
    diff_parser.add_argument("--format", choices=["text", "json"], default="text")
    diff_parser.add_argument("--output", "-o", default="-")

    roundtrip_parser = subparsers.add_parser("roundtrip", help="Test semantic round-trips through dialects")
    roundtrip_parser.add_argument("file")
    roundtrip_parser.add_argument("--dialect", default="auto")
    roundtrip_parser.add_argument("--via", required=True, help="Comma-separated dialect list, e.g. yaml,json,typescript")
    roundtrip_parser.add_argument("--schema")
    roundtrip_parser.add_argument("--output", "-o", default="-")

    schema_parser = subparsers.add_parser("schema", help="Import/export JSON Schema and generate language types")
    schema_sub = schema_parser.add_subparsers(dest="schema_command", required=True)
    schema_import = schema_sub.add_parser("import", help="Import JSON Schema 2020-12 into a typed Wellm module")
    schema_import.add_argument("file")
    schema_import.add_argument("--root-type")
    schema_import.add_argument("--output", "-o", default="-")
    schema_export = schema_sub.add_parser("export", help="Export a typed Wellm schema module to JSON Schema")
    schema_export.add_argument("file")
    schema_export.add_argument("--output", "-o", default="-")
    schema_codegen = schema_sub.add_parser("codegen", help="Generate static types from JSON Schema or a typed schema module")
    schema_codegen.add_argument("file")
    schema_codegen.add_argument("--from", dest="source_format", choices=["json-schema", "typed"], default="json-schema")
    schema_codegen.add_argument("--language", choices=["typescript", "python"], required=True)
    schema_codegen.add_argument("--root-type")
    schema_codegen.add_argument("--output", "-o", default="-")

    intent_parser = subparsers.add_parser("intent", help="Compare intent represented in multiple file formats")
    intent_sub = intent_parser.add_subparsers(dest="intent_command", required=True)
    intent_analyze = intent_sub.add_parser("analyze", help="Analyze semantic and schema drift between representations")
    intent_analyze.add_argument("project", help="wellm.intent-format-project/v1 JSON or YAML")
    intent_analyze.add_argument("--output", "-o", default="-")
    intent_analyze.add_argument("--todo2code-evidence")

    env_parser = subparsers.add_parser("env", help="Manage and verify the global environment contract")
    env_sub = env_parser.add_subparsers(dest="env_command", required=True)
    env_sub.add_parser("show", help="Print the environment contract without secret values")
    env_setup = env_sub.add_parser("setup", help="Create .env from .env.example if missing")
    env_setup.add_argument("--force", action="store_true")
    env_sub.add_parser("sync", help="Regenerate .env.example and packaged contract")
    env_check = env_sub.add_parser("check", help="Verify variable declarations and .env values")
    env_check.add_argument("--dotenv")

    versions_parser = subparsers.add_parser("versions", help="Print, synchronize or verify format/API/schema versions")
    versions_parser.add_argument("--write", action="store_true")
    versions_parser.add_argument("--check", action="store_true")
    versions_parser.add_argument("--output", "-o", default="-")

    governance_parser = subparsers.add_parser("governance", help="Build deterministic governance artifacts")
    governance_sub = governance_parser.add_subparsers(dest="governance_command", required=True)
    governance_build = governance_sub.add_parser("build", help="Build or check a wellm.governance-project/v1 file")
    governance_build.add_argument("project")
    governance_build.add_argument("--check", action="store_true")
    governance_build.add_argument("--report")

    policy_parser = subparsers.add_parser("policy", help="Import, lint and format policy DSL in Markdown")
    policy_sub = policy_parser.add_subparsers(dest="policy_command", required=True)
    policy_import = policy_sub.add_parser("import", help="Import policy or Markdown fenced blocks to policy IR")
    policy_import.add_argument("file")
    policy_import.add_argument("--output", "-o", default="-")
    policy_lint = policy_sub.add_parser("lint", help="Lint rule identifiers and state-machine references")
    policy_lint.add_argument("file")
    policy_lint.add_argument("--undeclared-states", choices=["error", "warning", "ignore"], default="error")
    policy_lint.add_argument("--format", choices=["text", "json"], default="text")
    policy_fmt = policy_sub.add_parser("fmt", help="Rewrite policy-shaped compatibility fences")
    policy_fmt.add_argument("file")
    policy_fmt.add_argument("--rewrite-fences", action="store_true")
    policy_fmt.add_argument("--target-fence", choices=["dsl", "policy", "wellm-policy"], default="wellm-policy")
    policy_fmt.add_argument("--check", action="store_true")
    policy_fmt.add_argument("--output", "-o")

    execute_parser = subparsers.add_parser("execute", help="Execute a registered URI Process")
    execute_parser.add_argument("uri")
    execute_parser.add_argument("--payload", default="{}", help="JSON payload or @path/to/file.json")
    execute_parser.add_argument("--contract", default="contract:dev")
    execute_parser.add_argument("--run-id", default="")
    execute_parser.add_argument("--environment", default="backend")
    execute_parser.add_argument("--runtime", dest="runtime_ref", default="runtime:backend-python@1")

    plesk_plan = subparsers.add_parser("plesk-plan", help="Build a fail-closed Plesk publication plan")
    plesk_plan.add_argument("config", help="subactor.projects/v1 JSON or YAML")
    plesk_plan.add_argument("--project", required=True)
    plesk_plan.add_argument("--source-ref", action="append", default=[], metavar="REF=PATH")
    plesk_plan.add_argument("--workspace-root")
    plesk_plan.add_argument("--to", choices=["json", "yaml", "typed", "hcl", "typescript", "toon"], default="json")
    plesk_plan.add_argument("--output", "-o", default="-")

    plesk_publish = subparsers.add_parser(
        "plesk-publish",
        help="Run Plesk connector preflight/dry-run; apply only with an exact plan hash and signed grant",
    )
    plesk_publish.add_argument("config")
    plesk_publish.add_argument("--project", required=True)
    plesk_publish.add_argument("--source-ref", action="append", default=[], metavar="REF=PATH")
    plesk_publish.add_argument("--workspace-root")
    plesk_publish.add_argument("--node-url")
    plesk_publish.add_argument("--token-env", default="URIRUN_TOKEN")
    plesk_publish.add_argument("--contract")
    plesk_publish.add_argument("--apply", action="store_true")
    plesk_publish.add_argument("--plan-hash")
    plesk_publish.add_argument("--apply-grant-env", default="URIRUN_APPLY_GRANT")
    plesk_publish.add_argument("--output", "-o", default="-")

    benchmark = subparsers.add_parser(
        "benchmark-llm",
        help="Benchmark LLM format/logic capability and select the cheapest capable candidate",
    )
    benchmark.add_argument("config", help="wellmanifest.llm-benchmark/v1 JSON or YAML")
    benchmark.add_argument("--fixture", help="Project/config fixture; overrides fixture_file")
    benchmark.add_argument("--mock", action="store_true", help="Use the deterministic offline adapter")
    benchmark.add_argument("--output-dir", default=".wellm/benchmark")

    subparsers.add_parser("capabilities", help="Print runtime capabilities")
    subparsers.add_parser("profiles", help="Print named data-formatting profiles")

    serve_parser = subparsers.add_parser("serve", help="Run HTTP/WebSocket runtime gateway")
    serve_parser.add_argument("--host", default="0.0.0.0")
    serve_parser.add_argument("--port", type=int, default=8080)

    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    runtime = WellManifestRuntime()

    if args.command == "versions":
        try:
            if args.write:
                registry = sync_version_registry()
            elif args.check:
                registry = sync_version_registry(check=True)
            else:
                registry = load_version_registry()
        except ValueError as exc:
            print(f"ERROR WM-VERSION-001: {exc}", file=sys.stderr)
            raise SystemExit(1) from exc
        _write_output(serialize_registry(registry), args.output)
        return

    if args.command == "env":
        if args.env_command == "show":
            print(json.dumps(load_env_contract(), ensure_ascii=False, indent=2))
            return
        if args.env_command == "setup":
            print(setup_env(force=args.force))
            return
        if args.env_command == "sync":
            sync_env_contract()
            print("environment contract synchronized")
            return
        report = verify_env_contract(dotenv=args.dotenv)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        raise SystemExit(0 if report["ok"] else 1)

    if args.command == "schema":
        if args.schema_command == "import":
            schema = _load_json(args.file)
            _write_output(json_schema_to_typed_module(schema, root_name=args.root_type), args.output)
            return
        if args.schema_command == "export":
            schema = typed_module_to_json_schema(_read(args.file), source_name=args.file)
            _write_output(json.dumps(schema, ensure_ascii=False, indent=2) + "\n", args.output)
            return
        schema = (
            typed_module_to_json_schema(_read(args.file), source_name=args.file)
            if args.source_format == "typed"
            else _load_json(args.file)
        )
        output = (
            json_schema_to_typescript(schema, root_name=args.root_type)
            if args.language == "typescript"
            else json_schema_to_python(schema, root_name=args.root_type)
        )
        _write_output(output, args.output)
        return

    if args.command == "intent":
        report = analyze_intent_project(runtime, args.project)
        rendered = json.dumps(report.model_dump(mode="json", by_alias=True), ensure_ascii=False, indent=2) + "\n"
        _write_output(rendered, args.output)
        if args.todo2code_evidence:
            evidence = todo2code_evidence(report)
            _write_output(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", args.todo2code_evidence)
        _print_diagnostics(report.diagnostics)
        raise SystemExit(0 if report.equivalent else 1)

    if args.command == "inspect":
        source = _read(args.file)
        document = runtime.parse(source, dialect=args.dialect, source_name=args.file)
        target = runtime.registry.get("json")
        print(target.emit(document, projection="ir"), end="")
        _print_diagnostics(document.diagnostics)
        raise SystemExit(1 if not document.ok else 0)

    if args.command == "run":
        source = _read(args.file)
        document = runtime.parse(source, dialect=args.dialect, source_name=args.file)
        projection = args.projection
        if projection == "auto":
            projection = "data" if document.metadata.document_kind == "data" else "ir"
        diagnostics = list(document.diagnostics)
        if args.schema and projection == "data":
            diagnostics.extend(
                runtime.schema_validator.validate(
                    document.data,
                    _load_json(args.schema),
                    source=args.file,
                    source_map=document.source_map,
                )
            )
        target = runtime.registry.get(args.target_dialect)
        try:
            output = target.emit(document, projection=projection, pretty=not args.compact)
        except (ValueError, TypeError, KeyError) as exc:
            print(f"ERROR WM-RUN-001: {exc}", file=sys.stderr)
            raise SystemExit(2) from exc
        _print_diagnostics(diagnostics)
        print(output, end="" if output.endswith("\n") else "\n")
        raise SystemExit(1 if _has_errors(diagnostics) else 0)

    if args.command == "convert":
        schema = _load_json(args.schema) if args.schema else None
        result = runtime.convert(
            ConversionRequest(
                source=_read(args.file),
                source_dialect=args.source_dialect,
                target_dialect=args.target_dialect,
                projection=args.projection,
                schema=schema,
                source_name=args.file,
                pretty=not args.compact,
                type_mode=args.type_mode,
            )
        )
        _print_diagnostics(result.diagnostics)
        if result.output is None:
            raise SystemExit(2)
        output = result.output if isinstance(result.output, str) else json.dumps(result.output, ensure_ascii=False, indent=2)
        _write_output(output, args.output)
        raise SystemExit(1 if _has_errors(result.diagnostics) else 0)

    if args.command == "validate":
        result = runtime.validate(
            ValidationRequest(
                source=_read(args.file),
                dialect=args.dialect,
                schema=_load_json(args.schema),
                source_name=args.file,
            )
        )
        _print_diagnostics(result.diagnostics)
        print(json.dumps({"valid": result.valid}, ensure_ascii=False))
        raise SystemExit(0 if result.valid else 1)

    if args.command == "fmt":
        source = _read(args.file)
        document = runtime.parse(source, dialect=args.dialect, source_name=args.file)
        schema = _load_json(args.schema) if args.schema else None
        diagnostics = list(document.diagnostics)
        if schema is not None:
            diagnostics.extend(
                runtime.schema_validator.validate(
                    document.data,
                    schema,
                    source=args.file,
                    source_map=document.source_map,
                )
            )
        if args.profile in {"repo-json@1", "json-data@1", "wire-json@1", "yaml-json@1", "typescript-data@1"}:
            rendered = serialize_profile(document.data, args.profile, schema=schema)
        elif args.profile == "wellm-typed@1":
            rendered = runtime.registry.get("typed").emit(document, projection="data", pretty=True)
        elif args.profile == "hcl-static@1":
            rendered = runtime.registry.get("hcl").emit(document, projection="data", pretty=True)
        elif args.profile == "policy-md@1":
            from .dialects.policy import PolicyDialect

            rendered, _ = PolicyDialect.rewrite_fences(source)
        else:
            parser.error(f"Profile {args.profile} is not supported by fmt")
        _print_diagnostics(diagnostics)
        compare_path = Path(args.output) if args.output != "-" else (Path(args.file) if args.file != "-" else None)
        if args.check:
            current = compare_path.read_text(encoding="utf-8") if compare_path and compare_path.exists() else None
            if current != rendered or _has_errors(diagnostics):
                raise SystemExit(1)
            return
        _write_output(rendered, args.output)
        raise SystemExit(1 if _has_errors(diagnostics) else 0)

    if args.command == "semantic-diff":
        left = runtime.parse(_read(args.left), dialect=args.left_dialect, source_name=args.left)
        right = runtime.parse(_read(args.right), dialect=args.right_dialect, source_name=args.right)
        report = semantic_diff(left.data, right.data)
        rendered = (
            json.dumps(report.model_dump(mode="json", by_alias=True), ensure_ascii=False, indent=2) + "\n"
            if args.format == "json"
            else format_semantic_diff(report)
        )
        _write_output(rendered, args.output)
        raise SystemExit(0 if report.equivalent else 1)

    if args.command == "roundtrip":
        document = runtime.parse(_read(args.file), dialect=args.dialect, source_name=args.file)
        schema = _load_json(args.schema) if args.schema else None
        report = roundtrip_document(
            runtime,
            document,
            [item.strip() for item in args.via.split(",") if item.strip()],
            schema=schema,
        )
        _write_output(
            json.dumps(report.model_dump(mode="json", by_alias=True), ensure_ascii=False, indent=2) + "\n",
            args.output,
        )
        _print_diagnostics(report.diagnostics)
        raise SystemExit(0 if report.equivalent and not _has_errors(report.diagnostics) else 1)

    if args.command == "governance":
        if args.governance_command == "build":
            report = GovernanceBuilder(runtime).build(args.project, check=args.check)
            rendered = json.dumps(report.model_dump(mode="json", by_alias=True), ensure_ascii=False, indent=2) + "\n"
            if args.report:
                _write_output(rendered, args.report)
            else:
                print(rendered, end="")
            _print_diagnostics(report.diagnostics)
            raise SystemExit(0 if report.ok else 1)

    if args.command == "policy":
        from .dialects.policy import PolicyDialect

        source = _read(args.file)
        if args.policy_command == "import":
            document = runtime.parse(source, dialect="policy", source_name=args.file)
            output = runtime.registry.get("json").emit(document, projection="ir")
            _write_output(output, args.output)
            _print_diagnostics(document.diagnostics)
            raise SystemExit(1 if _has_errors(document.diagnostics) else 0)
        if args.policy_command == "lint":
            document = runtime.parse(source, dialect="policy", source_name=args.file)
            diagnostics = [
                *document.diagnostics,
                *lint_policy_document(document, undeclared_states=args.undeclared_states),
            ]
            if args.format == "json":
                print(
                    json.dumps(
                        {
                            "valid": not _has_errors(diagnostics),
                            "ruleCount": len(document.ir.get("rules", [])),
                            "stateCount": len(document.ir.get("states", [])),
                            "diagnostics": [item.model_dump(mode="json") for item in diagnostics],
                        },
                        ensure_ascii=False,
                        indent=2,
                    )
                )
            else:
                _print_diagnostics(diagnostics)
            raise SystemExit(1 if _has_errors(diagnostics) else 0)
        if args.policy_command == "fmt":
            rendered = source
            replacements = 0
            if args.rewrite_fences:
                rendered, replacements = PolicyDialect.rewrite_fences(source, target=args.target_fence)
            output_path = args.output or args.file
            if args.check:
                if replacements or rendered != source:
                    raise SystemExit(1)
                return
            _write_output(rendered, output_path)
            print(json.dumps({"rewrittenFences": replacements, "output": output_path}))
            return

    if args.command == "execute":
        if args.payload.startswith("@"):
            payload = json.loads(Path(args.payload[1:]).read_text(encoding="utf-8"))
        else:
            payload = json.loads(args.payload)
        response = runtime.execute_uri(
            ExecuteRequest(
                uri=args.uri,
                payload=payload,
                contract_ref=args.contract,
                run_id=args.run_id,
                runtime=RuntimeTarget(
                    runtime_ref=args.runtime_ref,
                    environment=args.environment,
                    execution="local",
                ),
            )
        )
        print(json.dumps(response.model_dump(mode="json"), ensure_ascii=False, indent=2))
        raise SystemExit(0 if response.ok else 1)

    if args.command in {"plesk-plan", "plesk-publish"}:
        from .plesk import (
            PleskPublicationExecutor,
            PleskPublicationPlanner,
            WorkspaceResolver,
            load_project_registry,
        )
        from .urirun import UrirunProcessClient

        registry = load_project_registry(args.config)
        resolver = WorkspaceResolver(
            mappings=_source_mappings(args.source_ref),
            workspace_root=args.workspace_root,
        )
        plan = PleskPublicationPlanner(registry, resolver).build(args.project)

        if args.command == "plesk-plan":
            output = _emit_data(runtime, plan.model_dump(mode="json", by_alias=True), args.to)
            _write_output(output, args.output)
            raise SystemExit(1 if _has_errors(plan.diagnostics) else 0)

        node_url = args.node_url or registry.connector.node_url
        if not node_url:
            parser.error("plesk-publish requires --node-url or connector.node_url in the registry")
        token = os.getenv(args.token_env, "")
        contract = args.contract or registry.connector.contract_ref
        client = UrirunProcessClient(node_url=node_url, token=token, contract_ref=contract)
        executor = PleskPublicationExecutor(client)
        dry = executor.dry_run(plan)
        receipt = dry
        if args.apply:
            grant = os.getenv(args.apply_grant_env, "")
            receipt = executor.apply(
                plan,
                plan_hash=args.plan_hash or "",
                apply_grant=grant,
                dry_run_receipt=dry,
            )
        _write_output(
            json.dumps(receipt.model_dump(mode="json", by_alias=True), ensure_ascii=False, indent=2) + "\n",
            args.output,
        )
        raise SystemExit(0 if receipt.ok else 1)

    if args.command == "benchmark-llm":
        from .llmbench import BenchmarkConfig, BenchmarkRunner, LiteLLMAdapter, MockAdapter, build_cases, write_report

        config_path = Path(args.config)
        config = BenchmarkConfig.model_validate(_load_data(str(config_path)))
        fixture_path = args.fixture or config.fixture_file
        if not fixture_path:
            parser.error("benchmark-llm requires --fixture or fixture_file in the benchmark config")
        fixture_candidate = Path(fixture_path)
        if not fixture_candidate.is_absolute():
            fixture_candidate = config_path.parent / fixture_candidate
        fixture = _load_data(str(fixture_candidate))
        cases = build_cases(fixture, list(config.formats), runtime=runtime)
        if args.mock:
            behaviors = config.metadata.get("mock_behaviors", {})
            adapter = MockAdapter(behaviors if isinstance(behaviors, dict) else {})
        else:
            adapter = LiteLLMAdapter()
        report = BenchmarkRunner(adapter, runtime=runtime).run(config, cases)
        json_path, markdown_path = write_report(report, args.output_dir)
        print(
            json.dumps(
                {
                    "selected_model_id": report.selected_model_id,
                    "selected_model": report.selected_model,
                    "selected_format": report.selected_format,
                    "json_report": str(json_path),
                    "markdown_report": str(markdown_path),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        raise SystemExit(0 if report.selected_model_id else 1)

    if args.command == "capabilities":
        print(json.dumps(runtime.capabilities(), ensure_ascii=False, indent=2))
        return

    if args.command == "profiles":
        print(json.dumps(available_profiles(), ensure_ascii=False, indent=2))
        return

    if args.command == "serve":
        import uvicorn

        uvicorn.run("wellmanifest.server:app", host=args.host, port=args.port)
        return

    parser.error(f"Unsupported command: {args.command}")


if __name__ == "__main__":
    main()
