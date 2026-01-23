/**
 * Passkey 类型定义
 */

// Passkey 列表项
export interface PasskeyItem {
  id: number;
  name: string;
  created_at: string;
  last_used_at: string | null;
  backup_eligible: boolean;
  aaguid: string | null;
}

// 注册选项（从后端返回）
export interface RegistrationOptions {
  challenge: string;
  rp: { name: string; id: string };
  user: {
    id: string;
    name: string;
    displayName: string;
  };
  pubKeyCredParams: Array<{ type: string; alg: number }>;
  timeout?: number;
  excludeCredentials?: Array<{
    type: string;
    id: string;
    transports?: string[];
  }>;
  authenticatorSelection?: {
    residentKey?: string;
    userVerification?: string;
  };
}

// 认证选项
export interface AuthenticationOptions {
  challenge: string;
  timeout?: number;
  rpId?: string;
  allowCredentials?: Array<{
    type: string;
    id: string;
    transports?: string[];
  }>;
  userVerification?: string;
}

// 注册请求
export interface PasskeyCreateRequest {
  name: string;
  attestation_response: unknown;
}

// 删除请求
export interface PasskeyDeleteRequest {
  passkey_id: number;
}

// 认证开始请求
export interface PasskeyAuthStartRequest {
  username: string;
}

// 认证完成请求
export interface PasskeyAuthFinishRequest {
  username: string;
  credential: unknown;
}
