import Link from "next/link";
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
import { Activity, ArrowRight, BarChart3, Database, ShieldCheck } from "lucide-react";

export default function HomePage() {
  return (
    <div className="space-y-8 max-w-4xl mx-auto">
      <div className="space-y-3">
        <div className="flex items-center space-x-2">
          <Badge variant="outline" className="text-xs py-0.5">
            Phase 0: Scaffolding
          </Badge>
          <Badge variant="success" className="text-xs py-0.5">
            Ready
          </Badge>
        </div>
        <h1 className="text-4xl font-extrabold tracking-tight sm:text-5xl text-slate-900 dark:text-white">
          Backtesting Framework
        </h1>
        <p className="text-lg text-slate-600 dark:text-slate-400">
          High-performance quantitative backtesting architecture tailored for Indian
          equities across NSE 101–750 constituents with bias-free historical execution.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 pt-4">
        <Card className="border-slate-200 dark:border-slate-800 shadow-sm hover:shadow transition-shadow">
          <CardHeader className="pb-3">
            <div className="p-2 w-10 h-10 rounded-lg bg-blue-100 dark:bg-blue-950 text-blue-600 dark:text-blue-400 flex items-center justify-center mb-2">
              <Activity className="w-5 h-5" />
            </div>
            <CardTitle className="text-base font-semibold">FastAPI Engine</CardTitle>
            <CardDescription className="text-xs">
              Asynchronous API with structured JSON telemetry and OpenAPI contracts.
            </CardDescription>
          </CardHeader>
          <CardContent className="text-xs text-slate-500">
            Endpoint: <code className="bg-slate-100 dark:bg-slate-800 px-1 py-0.5 rounded">:8000/health</code>
          </CardContent>
          <CardFooter className="pt-0">
            <Button asChild variant="outline" size="sm" className="w-full text-xs">
              <Link href="/api-health">
                Check Status <ArrowRight className="w-3.5 h-3.5 ml-1" />
              </Link>
            </Button>
          </CardFooter>
        </Card>

        <Card className="border-slate-200 dark:border-slate-800 shadow-sm hover:shadow transition-shadow">
          <CardHeader className="pb-3">
            <div className="p-2 w-10 h-10 rounded-lg bg-emerald-100 dark:bg-emerald-950 text-emerald-600 dark:text-emerald-400 flex items-center justify-center mb-2">
              <BarChart3 className="w-5 h-5" />
            </div>
            <CardTitle className="text-base font-semibold">Universe & Trend</CardTitle>
            <CardDescription className="text-xs">
              Prepared for NSE 750 (excluding top 100), 4-EMA stacking and market regime filters.
            </CardDescription>
          </CardHeader>
          <CardContent className="text-xs text-slate-500">
            Look-ahead & survivorship bias mitigation ready.
          </CardContent>
          <CardFooter className="pt-0">
            <Button variant="ghost" size="sm" disabled className="w-full text-xs text-slate-400">
              Phase 1–3
            </Button>
          </CardFooter>
        </Card>

        <Card className="border-slate-200 dark:border-slate-800 shadow-sm hover:shadow transition-shadow">
          <CardHeader className="pb-3">
            <div className="p-2 w-10 h-10 rounded-lg bg-indigo-100 dark:bg-indigo-950 text-indigo-600 dark:text-indigo-400 flex items-center justify-center mb-2">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <CardTitle className="text-base font-semibold">Full Test Harness</CardTitle>
            <CardDescription className="text-xs">
              Pytest (≥80% cov), Vitest component mocks with MSW, and Playwright E2E suites.
            </CardDescription>
          </CardHeader>
          <CardContent className="text-xs text-slate-500">
            CI automated verification on pull requests.
          </CardContent>
          <CardFooter className="pt-0">
            <Button variant="ghost" size="sm" disabled className="w-full text-xs text-slate-400">
              Verified
            </Button>
          </CardFooter>
        </Card>
      </div>

      <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-6 flex flex-col sm:flex-row items-center justify-between gap-4">
        <div className="flex items-center space-x-4">
          <div className="p-3 bg-blue-50 dark:bg-blue-900/30 rounded-full text-blue-600">
            <Database className="w-6 h-6" />
          </div>
          <div>
            <h4 className="font-semibold text-sm">System Verification</h4>
            <p className="text-xs text-slate-500">
              Confirm end-to-end communication with the backend service.
            </p>
          </div>
        </div>
        <Button asChild>
          <Link href="/api-health">
            Open Health Diagnostic <ArrowRight className="w-4 h-4 ml-2" />
          </Link>
        </Button>
      </div>
    </div>
  );
}
