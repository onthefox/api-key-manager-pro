import os
import sys

# Ensure the project root is importable regardless of where pytest is invoked.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Never collect the vendored duplicate subtree (see repo review notes).
collect_ignore = ["unified-proxy-collector"]


def _broken_pytest_plugins():
    """Return [(entry_point_name, distribution)] for pytest11 plugins that
    raise on import.

    Some environments ship third-party pytest plugins (e.g. old ``libtmux``
    releases) that apply marks to fixture functions at import time, which
    aborts collection outright with newer pytest versions ("Marks cannot be
    applied to fixtures"). We probe every registered plugin entry point up
    front so we can react before pytest loads them.
    """
    from importlib import import_module
    from importlib.metadata import distributions

    broken = []
    for dist in distributions():
        try:
            eps = dist.entry_points
        except Exception:  # pragma: no cover - malformed metadata
            continue
        for ep in eps:
            if getattr(ep, "group", None) != "pytest11":
                continue
            try:
                import_module(ep.value.split(":")[0])
            except BaseException:
                broken.append((ep.name, dist.metadata.get("Name", "?")))
    return broken


_broken = _broken_pytest_plugins()
if _broken and os.environ.get("_APIKEY_TESTS_REEXEC") != "1":
    names = ", ".join(f"{n} ({d})" for n, d in _broken)
    print(
        f"[conftest] Broken pytest plugin(s) detected: {names}. Re-running "
        "this exact command with plugin autoload disabled so only the "
        "plugins this project needs run explicitly (keeps the suite "
        "deterministic and hermetic).",
        file=sys.stderr,
    )
    env = dict(
        os.environ,
        _APIKEY_TESTS_REEXEC="1",
        PYTEST_DISABLE_PLUGIN_AUTOLOAD="1",
    )
    os.execve(
        sys.executable,
        [sys.executable, "-m", "pytest", *sys.argv[1:]],
        env,
    )
elif _broken:
    print(
        "[conftest] WARNING: broken pytest plugin(s) still present after "
        "re-exec; tests may fail to collect.",
        file=sys.stderr,
    )
