"""Backwards-compatibility shim. The implementation now lives in the `mediageoplot` package.

Run `python -m mediageoplot --media_path ... --output ...` going forward.
"""

from mediageoplot.cli import main

if __name__ == "__main__":
    main()
