// frontend/app/page.tsx
// Quick one-page admin: fetch /stats and render KPIs + tables (shadcn/ui 기반 최소)
"use client";

import { useEffect, useState } from "react";
import { Tooltip, TooltipProvider, TooltipTrigger, TooltipContent } from "@/components/ui/tooltip";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { FaRss, FaCalendarAlt, FaClock } from "react-icons/fa";

type DomainRow = { domain: string; count: number };
type FeedRow = { 
  feed_url: string; 
  feed_title: string; 
  total: number; 
  recent_7d?: number;
  [key: string]: string | number | undefined;
};

type Stats = {
  generated_at: string;
  days: number;
  feeds: number;
  entries_total: number;
  entries_recent: number;
  domains_top10: DomainRow[];
  weekday_dist: Record<string, number>;
  by_feed: FeedRow[];
  date_range: {
    start_date: string;
    end_date: string;
  };
};

export default function Page() {
  const [data, setData] = useState<Stats | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const base = process.env.NEXT_PUBLIC_RSS_API ?? "http://localhost:8030";

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        setError(null);
        const response = await fetch(`${base}/stats?days=7`, {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
          },
        });
        
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const result = await response.json();
        setData(result);
      } catch (err) {
        console.error('Fetch error:', err);
        const errorMessage = err instanceof Error ? err.message : '알 수 없는 오류가 발생했습니다.';
        setError(errorMessage);
        setData(null);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
    const interval = setInterval(fetchData, 60000); // 1 minute interval
    return () => clearInterval(interval);
  }, [base]);

  const [sortConfig, setSortConfig] = useState<{ key: string; direction: string } | null>(null);

  if (loading) return <div className="p-6">Loading…</div>;
  if (error) {
    return (
      <div className="p-6">
        <div className="text-red-500 font-semibold mb-2">오류 발생</div>
        <div className="text-sm text-gray-600 mb-4">{error}</div>
        <div className="text-xs text-gray-500">
          API 서버가 실행 중인지 확인하세요: {base}
        </div>
      </div>
    );
  }
  if (!data) return <div className="p-6">데이터를 불러올 수 없습니다.</div>;

  const sortedFeeds = [...data.by_feed].sort((a, b) => {
    if (sortConfig !== null) {
      const aVal = a[sortConfig.key];
      const bVal = b[sortConfig.key];
      if (aVal !== undefined && bVal !== undefined) {
        if (aVal < bVal) {
          return sortConfig.direction === "ascending" ? -1 : 1;
        }
        if (aVal > bVal) {
          return sortConfig.direction === "ascending" ? 1 : -1;
        }
      }
    }
    return 0;
  });

  return (
    <TooltipProvider>
      <main className="p-6 space-y-6">
        <h1 className="text-2xl font-bold">RedFin RSS Admin</h1>

        {/* KPI */}
        <section className="flex flex-wrap justify-between gap-4">
          <Card className="flex-1 min-w-[200px]">
            <CardHeader className="flex flex-row items-center space-x-2">
              <FaRss className="text-blue-500" />
              <CardTitle className="text-lg">Feeds</CardTitle>
            </CardHeader>
            <CardContent>
              <p>{data.feeds}</p>
            </CardContent>
          </Card>
          <Card className="flex-1 min-w-[200px]">
            <CardHeader className="flex flex-row items-center space-x-2">
              <FaCalendarAlt className="text-green-500" />
              <CardTitle>Entries (total)</CardTitle>
            </CardHeader>
            <CardContent>
              <p>{data.entries_total}</p>
            </CardContent>
          </Card>
          <Card className="flex-1 min-w-[200px]">
            <CardHeader className="flex flex-row items-center space-x-2">
              <FaClock className="text-yellow-500" />
              <CardTitle>Entries (recent {data.days}d)</CardTitle>
            </CardHeader>
            <CardContent>
              <p>{data.entries_recent}</p>
            </CardContent>
          </Card>
          <Card className="flex-1 min-w-[200px]">
            <CardHeader className="flex flex-row items-center space-x-2">
              <FaCalendarAlt className="text-purple-500" />
              <CardTitle>Generated</CardTitle>
            </CardHeader>
            <CardContent>
              <p>{new Date(data.generated_at).toLocaleString()}</p>
            </CardContent>
          </Card>
          <Card className="flex-1 min-w-[200px]">
            <CardHeader className="flex flex-row items-center space-x-2">
              <FaCalendarAlt className="text-red-500" />
              <CardTitle>Date Range</CardTitle>
            </CardHeader>
            <CardContent>
              <p>{new Date(data.date_range.start_date).toLocaleDateString()} - {new Date(data.date_range.end_date).toLocaleDateString()}</p>
            </CardContent>
          </Card>
        </section>

        {/* Domains */}
        <section>
          <h2 className="text-xl font-semibold mb-2">
            Top Domains{" "}
            <Tooltip>
              <TooltipTrigger asChild>
                <span className="text-gray-500 cursor-pointer">(?)</span>
              </TooltipTrigger>
              <TooltipContent>
                <p>이 섹션은 주어진 기간 동안 가장 많이 언급된 도메인을 보여줍니다.</p>
              </TooltipContent>
            </Tooltip>
          </h2>
          <table className="w-full text-sm">
            <thead><tr><th className="text-left">Domain</th><th className="text-right">Count</th></tr></thead>
            <tbody>
              {data.domains_top10.map((d, i) => (
                <tr key={i} className="border-b">
                  <td>{d.domain}</td>
                  <td className="text-right">{d.count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>

        {/* Feeds */}
        <section>
          <h2 className="text-xl font-semibold mb-2">
            Feeds{" "}
            <Tooltip>
              <TooltipTrigger asChild>
                <span className="text-gray-500 cursor-pointer">(?)</span>
              </TooltipTrigger>
              <TooltipContent>
                <p>이 섹션은 특정 RSS 피드의 URL과 해당 피드에서 수집된 항목의 총 수 및 최근 7일 동안 수집된 항목 수를 보여줍니다.</p>
              </TooltipContent>
            </Tooltip>
          </h2>
          <table className="w-full text-sm">
            <thead>
              <tr>
                <th className="text-left" onClick={() => setSortConfig({ key: "feed_title", direction: sortConfig?.direction === "ascending" ? "descending" : "ascending" })}>Feed</th>
                <th className="text-right" onClick={() => setSortConfig({ key: "total", direction: sortConfig?.direction === "ascending" ? "descending" : "ascending" })}>Total</th>
                <th className="text-right" onClick={() => setSortConfig({ key: "recent_7d", direction: sortConfig?.direction === "ascending" ? "descending" : "ascending" })}>Recent 7d</th>
              </tr>
            </thead>
            <tbody>
              {sortedFeeds.map((f, i) => (
                <tr key={i} className="border-b">
                  <td>{f.feed_title}</td>
                  <td className="text-right">{f.total}</td>
                  <td className="text-right">{f.recent_7d ?? 0}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      </main>
    </TooltipProvider>
  );
}

function KPI({ title, value }: { title: string; value: any }) {
  return (
    <div className="rounded-lg shadow-md p-4 bg-white">
      <div className="text-sm text-gray-500">{title}</div>
      <div className="text-2xl font-semibold">{String(value)}</div>
    </div>
  );
}

<style jsx>{`
  .tooltip {
    position: relative;
    display: inline-block;
    cursor: pointer;
  }

  .tooltip .tooltiptext {
    visibility: hidden;
    width: 150px;
    background-color: rgba(0, 0, 0, 0.75);
    color: #fff;
    text-align: center;
    border-radius: 4px;
    padding: 8px;
    position: absolute;
    z-index: 10;
    bottom: 100%;
    left: 50%;
    margin-left: -75px;
    opacity: 0;
    transition: opacity 0.3s;
  }

  .tooltip:hover .tooltiptext {
    visibility: visible;
    opacity: 1;
  }
`}</style>
