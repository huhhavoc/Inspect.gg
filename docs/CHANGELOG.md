# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-04-13

### Added
- **SSE-based Hardware Scanning**: Real-time telemetry streaming from backend to UI.
- **Isolated Benchmarking**: Custom stress tests for CPU (raw ops), GPU (VRAM throughput), RAM bandwidth, and Disk I/O.
- **WMI Battery Detection**: Detailed wear level (%) and health status extraction.
- **Fair Price Calculator**: Internal math engine driven by a user-editable `pricing.json` configuration file.
- **AI Valuation Prompt Generator**: Automatically builds high-fidelity hardware profiles for ChatGPT/Gemini appraisals.
- **Claymorphism UI**: Beautiful, modern design system using glassmorphism and soft-clay aesthetics.
- **Auto-Configuring Launcher**: `launcher.bat` handles Python setup, virtual environments, and dependency resolution.
- **Reporting & Export**: Clean PDF/HTML export functionality.
- **Session Isolation**: Automated result caching and session-based report saving.

[1.0.0]: https://github.com/huhhavoc/Inspect.gg/releases/tag/v1.0.0
