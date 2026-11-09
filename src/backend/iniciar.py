"""Inicia os cinco processos; Ctrl+C encerra todos eles."""

import subprocess
import sys
import time


def iniciar_servicos():
    """Usa o mesmo Python do ambiente virtual para executar cada serviço."""
    processos = []
    try:
        for servico in ("quartos", "pessoas", "senhas", "acessos", "gateway"):
            processos.append(subprocess.Popen(
                [sys.executable, "-m", f"backend.{servico}"]
            ))
        print("Swagger UI: http://localhost:5000/docs/ — Ctrl+C para encerrar.", flush=True)
        while True:
            if any(processo.poll() is not None for processo in processos):
                raise SystemExit("Um serviço encerrou. Verifique as mensagens acima.")
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass
    finally:
        for processo in processos:
            if processo.poll() is None:
                processo.terminate()
        for processo in processos:
            try:
                processo.wait(timeout=5)
            except subprocess.TimeoutExpired:
                processo.kill()
                processo.wait()


if __name__ == "__main__":
    iniciar_servicos()
