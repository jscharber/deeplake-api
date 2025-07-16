#!/bin/bash

# Generate Python gRPC code from protocol buffer definitions

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
PROTO_DIR="$PROJECT_ROOT/proto"
OUTPUT_DIR="$PROJECT_ROOT/app/models/proto"

echo "Generating Python gRPC code..."
echo "Proto dir: $PROTO_DIR"
echo "Output dir: $OUTPUT_DIR"

# Create output directory if it doesn't exist
mkdir -p "$OUTPUT_DIR"

# Generate Python protobuf and gRPC code
python3 -m grpc_tools.protoc \
    --proto_path="$PROTO_DIR" \
    --python_out="$OUTPUT_DIR" \
    --grpc_python_out="$OUTPUT_DIR" \
    "$PROTO_DIR/deeplake_service.proto"

# Fix import paths in generated files
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    sed -i '' 's/import deeplake_service_pb2/from . import deeplake_service_pb2/' "$OUTPUT_DIR/deeplake_service_pb2_grpc.py"
else
    # Linux
    sed -i 's/import deeplake_service_pb2/from . import deeplake_service_pb2/' "$OUTPUT_DIR/deeplake_service_pb2_grpc.py"
fi

echo "Generated files:"
ls -la "$OUTPUT_DIR"/*.py

echo "gRPC code generation complete!"