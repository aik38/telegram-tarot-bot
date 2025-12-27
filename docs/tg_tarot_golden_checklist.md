# Telegram Tarot Golden Checklist

Use this list to validate critical Telegram experiences. All items should be ✅ before release.

## /start
- [ ] Bot greets user with expected welcome copy.
- [ ] Language and localization match current beta requirements.
- [ ] Quick menu or onboarding prompts appear without delay.

## Tarot flow (cards always shown)
- [ ] Tarot request can be triggered from the main menu.
- [ ] Spread selection and confirmation are available without errors.
- [ ] Cards are always displayed (image + text) in the final result.
- [ ] Post-reading follow-up actions (e.g., consult, share) remain visible.

## Consult flow (no extra keyboard prompt)
- [ ] Consult entry point is visible and reachable after tarot completion.
- [ ] Conversation proceeds without extra keyboard prompts or unexpected menus.
- [ ] User can send free-form text and receive consult responses.

## /buy
- [ ] Command responds with current purchase options or paywall messaging.
- [ ] Payment instructions and CTAs render correctly.

## /status
- [ ] Command returns current account status and entitlements.
- [ ] Any usage counters or limits display accurate values.
