# syntax=docker/dockerfile:1.7
FROM rust:1.82.0-bookworm AS builder
WORKDIR /src
COPY Cargo.toml rust-toolchain.toml ./
COPY crates ./crates
RUN cargo test -p wellmanifest-core -p wellmanifest-cli \
 && cargo build --release -p wellmanifest-cli

FROM debian:bookworm-slim
RUN useradd --system --uid 10001 --create-home wellmanifest
COPY --from=builder /src/target/release/wellmanifest-native /usr/local/bin/wellmanifest
USER 10001:10001
ENTRYPOINT ["/usr/local/bin/wellmanifest"]
CMD ["--help"]
