import type { Method } from "./types";

export interface SampleIncident {
  id: string;
  label: string;
  problem: string;
  context: string;
  severity: "low" | "medium" | "high" | "critical";
  systemArea: string;
  method: Method;
  compareMethod?: Method;
}

export const SAMPLE_INCIDENTS: SampleIncident[] = [
  {
    id: "sso-cert-rotation",
    label: "SSO certificate rotation failures",
    problem: "Enterprise SSO logins are failing for multiple tenants after the identity provider rotated its SAML signing certificate.",
    context:
      "Symptoms: about 22% of SAML assertions rejected with signature validation errors; only tenants on the rotated IdP are affected; direct password login is unaffected. Evidence available: sso-gateway error logs, IdP rotation change ticket, federation metadata cache age metric, and tenant-level failure breakdown.",
    severity: "high",
    systemArea: "Identity & Access",
    method: "five_why",
    compareMethod: "fault_tree",
  },
  {
    id: "redis-session-evictions",
    label: "Random user logouts from Redis evictions",
    problem: "Logged-in users are randomly logged out during business hours after a recommendations feature launch.",
    context:
      "Symptoms: re-login rate is 6x baseline, Redis evicted_keys is climbing, and memory is pinned at maxmemory. The new feature stores large per-user payloads in the shared session Redis cluster. Evidence available: Redis INFO memory, keyspace size by prefix, deployment timeline, and re-login dashboard.",
    severity: "medium",
    systemArea: "Caching",
    method: "fishbone",
    compareMethod: "five_why",
  },
  {
    id: "payment-duplicate-captures",
    label: "Duplicate payment captures during slowness",
    problem: "A small number of customers were charged twice for one order during a period of gateway slowness.",
    context:
      "Symptoms: 41 duplicate captures over two hours; gateway p99 rose above 8 seconds; duplicates correlate with client-side retry log entries. Evidence available: gateway capture logs with request IDs, payment-service retry logs, reconciliation report, and gateway latency dashboard.",
    severity: "critical",
    systemArea: "Checkout & Payments",
    method: "fault_tree",
    compareMethod: "five_why",
  },
  {
    id: "kafka-hot-partition",
    label: "Kafka consumer lag from hot partition",
    problem: "Downstream order analytics and customer notifications are delayed by up to 45 minutes during a flash sale.",
    context:
      "Symptoms: consumer lag is concentrated on partitions 7 and 12 of the order-events topic; one merchant generated about 60% of traffic; remaining partitions show near-zero lag. Evidence available: per-partition lag graphs, message key distribution sample, consumer throughput metrics, and campaign schedule.",
    severity: "high",
    systemArea: "Event Streaming",
    method: "fault_tree",
    compareMethod: "fishbone",
  },
  {
    id: "blocking-index-migration",
    label: "Checkout timeouts after DB migration",
    problem: "Checkout requests timed out for 12 minutes during a scheduled release window after a database migration ran.",
    context:
      "Symptoms: pg_locks showed an ACCESS EXCLUSIVE lock on the orders table; active queries queued behind CREATE INDEX; checkout p99 exceeded 30 seconds and requests hit 504. Evidence available: pg_locks, pg_stat_activity, migration SQL diff, checkout latency dashboard, and deploy timestamp correlation.",
    severity: "critical",
    systemArea: "Database",
    method: "five_why",
    compareMethod: "fishbone",
  },
];
