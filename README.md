# todomate-mcp

TodoMate의 Firestore Todo를 조회·생성·수정·완료·삭제하는 Python MCP 서버입니다.

## 개발 환경

- Python 3.12 이상, uv
- Official MCP Python SDK (`mcp`), httpx, pydantic
- 개발 의존성: pytest

## 설치

```sh
uv sync
```

소스 코드는 `src/todomate_mcp/`, 테스트는 `tests/`에 작성합니다.
`.env.example`을 복사해 로컬 `.env`를 만들고 인증값을 설정합니다. `.env`는 Git에서 제외됩니다.

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

`list_todos`, `get_todo`, `create_todo`, `update_todo`, `complete_todo`, `delete_todo`를 지원합니다. 날짜를 생략하면 `Asia/Seoul`의 오늘을 사용합니다.

처음에는 `TODOMATE_FIREBASE_API_KEY`, `TODOMATE_EMAIL`, `TODOMATE_PASSWORD`를 설정합니다. 성공한 요청 뒤에는 refresh token이 로컬 `.env`에 저장되어 다음 실행부터 비밀번호 없이 세션을 복원합니다. 실행 환경 변수는 `.env` 값을 우선합니다. 인증값을 저장소에 넣지 마세요.
