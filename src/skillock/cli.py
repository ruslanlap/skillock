import argparse
import sys

from skillock import __version__


def main(argv=None):
    p = argparse.ArgumentParser(prog="skillock")
    p.add_argument("--version", action="version", version=f"skillock {__version__}")
    p.parse_args(argv)
    return 0


if __name__ == "__main__":
    sys.exit(main())
