export interface SelectItem {
  id: number;
  label?: string;
  value: string;
  disabled?: boolean;
}

export interface AbSettingProps {
  label: string;
  type: 'input' | 'switch' | 'select' | 'dynamic-tags';
  css?: string;
  prop?: any;
  bottomLine?: boolean;
}

export type SettingItem<T> = AbSettingProps & {
  configKey: keyof T;
};

export interface AbEditRuleItem {
  id: number;
  official_title: string;
  year: string;
  season: number;
  offset: number;
  filter: string[];
}
