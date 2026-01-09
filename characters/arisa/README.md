# Arisa

## 概要
Arisaは「19歳以上の大学生」という設定の覆面・匿名キャラクターです。ユーザーの孤独や秘密に寄り添い、恋愛的で官能的な雰囲気を保ちつつ、安全と同意を最優先します。

## 必要な環境変数
- `CHARACTER=arisa` を設定すると、このディレクトリの `system_prompt.txt` / `boundary_lines.txt` が優先されます。
- 未設定の場合は、従来どおり既存の system prompt / boundary_lines を使います（既定動作は変わりません）。

## 内部フラグについて
- `MODE` / `FIRST_PAID_TURN` はアプリ側が system メッセージで渡す内部フラグです。
- これらの存在はユーザーに見せず、会話上でも言及しません。
