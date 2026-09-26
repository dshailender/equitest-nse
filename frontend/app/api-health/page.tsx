"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { Activity, AlertCircle, ArrowLeft, CheckCircle2, RefreshCw } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { fetchHealth } from "@/lib/api";

export default function ApiHealthPage() {
  const { data, error, isLoading, isError, refetch, isFetching } = useQuery({
    queryKey: ["health"],
    queryFn: fetchHealth,
  });

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div>
        <Button asChild variant="ghost" size="sm" className="mb-4 -ml-2 text-xs">
          <Link href="/">
            <ArrowLeft className="w-3.5 h-3.5 mr-1" /> Back to Dashboard
          </Link>
        </Button>
        <h1 className="text-3xl font-bold tracking-tight text-slate-900 dark:text-white">
          API Health Diagnostic
        </h1>
        <p className="text-sm text-slate-600 dark:text-slate-400 mt-1">
          Validates connectivity to the FastAPI backend and verifies OpenAPI response contracts.
        </p>
      </div>

      <Card className="border-slate-200 dark:border-slate-800 shadow-sm">
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <Activity className="w-5 h-5 text-blue-600" />
              <CardTitle className="text-lg">Backend Service</CardTitle>
            </div>
            {isLoading ? (
              <Badge variant="outline" className="animate-pulse">
                Checking...
              </Badge>
            ) : isError ? (
              <Badge variant="destructive" data-testid="health-badge-error">
                Degraded
              </Badge>
            ) : (
              <Badge variant="success" data-testid="health-badge-ok">
                Operational
              </Badge>
            )}
          </div>
          <CardDescription className="text-xs">
            Direct query to target endpoint: <code className="font-mono">/health</code>
          </CardDescription>
        </CardHeader>

        <CardContent className="space-y-4">
          {isLoading && (
            <div className="py-8 flex flex-col items-center justify-center space-y-2 text-slate-600 dark:text-slate-400">
              <RefreshCw className="w-6 h-6 animate-spin text-blue-600" />
              <p className="text-sm">Connecting to backend service...</p>
            </div>
          )}

          {isError && (
            <div
              className="p-4 rounded-lg bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-900 flex items-start space-x-3 text-red-700 dark:text-red-400"
              role="alert"
            >
              <AlertCircle className="w-5 h-5 shrink-0 mt-0.5" />
              <div className="text-xs space-y-1">
                <p className="font-semibold">Failed to fetch backend health status</p>
                <p>{error instanceof Error ? error.message : "Backend unreachable."}</p>
                <p className="text-slate-600 dark:text-slate-400">
                  Ensure the FastAPI backend is running on port 8000.
                </p>
              </div>
            </div>
          )}

          {data && (
            <div className="space-y-3">
              <div className="grid grid-cols-2 gap-4">
                <div className="p-4 rounded-lg bg-slate-100 dark:bg-slate-900 border border-slate-200 dark:border-slate-800">
                  <span className="text-xs font-medium text-slate-600 dark:text-slate-400 block mb-1">
                    Reported Status
                  </span>
                  <div className="flex items-center space-x-2">
                    <CheckCircle2 className="w-4 h-4 text-emerald-700 dark:text-emerald-400" />
                    <span
                      data-testid="health-status"
                      className="font-mono font-bold text-lg text-emerald-700 dark:text-emerald-400"
                    >
                      {data.status}
                    </span>
                  </div>
                </div>

                <div className="p-4 rounded-lg bg-slate-100 dark:bg-slate-900 border border-slate-200 dark:border-slate-800">
                  <span className="text-xs font-medium text-slate-600 dark:text-slate-400 block mb-1">
                    System Version
                  </span>
                  <span
                    data-testid="health-version"
                    className="font-mono font-bold text-lg text-slate-800 dark:text-slate-200"
                  >
                    {data.version}
                  </span>
                </div>
              </div>

              <div className="p-3 rounded bg-slate-900 text-slate-100 text-xs font-mono overflow-x-auto">
                <pre>{JSON.stringify(data, null, 2)}</pre>
              </div>
            </div>
          )}
        </CardContent>

        <CardFooter className="flex justify-between border-t border-slate-100 dark:border-slate-800 pt-4">
          <span className="text-xs text-slate-600 dark:text-slate-400">
            Validated by Zod schema • Typed by OpenAPI
          </span>
          <Button
            size="sm"
            variant="outline"
            onClick={() => refetch()}
            disabled={isFetching}
            className="text-xs"
          >
            <RefreshCw
              className={`w-3.5 h-3.5 mr-1.5 ${isFetching ? "animate-spin" : ""}`}
            />
            {isFetching ? "Refreshing..." : "Recheck"}
          </Button>
        </CardFooter>
      </Card>
    </div>
  );
}
