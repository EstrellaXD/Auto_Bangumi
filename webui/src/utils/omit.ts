export function omit<T extends { [k: string]: any }>(
  obj: T,
  omitKeys: Array<keyof T>
) {
  return Object.keys(obj).reduce((acc, key) => {
    if (omitKeys.includes(key)) {
      return acc;
    } else {
      return { ...acc, [key]: obj[key] };
    }
  }, {});
}
