from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .models import ConversionRequest, ExecuteRequest, RuntimeTarget, ValidationRequest
from .runtime import WellManifestRuntime


def _read(path: str) -> str:
    if path == "-":
        return sys.stdin.read()
    return Path(path).read_text(encoding="utf-8")


def _load_json(path: str) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _print_diagnostics(items: list[Any]) -> None:
    for item in items:
        diagnostic = item.model_dump(mode="json") if hasattr(item, "model_dump") else item
        print(f"{diagnostic['severity']} {diagnostic['code']}: {diagnostic['message']}", file=sys.stderr)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="wellmanifest", description="WellManifest protocol and dialect runtime")
    parser.add_argument("--version", action="version", version="wellmanifest 0.1.0")
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
        if args.output == "-":
            print(output, end="" if output.endswith("\n") else "\n")
        else:
            Path(args.output).write_text(output, encoding="utf-8")
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
