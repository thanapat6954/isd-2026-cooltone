"""Check test-only imports before starting a backend or running expensive suites."""
import sys


def main():
    try:
        from fastapi.testclient import TestClient  # noqa: F401
    except (ImportError, RuntimeError) as error:
        print(f'Evaluation dependency missing or incompatible: {error}')
        print('Install with: .\\venv\\Scripts\\python.exe -m pip install -r requirements-evaluation-tested.txt')
        return 1
    print('Evaluation TestClient dependency ready')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
