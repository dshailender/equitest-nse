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
import {
  ArrowRight,
  BarChart3,
  BookOpen,
  CheckCircle2,
  Cpu,
  Database,
  FileText,
  Layers,
  Play,
  Scale,
  ShieldCheck,
  Sliders,
  TrendingUp,
} from "lucide-react";

export default function HomePage() {
  return (
    <div className="space-y-12 max-w-6xl mx-auto pb-12">
      {/* Hero Section */}
      <section className="space-y-6 pt-4 text-center sm:text-left">
        <div className="flex flex-wrap items-center justify-center sm:justify-start gap-2">
          <Badge variant="outline" className="text-xs py-0.5 border-blue-200 text-blue-700 dark:border-blue-800 dark:text-blue-300">
            Institutional Quantitative Platform
          </Badge>
          <Badge variant="success" className="text-xs py-0.5">
            NSE 101–750 Universe
          </Badge>
          <Badge variant="secondary" className="text-xs py-0.5">
            Zero Look-Ahead Bias
          </Badge>
        </div>

        <div className="space-y-3">
          <h1 className="text-4xl font-extrabold tracking-tight sm:text-5xl text-slate-900 dark:text-white">
            NSE 101–750 Quantitative Backtesting Framework
          </h1>
          <p className="text-lg text-slate-600 dark:text-slate-400 max-w-3xl leading-relaxed">
            High-performance event-driven simulation architecture designed for Indian equities.
            Enforces institutional research standards with point-in-time constituent tracking,
            4-EMA trend alignment, 2% risk capital sizing, and overnight gap-down realism.
          </p>
        </div>

        {/* Primary Action Buttons */}
        <div className="flex flex-wrap items-center justify-center sm:justify-start gap-3 pt-2">
          <Button asChild size="lg" className="shadow-sm">
            <Link href="/backtest" data-testid="btn-home-backtest">
              <Play className="w-4 h-4 mr-2" />
              Launch Backtest Engine
            </Link>
          </Button>
          <Button asChild variant="outline" size="lg" className="shadow-sm">
            <Link href="/sweep" data-testid="btn-home-sweep">
              <Sliders className="w-4 h-4 mr-2" />
              Parameter Sweep
            </Link>
          </Button>
          <Button asChild variant="outline" size="lg" className="shadow-sm">
            <Link href="/reports" data-testid="btn-home-reports">
              <FileText className="w-4 h-4 mr-2" />
              Performance Reports
            </Link>
          </Button>
          <Button asChild variant="ghost" size="lg">
            <Link href="/docs" data-testid="btn-home-docs">
              <BookOpen className="w-4 h-4 mr-2" />
              Documentation
            </Link>
          </Button>
        </div>
      </section>

      {/* Quantitative Core Invariants Bar */}
      <section className="space-y-4">
        <div className="flex items-center justify-between border-b border-slate-200 dark:border-slate-800 pb-2">
          <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-500">
            Institutional Research Guarantees
          </h2>
          <span className="text-xs text-slate-500">PRD Mandated Invariants</span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-4 shadow-sm space-y-1.5">
            <div className="flex items-center space-x-2 text-blue-600 dark:text-blue-400">
              <CheckCircle2 className="w-4 h-4" />
              <h3 className="font-semibold text-sm text-slate-900 dark:text-slate-100">
                Zero Look-Ahead
              </h3>
            </div>
            <p className="text-xs text-slate-600 dark:text-slate-400">
              Indicators evaluate on session <span className="font-mono">T</span> close; trade execution strictly occurs at session <span className="font-mono">T+1</span> Market Open.
            </p>
          </div>

          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-4 shadow-sm space-y-1.5">
            <div className="flex items-center space-x-2 text-emerald-600 dark:text-emerald-400">
              <CheckCircle2 className="w-4 h-4" />
              <h3 className="font-semibold text-sm text-slate-900 dark:text-slate-100">
                Survivorship-Free
              </h3>
            </div>
            <p className="text-xs text-slate-600 dark:text-slate-400">
              Point-in-time constituent membership for NSE 101–750 mid & small caps, eliminating retrospective survivorship bias.
            </p>
          </div>

          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-4 shadow-sm space-y-1.5">
            <div className="flex items-center space-x-2 text-amber-600 dark:text-amber-400">
              <CheckCircle2 className="w-4 h-4" />
              <h3 className="font-semibold text-sm text-slate-900 dark:text-slate-100">
                Top 100 Exclusion
              </h3>
            </div>
            <p className="text-xs text-slate-600 dark:text-slate-400">
              NIFTY 50 acts exclusively as a broader market regime filter. Top 100 large-caps are excluded from trade allocations.
            </p>
          </div>

          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-4 shadow-sm space-y-1.5">
            <div className="flex items-center space-x-2 text-purple-600 dark:text-purple-400">
              <CheckCircle2 className="w-4 h-4" />
              <h3 className="font-semibold text-sm text-slate-900 dark:text-slate-100">
                Gap-Down Realism
              </h3>
            </div>
            <p className="text-xs text-slate-600 dark:text-slate-400">
              Stop-losses below the 7% threshold fill at actual Market Open prices without artificial price smoothing.
            </p>
          </div>
        </div>
      </section>

      {/* 4-Stage Quantitative Workflow Pipeline */}
      <section className="space-y-4">
        <div className="flex items-center justify-between border-b border-slate-200 dark:border-slate-800 pb-2">
          <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-500">
            End-to-End Quantitative Pipeline
          </h2>
          <span className="text-xs text-slate-500">Signal to Settlement</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="relative p-5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm flex flex-col justify-between">
            <div className="space-y-2">
              <div className="w-8 h-8 rounded-lg bg-blue-100 dark:bg-blue-950 text-blue-600 dark:text-blue-400 flex items-center justify-center font-bold text-xs">
                01
              </div>
              <h4 className="font-semibold text-sm text-slate-900 dark:text-slate-100">
                Universe & Regime
              </h4>
              <p className="text-xs text-slate-600 dark:text-slate-400">
                Filters NSE 101–750 constituents against NIFTY 50 200-SMA external regime indicator.
              </p>
            </div>
            <Link
              href="/data"
              className="mt-4 text-xs font-medium text-blue-600 dark:text-blue-400 hover:underline flex items-center"
            >
              Universe Data <ArrowRight className="w-3 h-3 ml-1" />
            </Link>
          </div>

          <div className="relative p-5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm flex flex-col justify-between">
            <div className="space-y-2">
              <div className="w-8 h-8 rounded-lg bg-emerald-100 dark:bg-emerald-950 text-emerald-600 dark:text-emerald-400 flex items-center justify-center font-bold text-xs">
                02
              </div>
              <h4 className="font-semibold text-sm text-slate-900 dark:text-slate-100">
                4-EMA Stack & Trend
              </h4>
              <p className="text-xs text-slate-600 dark:text-slate-400">
                Computes EMA 10, 20, 50, 200 alignment and 1-bar shifted rolling 52-week high levels.
              </p>
            </div>
            <Link
              href="/indicators"
              className="mt-4 text-xs font-medium text-blue-600 dark:text-blue-400 hover:underline flex items-center"
            >
              Inspect Indicators <ArrowRight className="w-3 h-3 ml-1" />
            </Link>
          </div>

          <div className="relative p-5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm flex flex-col justify-between">
            <div className="space-y-2">
              <div className="w-8 h-8 rounded-lg bg-amber-100 dark:bg-amber-950 text-amber-600 dark:text-amber-400 flex items-center justify-center font-bold text-xs">
                03
              </div>
              <h4 className="font-semibold text-sm text-slate-900 dark:text-slate-100">
                Signals & Ranking
              </h4>
              <p className="text-xs text-slate-600 dark:text-slate-400">
                Detects 10/20 crossover entries and prioritizes by (Close - EMA20) / EMA20 descending.
              </p>
            </div>
            <Link
              href="/signals"
              className="mt-4 text-xs font-medium text-blue-600 dark:text-blue-400 hover:underline flex items-center"
            >
              Screen Signals <ArrowRight className="w-3 h-3 ml-1" />
            </Link>
          </div>

          <div className="relative p-5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm flex flex-col justify-between">
            <div className="space-y-2">
              <div className="w-8 h-8 rounded-lg bg-indigo-100 dark:bg-indigo-950 text-indigo-600 dark:text-indigo-400 flex items-center justify-center font-bold text-xs">
                04
              </div>
              <h4 className="font-semibold text-sm text-slate-900 dark:text-slate-100">
                Risk & Backtest
              </h4>
              <p className="text-xs text-slate-600 dark:text-slate-400">
                Applies 2% risk capital sizing, 7% stop-loss discipline, and executes event-driven simulations.
              </p>
            </div>
            <Link
              href="/backtest"
              className="mt-4 text-xs font-medium text-blue-600 dark:text-blue-400 hover:underline flex items-center"
            >
              Run Simulation <ArrowRight className="w-3 h-3 ml-1" />
            </Link>
          </div>
        </div>
      </section>

      {/* Subsystem Modules Grid */}
      <section className="space-y-4">
        <div className="flex items-center justify-between border-b border-slate-200 dark:border-slate-800 pb-2">
          <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-500">
            Platform Subsystems
          </h2>
          <span className="text-xs text-slate-500">Core Engines</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Backtest Engine */}
          <Card className="border-slate-200 dark:border-slate-800 shadow-sm hover:shadow-md transition-shadow">
            <CardHeader className="pb-3">
              <div className="p-2 w-10 h-10 rounded-lg bg-blue-100 dark:bg-blue-950 text-blue-600 dark:text-blue-400 flex items-center justify-center mb-2">
                <Play className="w-5 h-5" />
              </div>
              <CardTitle className="text-base font-semibold">Backtest Simulation</CardTitle>
              <CardDescription className="text-xs">
                Event-driven historical execution with mark-to-market equity curves, trade ledgers, and cash tracking.
              </CardDescription>
            </CardHeader>
            <CardContent className="text-xs text-slate-600 dark:text-slate-400">
              Interactive configuration with custom corpus, slippage, and date range controls.
            </CardContent>
            <CardFooter className="pt-0">
              <Button asChild variant="outline" size="sm" className="w-full text-xs">
                <Link href="/backtest">
                  Open Engine <ArrowRight className="w-3.5 h-3.5 ml-1" />
                </Link>
              </Button>
            </CardFooter>
          </Card>

          {/* Parameter Sweep */}
          <Card className="border-slate-200 dark:border-slate-800 shadow-sm hover:shadow-md transition-shadow">
            <CardHeader className="pb-3">
              <div className="p-2 w-10 h-10 rounded-lg bg-purple-100 dark:bg-purple-950 text-purple-600 dark:text-purple-400 flex items-center justify-center mb-2">
                <Sliders className="w-5 h-5" />
              </div>
              <CardTitle className="text-base font-semibold">Parameter Optimization</CardTitle>
              <CardDescription className="text-xs">
                Cartesian grid parameter sweeps across stop-loss and risk allocations with 2D heatmaps.
              </CardDescription>
            </CardHeader>
            <CardContent className="text-xs text-slate-600 dark:text-slate-400">
              Multi-run comparative overlay charts and differential performance metrics.
            </CardContent>
            <CardFooter className="pt-0">
              <Button asChild variant="outline" size="sm" className="w-full text-xs">
                <Link href="/sweep">
                  Explore Sweeps <ArrowRight className="w-3.5 h-3.5 ml-1" />
                </Link>
              </Button>
            </CardFooter>
          </Card>

          {/* Reports & Analytics */}
          <Card className="border-slate-200 dark:border-slate-800 shadow-sm hover:shadow-md transition-shadow">
            <CardHeader className="pb-3">
              <div className="p-2 w-10 h-10 rounded-lg bg-emerald-100 dark:bg-emerald-950 text-emerald-600 dark:text-emerald-400 flex items-center justify-center mb-2">
                <FileText className="w-5 h-5" />
              </div>
              <CardTitle className="text-base font-semibold">Reports & Analytics</CardTitle>
              <CardDescription className="text-xs">
                Tear sheets featuring CAGR, Sharpe, Sortino, underwater drawdown curves, and monthly heatmaps.
              </CardDescription>
            </CardHeader>
            <CardContent className="text-xs text-slate-600 dark:text-slate-400">
              Multi-format institutional export bundles (PDF, CSV, Excel, and ZIP).
            </CardContent>
            <CardFooter className="pt-0">
              <Button asChild variant="outline" size="sm" className="w-full text-xs">
                <Link href="/reports">
                  View Reports <ArrowRight className="w-3.5 h-3.5 ml-1" />
                </Link>
              </Button>
            </CardFooter>
          </Card>

          {/* Data & Universe */}
          <Card className="border-slate-200 dark:border-slate-800 shadow-sm hover:shadow-md transition-shadow">
            <CardHeader className="pb-3">
              <div className="p-2 w-10 h-10 rounded-lg bg-cyan-100 dark:bg-cyan-950 text-cyan-600 dark:text-cyan-400 flex items-center justify-center mb-2">
                <Database className="w-5 h-5" />
              </div>
              <CardTitle className="text-base font-semibold">Universe & Ingestion</CardTitle>
              <CardDescription className="text-xs">
                Point-in-time constituent membership, coverage diagnostics, and split/bonus adjustments.
              </CardDescription>
            </CardHeader>
            <CardContent className="text-xs text-slate-600 dark:text-slate-400">
              Historical Parquet pricing archives for NSE 101–750 mid & small caps.
            </CardContent>
            <CardFooter className="pt-0">
              <Button asChild variant="outline" size="sm" className="w-full text-xs">
                <Link href="/data">
                  Data Diagnostics <ArrowRight className="w-3.5 h-3.5 ml-1" />
                </Link>
              </Button>
            </CardFooter>
          </Card>

          {/* Risk Engine */}
          <Card className="border-slate-200 dark:border-slate-800 shadow-sm hover:shadow-md transition-shadow">
            <CardHeader className="pb-3">
              <div className="p-2 w-10 h-10 rounded-lg bg-amber-100 dark:bg-amber-950 text-amber-600 dark:text-amber-400 flex items-center justify-center mb-2">
                <Scale className="w-5 h-5" />
              </div>
              <CardTitle className="text-base font-semibold">Risk & Capital Engine</CardTitle>
              <CardDescription className="text-xs">
                Fixed 2% risk capital sizing, 7% stop-loss calculation, and integer share allocations.
              </CardDescription>
            </CardHeader>
            <CardContent className="text-xs text-slate-600 dark:text-slate-400">
              Realistic gap-down loss modeling without artificial price smoothing.
            </CardContent>
            <CardFooter className="pt-0">
              <Button asChild variant="outline" size="sm" className="w-full text-xs">
                <Link href="/risk">
                  Risk Calculator <ArrowRight className="w-3.5 h-3.5 ml-1" />
                </Link>
              </Button>
            </CardFooter>
          </Card>

          {/* Validation & Audit */}
          <Card className="border-slate-200 dark:border-slate-800 shadow-sm hover:shadow-md transition-shadow">
            <CardHeader className="pb-3">
              <div className="p-2 w-10 h-10 rounded-lg bg-indigo-100 dark:bg-indigo-950 text-indigo-600 dark:text-indigo-400 flex items-center justify-center mb-2">
                <ShieldCheck className="w-5 h-5" />
              </div>
              <CardTitle className="text-base font-semibold">Audit & Validation</CardTitle>
              <CardDescription className="text-xs">
                Cryptographic SHA-256 reproducibility, TradingView diffs, and Empyrical validation.
              </CardDescription>
            </CardHeader>
            <CardContent className="text-xs text-slate-600 dark:text-slate-400">
              Verifies calculations against institutional benchmarks to within ±10⁻⁶ precision.
            </CardContent>
            <CardFooter className="pt-0">
              <Button asChild variant="outline" size="sm" className="w-full text-xs">
                <Link href="/validation">
                  Audit Hub <ArrowRight className="w-3.5 h-3.5 ml-1" />
                </Link>
              </Button>
            </CardFooter>
          </Card>
        </div>
      </section>
    </div>
  );
}
