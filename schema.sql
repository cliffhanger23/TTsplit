-- Run in your own Supabase SQL editor. Never expose the service-role key in GitHub.
create table if not exists public.members (
 email text primary key,
 active boolean not null default true
);
create table if not exists public.matches (
 id uuid primary key default gen_random_uuid(),
 league text not null,
 played_at timestamptz not null,
 player_a text not null,
 player_b text not null,
 set1_a integer not null,
 set1_b integer not null,
 set2_a integer not null,
 set2_b integer not null
);
create table if not exists public.upcoming (
 id uuid primary key default gen_random_uuid(),
 league text not null,
 starts_at timestamptz not null,
 player_a text not null,
 player_b text not null
);
create index if not exists matches_played_at_idx on public.matches (played_at desc);
create index if not exists upcoming_starts_at_idx on public.upcoming (starts_at asc);
alter table public.members enable row level security;
alter table public.matches enable row level security;
alter table public.upcoming enable row level security;
-- No public RLS policies. The Streamlit server uses a service-role key, never a browser key.
