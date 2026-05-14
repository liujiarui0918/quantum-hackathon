'use client';

import { Line } from '@antv/g2plot';
import { useEffect, useRef } from 'react';

export function MiniPowerChart({
  data,
  minRef,
  maxRef,
  height = 64,
}: {
  data: { t: string; p: number }[];
  minRef: number;
  maxRef: number;
  /** 图表高度（px），结果页用大高度展示更多时序细节 */
  height?: number;
}) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;

    const large = height >= 120;
    const labelSize = large ? 11 : height <= 96 ? 8 : 9;
    const axisStroke = 'rgba(110, 203, 255, 0.38)';
    const labelFill = 'rgba(138, 164, 191, 0.9)';
    const compact = height <= 96;
    const appendPadding = compact
      ? [4, 6, 14, 26]
      : large
        ? [10, 10, 26, 36]
        : [6, 8, 22, 32];

    const line = new Line(el, {
      data,
      xField: 't',
      yField: 'p',
      meta: {
        t: { alias: '时间' },
        p: { alias: '功率' },
      },
      appendPadding,
      height,
      autoFit: true,
      smooth: true,
      lineStyle: {
        stroke: 'rgba(61, 255, 206, 0.95)',
        lineWidth: large ? 1.6 : compact ? 1.15 : 1.25,
      },
      xAxis: {
        line: { style: { stroke: axisStroke } },
        tickLine: { style: { stroke: axisStroke } },
        label: {
          autoHide: true,
          autoRotate: large && !compact,
          style: { fill: labelFill, fontSize: labelSize },
        },
      },
      yAxis: {
        line: { style: { stroke: axisStroke } },
        tickLine: { style: { stroke: axisStroke } },
        label: {
          style: { fill: labelFill, fontSize: labelSize },
        },
        grid: {
          line: { style: { stroke: 'rgba(110, 203, 255, 0.12)' } },
        },
        title: {
          text: 'MW',
          style: { fill: labelFill, fontSize: labelSize },
          spacing: 8,
        },
      },
      tooltip: {
        showMarkers: false,
        fields: ['t', 'p'],
        formatter: (datum) => ({ name: datum.t, value: `${datum.p} MW` }),
      },
      annotations: [
        {
          type: 'line',
          start: ['min', minRef],
          end: ['max', minRef],
          style: {
            stroke: 'rgba(110, 203, 255, 0.85)',
            lineWidth: 1,
            lineDash: [3, 3],
          },
        },
        {
          type: 'line',
          start: ['min', maxRef],
          end: ['max', maxRef],
          style: {
            stroke: 'rgba(255, 77, 79, 0.85)',
            lineWidth: 1,
            lineDash: [3, 3],
          },
        },
      ],
    });

    line.render();
    return () => {
      line.destroy();
    };
  }, [data, minRef, maxRef, height]);

  return <div ref={ref} style={{ width: '100%', height }} />;
}
