# JorkaPrinter

**JorkaPrinter** is a maintenance bot for inkjet printers on Linux (CUPS). 

Inkjet printers have a fatal flaw: if left idle for too long, the print heads dry out and clog, leading to streaky prints and expensive cartridge replacements. Script solves this by automating a minimal maintenance cycle. It monitors your printing habits and only activates when necessary. The maintenance print consists of four small blocks (Cyan, Magenta, Yellow, Black) and a timestamp, consuming approximately 0.46% of an A4 page. This ensures all nozzles remain clear and functional with negligible ink cost. Random positioning allows you to reuse the same sheet of paper for months.

If the printer hasn't been used for a set period (default: 7 days), it automatically prints this minimal CMYK test pattern. The script checks CUPS logs (`/var/log/cups/page_log`) to avoid unnecessary prints if you've already used the printer recently.

## Requirements

*   CUPS
*   Python 3
*   ImageMagick

## Installation

1.  Clone the repository:
    ```bash
    git clone https://github.com/komparator147477/jorkaprinter.git
    cd jorkaprinter
    ```

2.  Run the installer:
    ```bash
    ./install.sh
    ```
    *   The installer will detect your default printer and set up a daily systemd timer.

3.  (Optional) Test immediately:
    ```bash
    ~/.local/bin/jorka-maintenance --force
    ```

## Manual Usage

The script is installed to `~/.local/bin/jorka-maintenance`.

| Flag | Description |
|------|-------------|
| `-h`, `--help` | Show help and exit |
| `--force` | Print a test page immediately, ignoring history |
| `--check`, `--status` | Show last-print time and whether maintenance is due (no printing) |
| `--printer NAME` | CUPS printer name (auto-detects default if omitted) |
| `--days N` | Days of inactivity before maintenance triggers (default: 7) |

## Uninstallation

To remove the service and timer:

```bash
systemctl --user disable --now jorka-maintenance.timer
rm ~/.config/systemd/user/jorka-maintenance.*
rm ~/.local/bin/jorka-maintenance
systemctl --user daemon-reload
```
