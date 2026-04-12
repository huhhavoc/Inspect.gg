# Contributing to Inspect.gg

Thank you for your interest in improving Inspect.gg! This guide will help you get started with development.

## 🛠️ Development Setup

1. **Clone the repository**:
   ```powershell
   git clone https://github.com/yourusername/inspect.gg.git
   cd inspect.gg
   ```
2. **Setup the Environment**:
   Run the terminal as **Administrator** (required for WMI/Telemetry access).
   ```powershell
   python -m venv venv
   .\venv\Scripts\activate
   pip install -r requirements.txt
   ```
3. **Run the Server**:
   ```powershell
   cd src
   python app.py
   ```

## 📜 Code Style & Principles

- **Plain Python Standard Lib**: We prefer standard library solutions where possible to keep the installer light.
- **Graceful Failures**: Hardware checks inside `system_info.py` must handle `None` or `Exception` returns gracefully without crashing the SSE stream.
- **SSE Architecture**: All new long-running tasks should be implemented as generators in `app.py` and steamed via `/api/run_all_sse`.

## 📍 Where to Change Things

- **New Hardware Checks**: Add logic to `src/utils/system_info.py`.
- **New Benchmarks**: Add logic to `src/utils/benchmarks.py`.
- **Pricing Logic**: 
  - To adjust base prices or deductions, edit `src/pricing.json`.
  - To change how math is computed, edit `src/utils/pricing.py`.

## 🚀 Submitting a Pull Request

1. Fork the repository.
2. Create a new feature branch (`git checkout -b feature/amazing-new-check`).
3. Commit your changes with clear descriptions.
4. Push to the branch (`git push origin feature/amazing-new-check`).
5. Open a Pull Request on GitHub describing what changed and **why**.

## ⚖️ License

By contributing, you agree that your contributions will be licensed under the project's MIT License.
