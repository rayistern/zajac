FROM node:24-alpine AS build

ARG PNPM_VERSION=10.32.1
RUN npm install -g pnpm@${PNPM_VERSION}

WORKDIR /workspace

COPY pnpm-lock.yaml pnpm-workspace.yaml package.json ./
COPY api/package.json ./api/package.json
COPY frontend/package.json ./frontend/package.json
COPY infra/package.json ./infra/package.json
RUN pnpm install --frozen-lockfile

COPY api ./api
RUN pnpm --filter ./api build
RUN pnpm --filter ./api deploy --legacy --prod /out

FROM node:24-alpine AS runtime

WORKDIR /app

ENV NODE_OPTIONS="--enable-source-maps"

COPY --from=build /out ./

EXPOSE 3000

CMD ["node", "dist/index.js"]
