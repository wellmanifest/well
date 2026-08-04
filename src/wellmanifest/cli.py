from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

import yaml

from .models import ConversionRequest, Document, DocumentMetadata, ExecuteRequest, RuntimeTarget, ValidationRequest
from .runtime import WellManifestRuntime


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
        print(f"{diagnostic['severity']} {diagnostic['code']}: {diagnostic['message']}", file=sys.stderr)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="wellm", description="WellManifest protocol and dialect runtime")
    parser.add_argument("--version", action="version", version="wellm 0.2.0rc2")
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

    validate_parser = subparsers.add_parser("validate", help="Validate against JSON Schema 2020-12")
    validate_parser.add_argument("file")
    validate_parser.add_argument("--dialect", default="auto")
    validate_parser.add_argument("--schema", required=True)

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
    plesk_plan.add_argument("--to", choices=["json", "yaml", "typed", "hcl", "typescript"], default="json")
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

    serve_parser = subparsers.add_parser("serve", help="Run HTTP/WebSocket runtime gateway")
    serve_parser.add_argument("--host", default="0.0.0.0")
    serve_parser.add_argument("--port", type=int, default=8080)

    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    runtime = WellManifestRuntime()

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
            diagnostics.extend(runtime.schema_validator.validate(document.data, _load_json(args.schema), source=args.file))
        target = runtime.registry.get(args.target_dialect)
        try:
            output = target.emit(document, projection=projection, pretty=not args.compact)
        except (ValueError, TypeError, KeyError) as exc:
            print(f"ERROR WM-RUN-001: {exc}", file=sys.stderr)
            raise SystemExit(2) from exc
        _print_diagnostics(diagnostics)
        print(output, end="" if output.endswith("\n") else "\n")
        raise SystemExit(1 if any(item.severity.value == "ERROR" for item in diagnostics) else 0)

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
            )
        )
        _print_diagnostics(result.diagnostics)
        if result.output is None:
            raise SystemExit(2)
        output = result.output if isinstance(result.output, str) else json.dumps(result.output, ensure_ascii=False, indent=2)
        _write_output(output, args.output)
        raise SystemExit(1 if any(item.severity.value == "ERROR" for item in result.diagnostics) else 0)

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
            raise SystemExit(1 if any(item.severity.value == "ERROR" for item in plan.diagnostics) else 0)

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
        _write_output(json.dumps(receipt.model_dump(mode="json", by_alias=True), ensure_ascii=False, indent=2) + "\n", args.output)
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

    if args.command == "serve":
        import uvicorn

        uvicorn.run("wellmanifest.server:app", host=args.host, port=args.port)
        return

    parser.error(f"Unsupported command: {args.command}")


if __name__ == "__main__":
    main()
