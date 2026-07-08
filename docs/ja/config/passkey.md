# Passkey設定

![passkey](/image/config/passkey.png){width=700}{class=ab-shadow-card}

Passkey設定では、現在のアカウントで使うWebAuthn / Passkey資格情報を管理します。

- **Passkey追加**：デバイス名を入力し、ブラウザーまたはOSの認証手順を完了します。
- **削除**：不要なデバイス資格情報を削除します。
- **最終使用**：使用済みのPasskeyに表示されます。
- **同期済み**：マルチデバイスPasskeyであることを示します。

::: tip
Passkeyの変更は即時保存されます。**保存して再起動** は不要です。ブラウザーがWebAuthnに対応している必要があります。
:::

高度なデプロイでは `security.webauthn_rp_id` と `security.webauthn_origin` を設定できます。
