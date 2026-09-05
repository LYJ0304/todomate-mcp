# todomate-mcp

Todomate MCP 서버 개발을 위한 Python 프로젝트입니다. Firebase 로그인과 메모리 내 토큰 갱신을 구현했으며, MCP 서버와 Todo 기능은 아직 구현하지 않았습니다.

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

Firebase 인증 테스트는 HTTP 응답을 mock으로 제공하므로 실제 계정이나 외부 API 접속이 필요하지 않습니다.

## MCP server

로컬 stdio 서버는 다음 명령으로 실행합니다.

```sh
uv run todomate-mcp
```

`list_todos(day?)`와 `get_todo(todo_id)`를 지원합니다. `day`를 생략하면 `Asia/Seoul`의 오늘을 사용합니다.

실제 TodoMate 계정에 연결하려면 실행 환경에 `TODOMATE_FIREBASE_API_KEY`, `TODOMATE_EMAIL`, `TODOMATE_PASSWORD`를 설정합니다. 인증값을 저장소에 넣지 마세요.
