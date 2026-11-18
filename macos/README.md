# macOS remote service

The installer runs Cactus Needle as a per-user LaunchAgent. It creates an
isolated Python environment, installs the supported `cactus-compute` version,
downloads or copies the server, and generates paths for the current user.

From a cloned repository:

```bash
./macos/cactus-needle.sh install
```

Without cloning:

```bash
curl -fsSLO https://raw.githubusercontent.com/pjaol/ha-cactus-needle/main/macos/cactus-needle.sh
chmod +x cactus-needle.sh
./cactus-needle.sh install
```

Then add the Home Assistant integration using the Mac's LAN address, for
example `http://mac-mini.local:18080`.

Useful commands:

```bash
./macos/cactus-needle.sh status
./macos/cactus-needle.sh update
./macos/cactus-needle.sh restart
./macos/cactus-needle.sh uninstall
./macos/cactus-needle.sh uninstall --purge
```

The default installation directory is
`~/Library/Application Support/Cactus Needle`. Override it with
`CACTUS_NEEDLE_HOME`; the port and versions can similarly be selected with
`CACTUS_NEEDLE_PORT`, `CACTUS_NEEDLE_RELEASE`, and `CACTUS_VERSION`. Slow
first-time downloads can use `CACTUS_NEEDLE_STARTUP_TIMEOUT` to change the
default ten-minute health-check window.

Uninstalling preserves the downloaded model cache unless `--purge` is passed.
