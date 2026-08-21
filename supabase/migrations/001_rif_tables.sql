-- RIF Runtime evidence schema
-- Apply with: supabase db push  (or paste into the Supabase SQL editor)
--
-- Architecture:
--   identities       — one row per authenticated user (maps Supabase auth.users)
--   execution_runs   — one row per governed run created by POST /v1/runs
--   evidence_ledger  — append-only audit rows produced by the RIF Runtime
--   state_log        — runtime posture / lifecycle events per identity

-- ── identities ────────────────────────────────────────────────────────────────
-- Mirrors auth.users so foreign keys can reference it without crossing schemas.
create table if not exists public.identities (
    id         uuid        primary key,
    created_at timestamptz not null default now()
);

-- Populate automatically when a new user signs up.
create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer set search_path = public
as $$
begin
    insert into public.identities (id) values (new.id)
    on conflict (id) do nothing;
    return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
    after insert on auth.users
    for each row execute procedure public.handle_new_user();

-- ── execution_runs ────────────────────────────────────────────────────────────
-- One row per call to POST /v1/runs.
create table if not exists public.execution_runs (
    run_id      uuid        primary key,
    identity_id uuid        not null references public.identities (id),
    status      text        not null,
    prompt      text        not null default '',
    created_at  timestamptz not null default now(),
    updated_at  timestamptz not null default now()
);

create index if not exists idx_execution_runs_identity
    on public.execution_runs (identity_id, created_at desc);

-- ── evidence_ledger ───────────────────────────────────────────────────────────
-- Append-only: the RIF Runtime writes here for every governance event.
-- Rows are never updated or deleted; a new row supersedes the previous one.
create table if not exists public.evidence_ledger (
    id          bigint      generated always as identity primary key,
    run_id      uuid        not null references public.execution_runs (run_id),
    kind        text        not null,   -- e.g. 'policy_decision', 'agent_output'
    payload     jsonb       not null,
    created_at  timestamptz not null default now()
);

create index if not exists idx_evidence_ledger_run
    on public.evidence_ledger (run_id, created_at);

-- ── state_log ─────────────────────────────────────────────────────────────────
-- Runtime lifecycle events (posture transitions, environment changes, etc.)
-- that are not tied to a specific run.
create table if not exists public.state_log (
    id          bigint      generated always as identity primary key,
    identity_id uuid        not null references public.identities (id),
    event       text        not null,
    payload     jsonb,
    created_at  timestamptz not null default now()
);

create index if not exists idx_state_log_identity
    on public.state_log (identity_id, created_at desc);

-- ── Row-Level Security ────────────────────────────────────────────────────────
-- Users see only their own rows; the service-role key (used by RIF Runtime)
-- bypasses RLS for evidence writes.

alter table public.identities       enable row level security;
alter table public.execution_runs   enable row level security;
alter table public.evidence_ledger  enable row level security;
alter table public.state_log        enable row level security;

-- identities: each user can read their own row.
create policy "users read own identity"
    on public.identities for select
    using (auth.uid() = id);

-- execution_runs: each user can read their own runs; only the service role
-- can insert/update (done via RIF Runtime with service_role key).
create policy "users read own runs"
    on public.execution_runs for select
    using (auth.uid() = identity_id);

-- evidence_ledger: each user can read evidence for their own runs.
create policy "users read own evidence"
    on public.evidence_ledger for select
    using (
        exists (
            select 1 from public.execution_runs r
            where r.run_id = evidence_ledger.run_id
              and r.identity_id = auth.uid()
        )
    );

-- state_log: each user can read their own state events.
create policy "users read own state"
    on public.state_log for select
    using (auth.uid() = identity_id);
