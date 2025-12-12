# API_SPEC

# API Specification (MVP)

Base URL: `/api`

## 1. Health Check

### GET /api/health

- 説明: APIサーバのヘルスチェック。
- レスポンス例:

```json
{
  "status": "ok",
  "env": "dev-local"
}
