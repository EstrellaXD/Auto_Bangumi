export type SelectItem = {
  id: number;
  label?: string;
  value: string;
  disabled?: boolean;
};

export type AbSettingProps = {
  label: string;
  type: 'input' | 'switch' | 'select';
  css?: string;
  prop?: any;
  bottomLine?: boolean;
};

export type SettingItem<T> = AbSettingProps & {
  configKey: keyof T;
  data?: any;
};
