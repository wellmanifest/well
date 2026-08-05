from __future__ import annotations

import os
from concurrent import futures
from typing import Any, Iterable

from google.protobuf import json_format, struct_pb2

from .models import ConversionRequest, Envelope, ExecuteRequest, ValidationRequest
from .runtime import WellManifestRuntime


def _dict_from_struct(value: Any) -> dict[str, Any]:
    return json_format.MessageToDict(value, preserving_proto_field_name=True) if value is not None else {}


def _value_to_python(value: Any) -> Any:
    return json_format.MessageToDict(value, preserving_proto_field_name=True) if value is not None else None


def _parse_dict(data: dict[str, Any], message: Any) -> Any:
    return json_format.ParseDict(data, message, ignore_unknown_fields=False)


def main() -> None:
    try:
        import grpc
        from wellmanifest.generated import wellmanifest_pb2, wellmanifest_pb2_grpc
    except ImportError as exc:
        raise SystemExit(
            "Generate protobuf stubs with scripts/generate_proto.sh and install `wellmanifest[grpc]`."
        ) from exc

    runtime = WellManifestRuntime()

    class RuntimeService(wellmanifest_pb2_grpc.RuntimeServiceServicer):
        def Convert(self, request: Any, _context: Any) -> Any:
            result = runtime.convert(
                ConversionRequest(
                    source=request.source_text,
                    source_dialect=request.source_dialect or "auto",
                    target_dialect=request.target_dialect or "json",
                    projection=request.projection or "data",
                    schema=_dict_from_struct(request.schema) or None,
                    source_name=request.source_name or None,
                    pretty=request.pretty,
                    type_mode=getattr(request, "type_mode", "preserve") or "preserve",
                )
            )
            return _parse_dict(result.model_dump(mode="json"), wellmanifest_pb2.ConvertResponse())

        def Validate(self, request: Any, _context: Any) -> Any:
            result = runtime.validate(
                ValidationRequest(
                    source=request.source_text,
                    dialect=request.dialect or "auto",
                    schema=_dict_from_struct(request.schema),
                    source_name=request.source_name or None,
                )
            )
            return _parse_dict(result.model_dump(mode="json"), wellmanifest_pb2.ValidateResponse())

        def Execute(self, request: Any, _context: Any) -> Any:
            data = json_format.MessageToDict(request, preserving_proto_field_name=True)
            result = runtime.execute_uri(ExecuteRequest.model_validate(data))
            return _parse_dict(result.model_dump(mode="json"), wellmanifest_pb2.ExecuteResponse())

        def Exchange(self, request_iterator: Iterable[Any], _context: Any) -> Iterable[Any]:
            for request in request_iterator:
                data = json_format.MessageToDict(request, preserving_proto_field_name=True)
                response = runtime.exchange(Envelope.model_validate(data))
                yield _parse_dict(response.model_dump(mode="json"), wellmanifest_pb2.Envelope())

        def GetCapabilities(self, _request: Any, _context: Any) -> Any:
            message = wellmanifest_pb2.CapabilitiesResponse()
            _parse_dict(runtime.capabilities(), message.capabilities)
            return message

    server = grpc.server(futures.ThreadPoolExecutor(max_workers=int(os.getenv("WELLMANIFEST_GRPC_WORKERS", "8"))))
    wellmanifest_pb2_grpc.add_RuntimeServiceServicer_to_server(RuntimeService(), server)
    address = os.getenv("WELLMANIFEST_GRPC_ADDRESS", "0.0.0.0:50051")
    server.add_insecure_port(address)
    server.start()
    print(f"WellManifest gRPC server listening on {address}")
    server.wait_for_termination()


if __name__ == "__main__":
    main()
