"""Executa os testes e salva a saída do compilador em logs."""
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
TEST_DIR = ROOT / "testes"
LOG_DIR = ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)

tests = sorted(TEST_DIR.glob("*.pas"))
if not tests:
    print("Nenhum teste .pas encontrado em testes/.")
    sys.exit(2)

for test in tests:
    result = subprocess.run(
        [sys.executable, str(ROOT / "yacc.py"), str(test)],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    log = LOG_DIR / f"{test.stem}.log"
    log.write_text(f"Código de saída: {result.returncode}\n\n{result.stdout}", encoding="utf-8")
    print(f"{test.name}: código {result.returncode} -> logs/{log.name}")