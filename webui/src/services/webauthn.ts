import { apiPasskey } from '@/api/passkey';

/**
 * WebAuthn 浏览器 API 封装
 * 处理 Base64URL 编码和浏览器兼容性
 */

// ============ 工具函数 ============

function base64UrlToBuffer(base64url: string): ArrayBuffer {
  // 补齐 padding
  const base64 = base64url.replace(/-/g, '+').replace(/_/g, '/');
  const padding = '='.repeat((4 - (base64.length % 4)) % 4);
  const binary = atob(base64 + padding);

  const buffer = new ArrayBuffer(binary.length);
  const bytes = new Uint8Array(buffer);
  for (let i = 0; i < binary.length; i++) {
    bytes[i] = binary.charCodeAt(i);
  }
  return buffer;
}

function bufferToBase64Url(buffer: ArrayBuffer): string {
  const bytes = new Uint8Array(buffer);
  let binary = '';
  for (let i = 0; i < bytes.length; i++) {
    binary += String.fromCharCode(bytes[i]);
  }
  return btoa(binary).replace(/\+/g, '-').replace(/\//g, '_').replace(/=/g, '');
}

// ============ 注册流程 ============

/**
 * 注册新的 Passkey
 * @param deviceName 设备名称（用户输入）
 */
export async function registerPasskey(deviceName: string): Promise<void> {
  // 1. 获取注册选项
  const options = await apiPasskey.getRegistrationOptions();

  // 2. 转换选项为浏览器 API 格式
  const createOptions: PublicKeyCredentialCreationOptions = {
    challenge: base64UrlToBuffer(options.challenge),
    rp: options.rp,
    user: {
      id: base64UrlToBuffer(options.user.id),
      name: options.user.name,
      displayName: options.user.displayName,
    },
    pubKeyCredParams: options.pubKeyCredParams.map((p) => ({
      type: p.type as PublicKeyCredentialType,
      alg: p.alg,
    })),
    timeout: options.timeout || 60000,
    excludeCredentials: options.excludeCredentials?.map((cred) => ({
      type: cred.type as PublicKeyCredentialType,
      id: base64UrlToBuffer(cred.id),
      transports: cred.transports as AuthenticatorTransport[],
    })),
    authenticatorSelection: options.authenticatorSelection as AuthenticatorSelectionCriteria,
  };

  // 3. 调用浏览器 WebAuthn API
  let credential: PublicKeyCredential;
  try {
    const result = await navigator.credentials.create({
      publicKey: createOptions,
    });
    if (!result) {
      throw new Error('No credential returned');
    }
    credential = result as PublicKeyCredential;
  } catch (e: unknown) {
    if (e instanceof DOMException) {
      if (e.name === 'NotAllowedError') {
        throw new Error('Authentication was cancelled or timed out');
      }
      if (e.name === 'SecurityError') {
        throw new Error('WebAuthn requires a secure context (HTTPS or localhost)');
      }
      throw new Error(`Browser rejected the request: ${e.message}`);
    }
    throw e;
  }

  // 4. 序列化 credential 为 JSON
  const response = credential.response as AuthenticatorAttestationResponse;
  const attestationResponse = {
    id: credential.id,
    rawId: bufferToBase64Url(credential.rawId),
    type: credential.type,
    response: {
      clientDataJSON: bufferToBase64Url(response.clientDataJSON),
      attestationObject: bufferToBase64Url(response.attestationObject),
    },
  };

  // 5. 提交到后端验证
  await apiPasskey.verifyRegistration({
    name: deviceName,
    attestation_response: attestationResponse,
  });
}

// ============ 认证流程 ============

/**
 * 使用 Passkey 登录
 * @param username 用户名（可选，不提供时使用可发现凭证模式）
 */
export async function loginWithPasskey(username?: string): Promise<void> {
  // 1. 获取认证选项
  const options = await apiPasskey.getLoginOptions(
    username ? { username } : {}
  );

  // 2. 转换选项
  const getOptions: PublicKeyCredentialRequestOptions = {
    challenge: base64UrlToBuffer(options.challenge),
    timeout: options.timeout || 60000,
    rpId: options.rpId,
    // allowCredentials is undefined for discoverable credentials mode
    allowCredentials: options.allowCredentials?.map((cred) => ({
      type: cred.type as PublicKeyCredentialType,
      id: base64UrlToBuffer(cred.id),
      transports: cred.transports as AuthenticatorTransport[],
    })),
    userVerification: options.userVerification as UserVerificationRequirement,
  };

  // 3. 调用浏览器 API
  const credential = (await navigator.credentials.get({
    publicKey: getOptions,
  })) as PublicKeyCredential;

  if (!credential) {
    throw new Error('Failed to get credential');
  }

  // 4. 序列化响应
  const response = credential.response as AuthenticatorAssertionResponse;
  const assertionResponse = {
    id: credential.id,
    rawId: bufferToBase64Url(credential.rawId),
    type: credential.type,
    response: {
      clientDataJSON: bufferToBase64Url(response.clientDataJSON),
      authenticatorData: bufferToBase64Url(response.authenticatorData),
      signature: bufferToBase64Url(response.signature),
      userHandle: response.userHandle
        ? bufferToBase64Url(response.userHandle)
        : null,
    },
  };

  // 5. 提交到后端验证并登录
  await apiPasskey.loginWithPasskey({
    ...(username && { username }),
    credential: assertionResponse,
  });
}

// ============ 浏览器支持检测 ============

export function isWebAuthnSupported(): boolean {
  return !!(
    window.PublicKeyCredential &&
    navigator.credentials &&
    navigator.credentials.create
  );
}

export async function isPlatformAuthenticatorAvailable(): Promise<boolean> {
  if (!isWebAuthnSupported()) return false;

  try {
    return await PublicKeyCredential.isUserVerifyingPlatformAuthenticatorAvailable();
  } catch {
    return false;
  }
}
