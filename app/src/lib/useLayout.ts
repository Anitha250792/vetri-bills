import { useWindowDimensions } from 'react-native';

import { MAX_WIDTH } from '@/theme';

/** Product grid: 2 columns on a phone, 3 on a tablet, 4 on a wide web page. */
export function useLayout() {
  const { width } = useWindowDimensions();
  const content = Math.min(width, MAX_WIDTH);
  const columns = width >= 1000 ? 4 : width >= 680 ? 3 : 2;
  const gap = 12;
  const gutter = 14;
  const cardWidth = (content - gutter * 2 - gap * (columns - 1)) / columns;
  return { width, content, columns, gap, gutter, cardWidth, wide: width >= 900 };
}
