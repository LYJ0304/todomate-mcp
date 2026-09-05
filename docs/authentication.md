# TodoMate 인증 방식 분석

이슈 [#1](https://github.com/LYJ0304/todomate-mcp/issues/1)의 분석 결과다. 후속 이슈 [#2](https://github.com/LYJ0304/todomate-mcp/issues/2)에서 Python `FirebaseAuthSession`을 구현할 때 참고한다.

- 조사일: 2026-09-05
- 참고 저장소: `3x-haust/todomate-api`
- 분석 기준 커밋: [`987b3fe7bf8e580794e4d7b27ac5ced05426b068`](https://github.com/3x-haust/todomate-api/tree/987b3fe7bf8e580794e4d7b27ac5ced05426b068)
- **기존 구현**은 해당 커밋에서 확인한 동작, **공식 규약**은 Firebase 문서에 명시된 내용, **설계 제안**은 이 프로젝트에서 채택할 방향을 뜻한다.

실제 계정 로그인이나 API 호출로 검증하지 않았다. 아래 요청 예시의 값은 모두 자리표시자다.

## Authentication flow

**기존 구현:** `TodomateClient`는 `FirebaseAuthSession`을 생성하고 이를 `FirestoreRestClient`에 전달한다. 생성 시점에는 인증 요청을 보내지 않으며, `idToken()`, `userId()`, `snapshot()` 호출에서 세션이 필요할 때 인증한다. 이메일·비밀번호와 refresh token 중 하나로 시작할 수 있다. [클라이언트 구성][client] · [인증 세션][auth]

```text
이메일·비밀번호 + Firebase API key
  → Firebase Auth 로그인
  → ID token, refresh token, UID, 만료 시각 보관
  → 유효한 ID token 요청 (필요하면 refresh token으로 갱신)
  → Authorization: Bearer <ID_TOKEN>으로 Firestore 접근
```

**공식 규약:** Firestore REST API는 Firebase ID token을 `Authorization: Bearer <ID_TOKEN>` 헤더로 받으며, 해당 사용자 요청의 권한은 Firestore Security Rules로 판단한다. 로그인 성공만으로 모든 데이터 접근이 허용되는 것은 아니다. [Firestore REST 인증][firestore-auth]

**기존 구현:** Firestore 요청마다 인증 세션에서 ID token을 가져와 이 헤더를 구성한다. 참고 서버의 `/auth/login`이 발급하는 자체 세션 토큰은 Firebase ID token과 다르다. 자체 세션에는 refresh token, UID, 발급·만료 시각을 넣어 인코딩하며, Firestore에는 Firebase ID token을 전달한다. [Firestore 호출부][firestore] · [로그인 라우트][routes]

## Sign-in request

**공식 규약:** [이메일·비밀번호 로그인][sign-in]

```http
POST https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key=<FIREBASE_API_KEY>
Content-Type: application/json

{"email":"<EMAIL>","password":"<PASSWORD>","returnSecureToken":true}
```

| 값 | 타입 | 의미 |
| --- | --- | --- |
| `key` (query) | string | Firebase 프로젝트의 Web API key |
| `email` | string | 로그인 이메일 |
| `password` | string | 계정 비밀번호 |
| `returnSecureToken` | boolean | ID token과 refresh token 반환 요청. `true` 사용 |

**기존 구현:** 위 endpoint와 JSON 필드를 사용한다. HTTP 성공 여부를 검사하고 실패하면 `AUTH_FAILED`를 반환한다. [인증 세션][auth]

## Sign-in response

**공식 규약:** 성공 시 HTTP 200과 JSON 응답을 반환한다. 아래는 세션에 필요한 필드다. [로그인 응답][sign-in]

| 필드 | 타입 | 의미 / 내부 상태 |
| --- | --- | --- |
| `idToken` | string | 사용자 요청 인증에 사용할 ID token |
| `refreshToken` | string | ID token 재발급에 사용할 refresh token |
| `localId` | string | 사용자 UID |
| `expiresIn` | string | ID token이 만료되기까지의 초 수 |

**기존 구현:** 네 필드를 문자열로 검증하고 `localId`를 `uid`로 매핑한다. 만료 시각은 `현재 시각(ms) + Number(expiresIn) × 1000`으로 계산한다. 스키마 불일치는 `AUTH_RESPONSE_INVALID`로 처리한다. 숫자 문자열인지, 양수인지에 대한 추가 검증은 없다. [인증 세션][auth]

**설계 제안:** 필요한 문자열은 비어 있지 않은지 확인하고, 만료값은 양의 유효한 숫자로 검증한다. 내부 시간 단위는 초로 통일하고 `expires_at = 현재 시각(초) + 만료까지의 초 수`로 계산한다. 특정 수명을 상수로 가정하지 않고 응답값을 사용한다.

## Token refresh flow

**공식 규약:** [토큰 갱신][refresh]

```http
POST https://securetoken.googleapis.com/v1/token?key=<FIREBASE_API_KEY>
Content-Type: application/x-www-form-urlencoded

grant_type=refresh_token&refresh_token=<URL_ENCODED_REFRESH_TOKEN>
```

| 요청 값 | 타입 | 의미 |
| --- | --- | --- |
| `key` (query) | string | Firebase API key |
| `grant_type` | string | 고정값 `refresh_token` |
| `refresh_token` | string | 기존 refresh token |

| 응답 필드 | 타입 | 내부 상태 |
| --- | --- | --- |
| `id_token` | string | 새 ID token |
| `refresh_token` | string | 기존 또는 새 refresh token. 반환값을 보관 |
| `user_id` | string | UID |
| `expires_in` | string | ID token 만료까지의 초 수 |

**기존 구현:** 위 endpoint와 필드명을 사용하지만 요청 본문은 JSON으로 보낸다. 기본 HTTP transport의 `json` 옵션을 사용하므로 공식 문서의 form 형식과 차이가 있다. JSON 요청의 실제 수용 여부는 이번 조사에서 검증하지 않았다. [인증 세션][auth] · [HTTP transport][http]

**기존 구현:** 남은 수명이 60초보다 길면 메모리의 토큰을 재사용하고, 그렇지 않으면 다음 세션 접근 시 갱신한다. 백그라운드 갱신은 없다. 성공한 응답으로 토큰·UID·만료 시각을 교체한다. 60초 여유는 이 구현의 정책이며 Firebase의 필수 규약은 아니다.

**설계 제안:** 공식 문서의 form 형식을 사용하고, HTTP 클라이언트에 form 인코딩을 맡긴다. 기존의 요청 시 갱신 방식과 60초 여유를 사용한다. 전체 응답 검증에 성공한 뒤 상태를 교체하며, 실패한 요청에 만료된 토큰을 반환하지 않는다.

### 실패 처리

**공식 규약:** API 오류 원인은 응답의 `error.message`에 담긴다. 갱신 오류에는 `TOKEN_EXPIRED`, `INVALID_REFRESH_TOKEN`, `USER_DISABLED`, `USER_NOT_FOUND`, `PROJECT_NUMBER_MISMATCH` 등이 있다. [오류 응답][errors] · [갱신 오류][refresh]

**기존 구현:**

- 로그인 HTTP 실패는 `AUTH_FAILED`, 응답 스키마 불일치는 `AUTH_RESPONSE_INVALID`로 처리한다.
- 갱신 HTTP 실패 또는 응답 스키마 불일치 시, 이메일·비밀번호로 시작한 세션은 다시 로그인한다.
- refresh token으로 시작한 세션은 각각 `AUTH_REFRESH_FAILED`, `AUTH_REFRESH_RESPONSE_INVALID`를 반환한다.
- 기본 transport의 네트워크 예외는 `UPSTREAM_REQUEST_FAILED`로 전달되며 위 재로그인 분기에 들어가지 않는다. JSON 파싱 예외 역시 스키마 검사 이전에 발생하므로 해당 분기로 처리되지 않는다.
- Firebase의 상세 오류 본문을 읽어 원인을 구분하지 않는다.

근거: [인증 세션][auth] · [HTTP transport][http]

**설계 제안:** 로그인 실패, 갱신 실패, 잘못된 응답, 네트워크 실패를 호출자가 구분할 수 있게 한다. 갱신 실패 시 비밀번호로 자동 재로그인하지 않고 실패를 전달한다. 재인증이 필요한 실패와 일시적인 통신 실패를 구분하며, 응답 원문이나 비밀번호·토큰을 오류 메시지에 넣지 않는다. 비밀번호를 재로그인 목적으로 세션에 계속 보관하지 않는다.

## Required configuration values

**기존 구현:** `TODOMATE_FIREBASE_API_KEY` 환경 변수를 읽고, 이메일·비밀번호 또는 refresh token은 생성자 인자로 받는다. Firestore project ID는 `config.ts`의 `firebaseConfig.projectId`, database는 `(default)`를 사용한다. [설정][config] · [클라이언트][client] · [Firestore 호출부][firestore]

**설계 제안:** 설정·로그인 입력과 실행 중 세션 상태를 다음처럼 구분한다. 아래 이름은 역할을 나타내며, 새 환경 변수 이름을 확정하는 것은 아니다.

| 구분 | 값 | 담당 |
| --- | --- | --- |
| 인증 설정 | Firebase API key | 인증 Client |
| 로그인 입력 | 이메일·비밀번호 | 로그인 호출 |
| 실행 중 상태 | ID token, refresh token, UID, 만료 시각 | 인증 세션, 메모리 보관 |
| Firestore 설정 | project ID, database ID | Firestore Client |

API key는 사용자 ID token을 대신하지 않는다. 참고 서버의 CORS·포트·자체 세션 암호화 설정은 이슈 #2의 Firebase 인증 세션에 포함하지 않는다. 실제 인증값은 코드나 이 문서에 기록하지 않는다.

## MCP에서 구현할 예정인 인증 책임

**설계 제안:** 이슈 #2의 `FirebaseAuthSession`은 다음만 담당한다.

1. 이메일·비밀번호로 로그인하고 응답을 검증한다.
2. ID token, refresh token, UID, 만료 시각을 메모리에 관리한다.
3. 호출 시 유효한 ID token을 제공하며 필요하면 갱신한다.
4. 성공한 갱신 응답으로 세션을 교체한다.
5. 인증·응답·통신 실패를 구분해 전달하고 비밀값 노출을 막는다.

Firestore 요청과 Bearer 헤더 구성은 Firestore Client, MCP tool 입력 검증은 tool 계층이 담당한다. 인증 세션에는 Firestore 경로나 MCP 프로토콜 처리를 넣지 않는다.

저장된 refresh token으로 세션 복원하기, 디스크 보관, 환경 변수·secret 운영 정책은 이슈 [#12](https://github.com/LYJ0304/todomate-mcp/issues/12)에서 다룬다. Python 구현, 새 의존성, Firebase Admin SDK, 실제 계정 로그인은 이 문서 작업의 범위 밖이다.

## 기존 구현의 한계와 미확인 사항

- 갱신 요청 형식이 공식 문서와 다르다. Python 구현은 form 형식을 따른다.
- 만료값의 숫자 유효성 검증이 부족하다. 후속 구현에서 검증한다.
- 기존의 자동 재로그인과 포괄적 오류 처리는 그대로 복제하지 않는다. 위 실패 처리 제안을 적용한다.
- 실제 TodoMate 계정에서 이메일·비밀번호 로그인과 갱신이 가능한지, 프로젝트의 현재 인증 설정 및 Firestore Rules가 무엇인지는 확인하지 않았다.
- 실제 API 성공 여부나 JSON 갱신 요청의 호환성을 확인한 문서가 아니다. 기존 코드에서 확인한 사실과 공식 규약을 근거로 후속 구현 방향을 정리했다.

## 출처

- [기존 인증 세션][auth]
- [클라이언트 구성][client]
- [Firestore 호출부][firestore]
- [HTTP transport][http]
- [런타임 설정][config]
- [서버 로그인 라우트][routes]
- [Firebase 이메일·비밀번호 로그인][sign-in]
- [Firebase 토큰 갱신][refresh]
- [Firebase 오류 응답][errors]
- [Firestore REST 인증][firestore-auth]

[auth]: https://github.com/3x-haust/todomate-api/blob/987b3fe7bf8e580794e4d7b27ac5ced05426b068/src/firebase-auth.ts
[client]: https://github.com/3x-haust/todomate-api/blob/987b3fe7bf8e580794e4d7b27ac5ced05426b068/src/todomate-client.ts
[firestore]: https://github.com/3x-haust/todomate-api/blob/987b3fe7bf8e580794e4d7b27ac5ced05426b068/src/firestore-client.ts
[http]: https://github.com/3x-haust/todomate-api/blob/987b3fe7bf8e580794e4d7b27ac5ced05426b068/src/http.ts
[config]: https://github.com/3x-haust/todomate-api/blob/987b3fe7bf8e580794e4d7b27ac5ced05426b068/src/config.ts
[routes]: https://github.com/3x-haust/todomate-api/blob/987b3fe7bf8e580794e4d7b27ac5ced05426b068/src/server/auth-routes.ts
[sign-in]: https://firebase.google.com/docs/reference/rest/auth#section-sign-in-email-password
[refresh]: https://firebase.google.com/docs/reference/rest/auth#section-refresh-token
[errors]: https://firebase.google.com/docs/reference/rest/auth#section-error-format
[firestore-auth]: https://firebase.google.com/docs/firestore/use-rest-api#authentication_and_authorization
