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
    const labelSize = large ? 11 : height <= 96 ? 9 : 10;
    const axisStroke = 'var(--line)';
    const labelFill = 'var(--muted)';
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
        stroke: 'var(--accent)',
        lineWidth: large ? 2.5 : compact ? 1.5 : 2,
      },
      xAxis: {
        line: { style: { stroke: axisStroke } },
        tickLine: { style: { stroke: axisStroke } },
        label: {
          autoHide: true,
          autoRotate: large && !compact,
          style: { fill: labelFill, fontSize: labelSize, fontWeight: 500 },
        },
      },
      yAxis: {
        line: { style: { stroke: axisStroke } },
        tickLine: { style: { stroke: axisStroke } },
        label: {
          style: { fill: labelFill, fontSize: labelSize, fontWeight: 500 },
        },
        grid: {
          line: { style: { stroke: 'var(--line)', lineDash: [2, 2] } },
        },
        title: {
          text: 'MW',
          style: { fill: labelFill, fontSize: labelSize, fontWeight: 600 },
          spacing: 8,
        },
      },
      tooltip: {
        showMarkers: false,
        fields: ['t', 'p'],
        formatter: (datum) => ({ name: datum.t, value: `${datum.p} MW` }),
        domStyles: {
          'g2-tooltip': {
            backgroundColor: '#fff',
            boxShadow: '0 8px 24px rgba(0,0,0,0.1)',
            borderRadius: '8px',
            border: '1px solid var(--line)',
            color: 'var(--text)',
            fontSize: '13px',
          }
        }
      },
      annotations: [
        {
          type: 'line',
          start: ['min', minRef],
          end: ['max', minRef],
          style: {
            stroke: 'var(--muted)',
            lineWidth: 1,
            lineDash: [4, 4],
          },
        },
        {
          type: 'line',
          start: ['min', maxRef],
          end: ['max', maxRef],
          style: {
            stroke: 'var(--accent2)',
            lineWidth: 1,
            lineDash: [4, 4],
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
