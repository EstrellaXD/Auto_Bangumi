import { createSharedComposable, useBreakpoints } from '@vueuse/core';

export const useBreakpointQuery = createSharedComposable(() => {
  const breakpoints = useBreakpoints({
    tablet: 640,
    pc: 1024,
  });

  const isMobile = breakpoints.smaller('tablet');          // <640px (phones)
  const isTablet = breakpoints.between('tablet', 'pc');    // 640-1023px (tablets)
  const isPC = breakpoints.isGreater('pc');                // >=1024px (desktop)
  const isMobileOrTablet = breakpoints.smaller('pc');      // <1024px (legacy isMobile)
  const isTabletOrPC = breakpoints.greaterOrEqual('tablet'); // >=640px

  return {
    breakpoints,
    isMobile,
    isTablet,
    isPC,
    isMobileOrTablet,
    isTabletOrPC,
  };
});
