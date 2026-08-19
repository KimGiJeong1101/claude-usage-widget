"""PyInstaller entry point (lives outside the usage_widget package so the
package stays importable when frozen)."""

from usage_widget.main import run

if __name__ == "__main__":
    run()
