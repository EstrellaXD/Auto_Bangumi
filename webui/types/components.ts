export interface SelectItem {
  id: number;
  label?: string;
  value: string;
  disabled?: boolean;
}

export interface AbSettingProps {
  label: string | (() => string);
  type: 'input' | 'switch' | 'select' | 'dynamic-tags';
  css?: string;
  prop?: any;
  bottomLine?: boolean;
  /** 字段说明文字（显示在标签下方） */
  description?: string;
  /** 校验错误文案（显示为错误态） */
  error?: string;
  required?: boolean;
}

export type SettingItem<T> = AbSettingProps & {
  configKey: keyof T;
};
