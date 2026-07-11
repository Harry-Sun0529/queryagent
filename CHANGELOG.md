# Changelog

All notable changes to this project will be documented in this file.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versioning: [SemVer](https://semver.org/). CLI arguments and config structure
enter the semver contract at v0.2.0; `metrics.yaml` required fields are
frozen from v0.1.1 (spec §四).

## [Unreleased]

### Added

- v0.1.0 core: event-stream architecture (`AgentEvent` family incl. reserved
  `ClarifyEvent`), `LLMBackend` / `Connector` / `MetricStore` protocols,
  Anthropic backend, MySQL connector, tool registry, context builder,
  config loader, fictional `demo_shop` dataset (dialect-agnostic generator),
  ReAct loop & SQL safety whitelist (human-written).
- v0.1.1 (in progress): YAML metric store with alias/keyword matching,
  SQLite connector (Docker-free demo path), OpenAI-compatible backend
  (DeepSeek/Qwen/GLM/vLLM/Ollama via `base_url`), `queryagent chat` CLI.
- v0.2.0 (in progress): eval toolkit — result-set comparison (order-
  insensitive, float tolerance), five-metric runner over the event stream,
  `queryagent eval` with `--backend/--model` dual-model support, public
  benchmark subset sampling (fixed seed).
