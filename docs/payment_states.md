# 決済状態遷移と通知シナリオ

課金フローの文言とUIは既存のまま維持しつつ、運用で詰まりやすいポイント（二重決済・失敗・返金）を整理します。表はコードの既存挙動（bot/main.py・core/db.py）に合わせています。

## 状態遷移

| 状態/イベント | 主なトリガー | DB 反映 | ユーザー通知 | 備考 |
| --- | --- | --- | --- | --- |
| pre_checkout 受領 | 正常な購入開始 | payment_events に `pre_checkout` を記録 | なし（エラー時のみ表示） | payload の user_id が一致しない場合は pre_checkout_rejected としてブロック |
| payment 受領 | `successful_payment` | payments に `paid` で記録。payment_events に `successful_payment` | 「ご購入ありがとうございました」+ /status 案内 | 同一 charge_id で重複した場合は後続を `successful_payment_duplicate` としてスキップ |
| 権限付与 | `grant_purchase`（正常決済・管理者付与） | users の pass/ticket/images を更新 | 付与完了メッセージ + /status 案内 | /admin grant も同じ処理経路で付与し、audit に記録 |
| 二重決済検出 | 同一 charge_id での再送 | payments は既存行を再利用（追加付与なし） | 「すでに処理済みです」+ /status 案内 | payment_events は `successful_payment_duplicate` |
| 返金完了 | /refund 実行 | payments.status=`refunded`、refunded_at 更新、payment_events に `refund` | 管理者へ「返金処理が完了しました」 | ユーザー通知は運用で案内（/status で確認を依頼） |
| 失敗/不正 | SKU 不明・payload 不一致 | payment_events に `pre_checkout_invalid_product` または `pre_checkout_rejected` | 「商品情報を確認できませんでした」「購入者情報を確認できませんでした」等を即時表示 | ユーザーに対して丁寧なリトライ案内のみ |

## 通知シナリオ（運用フロー）

| シナリオ | 判定方法 | 管理者のアクション | ユーザーへの案内 |
| --- | --- | --- | --- |
| 二重決済が疑われる | payment_events に `successful_payment_duplicate` が記録され、ユーザーには「処理済みです」と返答 | /status で権限が重複付与されていないか確認。必要なら /admin grant または /admin revoke で調整 | 「重複分は処理済みです。/status で現在の権限をご確認ください」と返信 |
| 決済失敗/不正 | pre_checkout で SKU 不一致・ユーザーID不一致などが検知され、エラーメッセージを返している | ログ（payment_events）で原因を確認。設定ミスの場合は修正後に再試行を案内 | 「購入者情報の確認に失敗しました。恐れ入りますが、もう一度 /buy からお試しください」と伝達 |
| 返金 | 管理者が /refund <charge_id> を実行し、payments.status が `refunded` に更新 | 処理完了後に audit/payment_events を確認し記録を残す | 「返金処理が完了しました。/status で権限を確認ください。反映に時間がかかる場合はサポートへご連絡ください」と送付 |
