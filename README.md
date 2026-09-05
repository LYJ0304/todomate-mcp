# todomate-mcp

Todomate MCP 서버 개발을 위한 최소 Python 프로젝트입니다. 아직 기능은 구현하지 않았습니다.

## 개발 환경

- Python 3.12 이상, uv
- Official MCP Python SDK (`mcp`), httpx, pydantic
- 개발 의존성: pytest

## 설치

```sh
uv sync
```

소스 코드는 `src/todomate_mcp/`, 테스트는 `tests/`에 작성합니다.
환경 변수가 필요해지면 `.env.example`을 참고해 `.env`를 만듭니다.
현재는 환경 변수가 필요하지 않으며, `.env` 자동 로딩도 구성하지 않았습니다.

## 테스트

```sh
uv run pytest
```

현재 테스트가 없어 pytest는 종료 코드 5를 반환합니다.
