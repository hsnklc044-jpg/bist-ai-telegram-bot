from pathlib import Path
import importlib.util
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
GATE = Path(__file__).with_name("price_fix_gate.py")
RESEARCH = ROOT / "core/backtest/research.py"

def load_gate():
    spec = importlib.util.spec_from_file_location("quantbist_price_gate", GATE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def check_args(args):
    fixes = None
    for i, arg in enumerate(args):
        if arg == "--price-fixes":
            if i + 1 >= len(args):
                raise ValueError("--price-fixes icin dosya yolu gerekli.")
            fixes = args[i + 1]
        elif arg.startswith("--price-fixes="):
            fixes = arg.split("=", 1)[1]

    if fixes is None:
        return "DUZELTMESIZ_ARASTIRMA"

    if not fixes.strip():
        raise ValueError("Bos fiyat duzeltme yolu reddedildi.")

    gate = load_gate()
    gate.validate_price_fixes(Path(fixes))
    return "ONAYLI_DUZELTME"

def main():
    args = sys.argv[1:]
    try:
        result = check_args(args)
    except Exception as exc:
        print("GUVENLIK KAPISI: ENGELLENDI")
        print(type(exc).__name__ + ":", exc)
        return 2

    print("GUVENLIK KAPISI:", result, flush=True)
    return subprocess.call([sys.executable, str(RESEARCH), *args], cwd=ROOT)

if __name__ == "__main__":
    raise SystemExit(main())
