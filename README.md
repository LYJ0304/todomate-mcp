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

Streamable HTTP 서버는 `/mcp`에서 실행합니다. 개인 Todo에 접근하므로 HTTP 실행에는 별도의 Bearer 토큰이 필요합니다.

```sh
# 로컬 개발
TODOMATE_MCP_ACCESS_TOKEN="$(openssl rand -hex 32)" uv run todomate-mcp http --host 127.0.0.1 --port 8000

# MCP client: http://127.0.0.1:8000/mcp
# Authorization: Bearer <TODOMATE_MCP_ACCESS_TOKEN>
```

`TODOMATE_MCP_HOST`, `TODOMATE_MCP_PORT`으로 기본 host와 port를 정할 수 있습니다. 공개 배포에서는 TLS를 종료하는 reverse proxy 뒤에서 실행하고, 외부 HTTPS 주소를 `TODOMATE_MCP_PUBLIC_URL`(예: `https://todos.example.com/mcp`)에 설정하세요. 현재 인증은 단일 개인용 Bearer 토큰 방식이며, 토큰 없이 `/mcp`에 요청하면 `401`을 반환합니다.

`list_todos`, `get_todo`, `create_todo`, `update_todo`, `complete_todo`, `delete_todo`를 지원합니다. 날짜를 생략하면 `Asia/Seoul`의 오늘을 사용합니다.

처음에는 `TODOMATE_FIREBASE_API_KEY`, `TODOMATE_EMAIL`, `TODOMATE_PASSWORD`를 설정합니다. 성공한 요청 뒤에는 refresh token이 로컬 `.env`에 저장되어 다음 실행부터 비밀번호 없이 세션을 복원합니다. 실행 환경 변수는 `.env` 값을 우선합니다. 인증값을 저장소에 넣지 마세요.
