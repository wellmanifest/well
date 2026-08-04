from __future__ import annotations

import os
import time

import grpc
from google.protobuf import empty_pb2

from wellmanifest.generated import wellmanifest_pb2, wellmanifest_pb2_grpc

address = os.getenv("WELLMANIFEST_GRPC_TARGET", "grpc:50051")
channel = grpc.insecure_channel(address)
for _ in range(30):
    try:
        grpc.channel_ready_future(channel).result(timeout=1)
        break
    except grpc.FutureTimeoutError:
        time.sleep(1)
else:
    raise SystemExit("gRPC e2e timeout")

stub = wellmanifest_pb2_grpc.RuntimeServiceStub(channel)
capabilities = stub.GetCapabilities(empty_pb2.Empty(), timeout=5)
assert capabilities.capabilities.fields["protocol"].string_value == "wellmanifest.protocol/v1"

response = stub.Convert(
    wellmanifest_pb2.ConvertRequest(
        source_text="status:\n  value: SUCCEEDED\n",
        source_dialect="yaml",
        target_dialect="json",
        projection="data",
        pretty=True,
    ),
    timeout=5,
)
assert "SUCCEEDED" in response.output
print("grpc e2e: PASS")
