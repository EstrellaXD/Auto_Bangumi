import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';

function readSource(relativePath: string): string {
  return readFileSync(new URL(relativePath, import.meta.url), 'utf8');
}

function phoneStyles(relativePath: string): string {
  const source = readSource(relativePath);
  const marker = '@media screen and (max-width: 639px)';
  const start = source.indexOf(marker);

  return start === -1 ? '' : source.slice(start);
}

function scssBlocks(source: string, selector: string): string[] {
  const blocks: string[] = [];
  let searchFrom = 0;

  while (searchFrom < source.length) {
    const selectorStart = source.indexOf(selector, searchFrom);
    if (selectorStart === -1) break;
    const blockStart = source.indexOf('{', selectorStart + selector.length);
    if (blockStart === -1) break;

    let depth = 0;
    for (let index = blockStart; index < source.length; index++) {
      if (source[index] === '{') depth += 1;
      if (source[index] !== '}') continue;
      depth -= 1;
      if (depth !== 0) continue;

      blocks.push(source.slice(blockStart + 1, index));
      searchFrom = index + 1;
      break;
    }

    if (searchFrom <= selectorStart) break;
  }

  return blocks;
}

function scssBlock(source: string, selector: string): string {
  return scssBlocks(source, selector)[0] ?? '';
}

function relativeLuminance(hex: string): number {
  const channels = hex
    .slice(1)
    .match(/.{2}/g)!
    .map((channel) => Number.parseInt(channel, 16) / 255)
    .map((channel) =>
      channel <= 0.04045
        ? channel / 12.92
        : ((channel + 0.055) / 1.055) ** 2.4
    );

  return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2];
}

function contrastRatio(foreground: string, background: string): number {
  const lighter = Math.max(
    relativeLuminance(foreground),
    relativeLuminance(background)
  );
  const darker = Math.min(
    relativeLuminance(foreground),
    relativeLuminance(background)
  );

  return (lighter + 0.05) / (darker + 0.05);
}

describe('setup wizard structure contract', () => {
  it('should keep setup steps outside a shared form', () => {
    const sources = [
      '../../../pages/setup.vue',
      '../wizard-container.vue',
      '../wizard-step-welcome.vue',
      '../wizard-step-account.vue',
      '../wizard-step-downloader.vue',
      '../wizard-step-rss.vue',
      '../wizard-step-notification.vue',
      '../wizard-step-review.vue',
    ].map(readSource);

    expect(sources.join('\n')).not.toMatch(/<form\b/i);
  });
});

describe('setup wizard mobile layout contract', () => {
  it('should scope setup page layout changes to phone widths', () => {
    expect(readSource('../../../pages/setup.vue')).toContain(
      '@media screen and (max-width: 639px)'
    );
  });

  it('should use dynamic viewport fallback and vertical scrolling on phones', () => {
    const pageRule = scssBlock(
      phoneStyles('../../../pages/setup.vue'),
      '.page-setup'
    );

    expect(pageRule).toMatch(
      /min-height:\s*100vh[\s\S]*?min-height:\s*100dvh[\s\S]*?align-items:\s*flex-start[\s\S]*?overflow-y:\s*auto/
    );
  });

  it('should pad every phone edge with its safe-area inset', () => {
    const pageRule = scssBlock(
      phoneStyles('../../../pages/setup.vue'),
      '.page-setup'
    );

    expect(pageRule).toMatch(
      /safe-area-inset-top[\s\S]*?safe-area-inset-right[\s\S]*?safe-area-inset-bottom[\s\S]*?safe-area-inset-left/
    );
  });

  it('should let the wizard shrink to the phone viewport', () => {
    const wizardRule = scssBlock(
      phoneStyles('../wizard-container.vue'),
      '.wizard-container'
    );

    expect(wizardRule).toMatch(
      /width:\s*100%[\s\S]*?max-width:\s*none[\s\S]*?min-width:\s*0/
    );
  });

  it('should make setup inputs full-width 44px targets with 16px text', () => {
    const inputRule = scssBlock(
      phoneStyles('../wizard-container.vue'),
      ':deep(.setup-input),'
    );

    expect(inputRule).toMatch(
      /width:\s*100%[\s\S]*?min-height:\s*var\(--touch-target\)[\s\S]*?font-size:\s*16px/
    );
  });

  it('should make wizard buttons and Naive select controls 44px tall', () => {
    const styles = phoneStyles('../wizard-container.vue');
    const buttonRule = scssBlock(styles, ':deep(.wizard-actions .ab-btn),');
    const selectRule = scssBlock(styles, ':deep(.n-base-selection),');

    expect({
      buttonIsTouchSafe: buttonRule.includes(
        'min-height: var(--touch-target)'
      ),
      selectIsTouchSafe: selectRule.includes(
        'min-height: var(--touch-target)'
      ),
    }).toEqual({ buttonIsTouchSafe: true, selectIsTouchSafe: true });
  });

  it('should make the mobile switch a 44px square target', () => {
    const switchRule = scssBlock(
      phoneStyles('../wizard-container.vue'),
      ':deep(.n-switch)'
    );

    expect(switchRule).toMatch(
      /min-width:\s*var\(--touch-target\)[\s\S]*?min-height:\s*var\(--touch-target\)/
    );
  });

  it('should allow mobile review values and status messages to wrap', () => {
    const styles = phoneStyles('../wizard-container.vue');
    const messageWraps = scssBlocks(styles, ':deep(.test-message)').some(
      (block) => block.includes('overflow-wrap: anywhere')
    );
    const reviewWraps = scssBlocks(styles, ':deep(.review-value)').some(
      (block) => block.includes('white-space: normal')
    );

    expect({ messageWraps, reviewWraps }).toEqual({
      messageWraps: true,
      reviewWraps: true,
    });
  });

  it('should keep mobile status text AA-readable in light and dark themes', () => {
    const styles = phoneStyles('../wizard-container.vue');
    const lightColors = styles.match(
      /\.wizard-container\s*\{[^}]*--setup-status-error:\s*(#[\da-f]{6});[^}]*--setup-status-success:\s*(#[\da-f]{6});/i
    );
    const darkColors = styles.match(
      /:global\(\.dark\) \.wizard-container\s*\{[^}]*--setup-status-error:\s*(#[\da-f]{6});[^}]*--setup-status-success:\s*(#[\da-f]{6});/i
    );
    const usesStatusVariables =
      /:deep\(\.error-text\),\s*:deep\(\.test-message\)\s*\{[^}]*color:\s*var\(--setup-status-error\)/.test(
        styles
      ) &&
      /:deep\(\.test-message\.success\)\s*\{[^}]*color:\s*var\(--setup-status-success\)/.test(
        styles
      );

    expect({
      darkError:
        darkColors && contrastRatio(darkColors[1], '#1e293b') >= 4.5,
      darkSuccess:
        darkColors && contrastRatio(darkColors[2], '#1e293b') >= 4.5,
      lightError:
        lightColors && contrastRatio(lightColors[1], '#ffffff') >= 4.5,
      lightSuccess:
        lightColors && contrastRatio(lightColors[2], '#ffffff') >= 4.5,
      usesStatusVariables,
    }).toEqual({
      darkError: true,
      darkSuccess: true,
      lightError: true,
      lightSuccess: true,
      usesStatusVariables: true,
    });
  });
});
