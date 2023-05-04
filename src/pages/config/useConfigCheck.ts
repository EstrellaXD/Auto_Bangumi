import { form } from './form-data';

export function checkIp(ip: string) {
  const check =
    /^((\d|[1-9]\d|1\d\d|2[0-4]\d|25[0-5])\.){3}(\d|[1-9]\d|1\d\d|2[0-4]\d|25[0-5])(?::(?:[0-9]|[1-9][0-9]{1,3}|[1-5][0-9]{4}|6[0-4][0-9]{3}|65[0-4][0-9]{2}|655[0-2][0-9]|6553[0-5]))?$/;

  return check.test(ip);
}

/** 有效端口检测 */
export function checkPort(port?: number) {
  if (!port) return false;
  if (port >= 0 && port <= 65535) return true;
  else return false;
}

/** host 格式检测 */
export function checkHost(host: string): [boolean, string] {
  if (host === '') return [false, '请输入host'];
  if (!/:/.test(host)) {
    return [false, "缺少 ':'"];
  } else {
    const [ip, port] = host.split(':');

    if (!checkIp(ip)) {
      return [false, '请输入有效ip!'];
    }

    if (!checkPort(Number(port))) {
      return [false, '请输入有效端口!'];
    }
  }

  return [true, ''];
}

export function useConfigCheck() {
  /** 端口验证 */
  function validtePort(rule: any, value: any, callback: any) {
    if (value === '') return callback(new Error('请输入端口号'));

    if (!checkPort(value)) {
      callback(new Error('无效端口 (端口范围 0 - 65535)'));
    } else {
      callback();
    }
  }

  /** host 验证 */
  function validteHost(rule: any, value: any, callback: any) {
    const [c, m] = checkHost(value);
    if (!c) return callback(new Error(m));
    callback();
  }

  /** proxy 启用时检测 ip 和 端口 */
  const validteFormProxy = {
    ip(rule: any, value: any, callback: any) {
      if (form.proxy.enable) {
        if (!checkIp(value)) return callback(new Error('请输入有效ip!'));
      }
      callback();
    },
    port(rule: any, value: any, callback: any) {
      if (form.proxy.enable) {
        if (!checkPort(value)) return callback(new Error('请输入有效端口!'));
      }
      callback();
    },
  };

  return {
    validtePort,
    validteHost,
    validteFormProxy,
  };
}
