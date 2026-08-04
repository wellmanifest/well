# syntax=docker/dockerfile:1.7
FROM node:22.16.0-bookworm-slim
WORKDIR /workspace
COPY packages/js ./packages/js
COPY scripts/e2e-node.mjs ./scripts/e2e-node.mjs
CMD ["node", "scripts/e2e-node.mjs"]
