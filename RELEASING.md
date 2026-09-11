# Build a macOS release

You need arm64 macOS and Python 3.14.3 for this build.
Run these commands from the repository root:

```bash
python3 -m venv .git/release-venv
.git/release-venv/bin/python -m pip install -r requirements-build.txt
bash scripts/build-macos.sh
```

You get `.git/release/ledger-macos-arm64`.
The binary bundles Python and SQLite. You do not need a separate Python installation to run it.
You use the same commands and environment variables as the `ledger` script.

Verify the architecture, signature, and command parser:

```bash
file .git/release/ledger-macos-arm64
codesign --verify .git/release/ledger-macos-arm64
.git/release/ledger-macos-arm64 --help
```

The build uses an ad hoc signature. You do not get an Apple notarization ticket.
See the [PyInstaller build options](https://www.pyinstaller.org/en/stable/usage.html) for platform restrictions.
