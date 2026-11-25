import importlib, sys, traceback, os
from pathlib import Path


BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[0]
sys.path.insert(0, str(ROOT))

def run_module(modname: str) -> bool:
    try:
        mod = importlib.import_module(modname)

        # ejecuta funciones test_* (estilo pytest) si existen
        test_fns = [
            name for name in dir(mod)
            if name.startswith("test_") and callable(getattr(mod, name))
        ]

        if not test_fns:
            print(f"[WARN] {modname}: no hay funciones test_* para ejecutar")
            return True

        ok = True
        for name in sorted(test_fns):
            fn = getattr(mod, name)
            try:
                fn()
            except Exception as e:
                ok = False
                print(f"[FAIL] {modname}.{name}: {e}")
                traceback.print_exc()

        if ok:
            print(f"[OK] {modname} ({len(test_fns)} tests)")
        return ok

    except Exception as e:
        print(f"[FAIL] {modname}: {e}")
        traceback.print_exc()
        return False

def main():
    os.chdir(ROOT)  # importante: Path("data") sea relativo al repositorio
    passed = True
    for f in sorted(BASE.glob("test_*.py")):
        modname = f"tests.{f.stem}"
        passed = run_module(modname) and passed
    if not passed:
        sys.exit(1)
    print("ALL TESTS PASSED")

if __name__ == "__main__":
    main()
