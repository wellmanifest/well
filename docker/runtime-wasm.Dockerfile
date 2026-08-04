# syntax=docker/dockerfile:1.7
FROM rust:1.82.0-bookworm AS builder
RUN rustup target add wasm32-unknown-unknown \
 && cargo install wasm-bindgen-cli --version 0.2.100 --locked
WORKDIR /src
COPY Cargo.toml rust-toolchain.toml ./
COPY crates ./crates
RUN cargo build --release -p wellmanifest-wasm --target wasm32-unknown-unknown \
 && mkdir -p /out \
 && wasm-bindgen \
      --target web \
      --out-dir /out \
      target/wasm32-unknown-unknown/release/wellmanifest_wasm.wasm

FROM scratch AS artifact
COPY --from=builder /out /wellmanifest-wasm
