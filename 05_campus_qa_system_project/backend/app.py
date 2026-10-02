from __future__ import annotations

from fcqa.config import load_config
from fcqa.server import run_server


def main() -> None:
    run_server(load_config())


if __name__ == "__main__":
    main()
