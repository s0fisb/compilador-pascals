"""Executa os testes e salva saídas reais em logs/*.log."""
from pathlib import Path
import subprocess, sys
ROOT = Path(__file__).resolve().parent
overall = 0
for test in sorted((ROOT / "testes").glob("*.pas")):
    result = subprocess.run([sys.executable, str(ROOT / "yacc.py"), str(test)],
        cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    log = ROOT / "logs" / f"{test.stem}.log"
    log.write_text(f"Código de saída: {result.returncode}\n\n{result.stdout}", encoding="utf-8")
    print(f"{test.name}: código {result.returncode} -> logs/{log.name}")
    if result.returncode not in (0, 1): overall = result.returncode

sys.exit(overall)
