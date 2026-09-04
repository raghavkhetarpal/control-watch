# Testing Strategy

## Testing Philosophy
The testing strategy ensures the integrity of the data ingestion, accuracy of the deterministic controls, correctness of risk calculations, and the safety/guardrails of the AI Copilot. Tests use isolated, deterministic mock data and **never use fabricated SEC data**.

## Test Categories

### Unit Testing
- **Scope**: Individual functions, parsers, and calculators.
- **Examples**: Testing the TSV parser with a string input; testing the inherent risk calculation formula.
- **Tooling**: `pytest`

### Integration Testing
- **Scope**: Interactions between components (e.g., Ingestion to Database).
- **Examples**: Verifying parsed data is correctly inserted into the SQLite/PostgreSQL test database and schema constraints are enforced.
- **Tooling**: `pytest` with test database fixtures.

### Control Testing
- **Scope**: Business logic of the 16 controls.
- **Examples**: Injecting a mock holding with negative quantity and verifying DQ-003 correctly flags it; injecting a clean holding and verifying it passes.
- **Tooling**: parameterized `pytest` tests.

### API Testing
- **Scope**: FastAPI endpoints.
- **Examples**: Hitting `/api/metrics` and verifying response schema and status codes.
- **Tooling**: `httpx` or `FastAPI.testclient`.

### AI Validation Testing
- **Scope**: AI Copilot prompt generation and output safety.
- **Examples**: Verifying the prompt includes the disclaimer; checking that the AI gracefully handles out-of-bounds inputs without hallucinations.
- **Tooling**: Mocked LLM responses in `pytest`.

### Edge Case Testing
- **Scope**: Boundary conditions and malformed inputs.
- **Examples**: Empty files, files with missing columns, extreme numerical values, unicode characters in identifiers.

## Coverage Targets
- **Business Logic (Controls, Risk Math)**: >85%
- **API Routes**: >80%
- **Overall Project**: >75%

## Running Tests
Run tests using pytest from the project root:
```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=src --cov-report=term-missing

# Run specific test category
pytest tests/unit/
```

## CI Integration
Testing is integrated via GitHub Actions. Upon every Pull Request or push to `main`:
1. Linter (`flake8` / `black`) runs.
2. Type checking (`mypy`) runs.
3. Unit and Integration tests run via `pytest`.
4. Coverage report is generated; fails if coverage drops below targets.

## Test Data
Test fixtures use minimal, hand-crafted datasets designed purely to trigger specific code paths. To comply with guidelines, we do not fabricate complete SEC N-PORT filings or attempt to spoof real-world financial data.
