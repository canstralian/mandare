import { expect, test } from 'claude-code/testing'
import { Effect, classifyBash, classifyMcp, classifyToolCall } from '../hooks/classify-effect.js'

test('classifies known read and local tools without widening authority', async () => {
  expect(classifyToolCall('Read', { file_path: 'README.md' })).toBe(Effect.READ)
  expect(classifyToolCall('Edit', { file_path: 'README.md' })).toBe(Effect.LOCAL_WRITE)
  expect(classifyToolCall('WebFetch', { url: 'https://example.test' })).toBe(Effect.NETWORK_READ)
})

test('classifies bash external writes and destructive commands', async () => {
  expect(classifyBash('git push origin feature/mod')).toBe(Effect.EXTERNAL_WRITE)
  expect(classifyBash('git push --force origin main')).toBe(Effect.DESTRUCTIVE)
  expect(classifyBash('rm -rf build')).toBe(Effect.DESTRUCTIVE)
  expect(classifyBash('pytest -q')).toBe(Effect.LOCAL_EXECUTION)
})

test('classifies MCP mutation verbs and denies unknown operations by default', async () => {
  expect(classifyMcp('mcp__GitHub__fetch_file')).toBe(Effect.NETWORK_READ)
  expect(classifyMcp('mcp__GitHub__create_pull_request')).toBe(Effect.EXTERNAL_WRITE)
  expect(classifyMcp('mcp__GitHub__delete_file')).toBe(Effect.DESTRUCTIVE)
  expect(classifyMcp('mcp__new-server__teleport')).toBe(Effect.UNKNOWN)
})

test('classifies force, deletion and mirror pushes as destructive', async () => {
  for (const command of [
    'git push -fu origin main',
    'git push origin +main:main',
    'git push --force-with-lease=main:abc123 origin main',
    'git push origin --delete old-branch',
    'git push origin :old-branch',
    'git push --mirror backup',
  ]) {
    expect(classifyBash(command)).toBe(Effect.DESTRUCTIVE)
  }
  expect(classifyBash('git push origin my-fix')).toBe(Effect.EXTERNAL_WRITE)
  expect(classifyBash('git push --follow-tags origin v1')).toBe(Effect.EXTERNAL_WRITE)
})

test('classifies network mutation spellings as external writes, plain fetches as reads', async () => {
  for (const command of [
    'curl -d x=1 https://api.example.test',
    'curl -sS --data-binary @body.json https://api.example.test',
    'curl -F file=@a.txt https://api.example.test',
    'curl --json {} https://api.example.test',
    'curl -XPOST https://api.example.test',
    'curl --request=DELETE https://api.example.test/x',
    'wget --post-data a=1 https://api.example.test',
    'gh api repos/o/r/issues -f title=t',
    'gh api -X PATCH repos/o/r',
    'gh api --method=DELETE repos/o/r/git/refs/heads/x',
  ]) {
    expect(classifyBash(command)).toBe(Effect.EXTERNAL_WRITE)
  }
  expect(classifyBash('curl -sSfL -o out.tgz https://example.test/a.tgz')).toBe(Effect.NETWORK_READ)
  expect(classifyBash('gh api repos/o/r')).toBe(Effect.NETWORK_READ)
  expect(classifyBash('gh api -X GET search/issues -f q=bug')).toBe(Effect.NETWORK_READ)
})

test('maps this build\'s read-only built-ins and keeps every other unmapped tool unknown', async () => {
  expect(classifyToolCall('ToolSearch', { query: 'x' })).toBe(Effect.READ)
  expect(classifyToolCall('ReadMcpResourceTool', { server: 's', uri: 'u' })).toBe(Effect.NETWORK_READ)
  expect(classifyToolCall('ListMcpResourcesTool', {})).toBe(Effect.NETWORK_READ)
  for (const tool of ['SendMessage', 'Artifact', 'PushNotification', 'RemoteTrigger', 'PublishPlugin']) {
    expect(classifyToolCall(tool, {})).toBe(Effect.UNKNOWN)
  }
  expect(classifyMcp('mcp__github__pull_request_read')).toBe(Effect.NETWORK_READ)
  expect(classifyMcp('mcp__github__request_copilot_review')).toBe(Effect.UNKNOWN)
})

test('preserves quoted and escaped Git directory arguments before classifying pushes', async () => {
  for (const command of [
    'git -C "my repo" push origin main',
    "git -C 'my repo' push origin main",
    'git -C my\\ repo push origin main',
    'git -c "user.name=My Name" push origin main',
  ]) {
    expect(classifyBash(command)).toBe(Effect.EXTERNAL_WRITE)
  }
  expect(classifyBash('git -C "my repo" push --force origin main')).toBe(Effect.DESTRUCTIVE)
})

test('keeps literal separators inside Git option arguments in one shell word', async () => {
  for (const directory of ['my;repo', 'my|repo', 'my&repo', 'my(repo)', 'my`repo', 'my{repo}', 'my\nrepo']) {
    expect(classifyBash(`git -C '${directory}' push origin main`)).toBe(Effect.EXTERNAL_WRITE)
    expect(classifyBash(`git -C '${directory}' push --force origin main`)).toBe(Effect.DESTRUCTIVE)
  }
  for (const directory of ['my\\;repo', 'my\\|repo', 'my\\&repo', 'my\\(repo\\)', 'my\\`repo', 'my\\{repo\\}']) {
    expect(classifyBash(`git -C ${directory} push origin main`)).toBe(Effect.EXTERNAL_WRITE)
  }
})

test('preserves empty option values and quoted command strings', async () => {
  for (const value of ['""', "''"]) {
    expect(classifyBash(`git --namespace ${value} push origin main`)).toBe(Effect.EXTERNAL_WRITE)
    expect(classifyBash(`git --namespace ${value} push --force origin main`)).toBe(Effect.DESTRUCTIVE)
  }
  expect(classifyBash("bash -c 'git -C \"my repo\" push origin main'")).toBe(Effect.EXTERNAL_WRITE)
  expect(classifyBash("bash -c 'git status; git push --force origin main'")).toBe(Effect.DESTRUCTIVE)
  expect(classifyBash('git sta\\\ntus; git pu\\\nsh origin main')).toBe(Effect.EXTERNAL_WRITE)
  expect(classifyBash("git -C 'my\\repo' push origin main")).toBe(Effect.EXTERNAL_WRITE)
})

test('keeps real separators and fails closed on incomplete shell words', async () => {
  expect(classifyBash('git status; git push origin main')).toBe(Effect.EXTERNAL_WRITE)
  expect(classifyBash('git status | git push --force origin main')).toBe(Effect.DESTRUCTIVE)
  expect(classifyBash('git -C "unfinished push origin main')).toBe(Effect.UNKNOWN)
  expect(classifyBash('git push origin main' + '\\')).toBe(Effect.UNKNOWN)
  let nested = 'git push origin main'
  for (let depth = 0; depth < 6; depth += 1) nested = 'bash -c ' + JSON.stringify(nested)
  expect(classifyBash(nested)).toBe(Effect.UNKNOWN)
})

test('requires approval for unsupported active command substitutions', async () => {
  for (const command of [
    'git -C "$(printf "%s" "my;repo")" push origin main',
    'git -C "$(printf "%s" "my;repo")" push --force origin main',
    'git -C $(printf "%s" "my;repo") push origin main',
    'git -C "`printf "%s" "my;repo"`" push origin main',
    'echo "$(git push origin main)"',
    "sh -c 'git -C \"$(printf \"%s\" \"my;repo\")\" push origin main'",
    'git -C "$((1 + $(printf 1)))" push origin main',
    'git -C "$\\\n(printf "%s" "my;repo")" push origin main',
  ]) expect(classifyBash(command)).toBe(Effect.UNKNOWN)
  expect(classifyBash("git -C '$(literal)' push origin main")).toBe(Effect.EXTERNAL_WRITE)
  expect(classifyBash('git -C "\\$(literal)" push origin main')).toBe(Effect.EXTERNAL_WRITE)
  expect(classifyBash('git -C "my\\`repo" push origin main')).toBe(Effect.EXTERNAL_WRITE)
})

test('requires approval for env split-string spellings without interpreting their grammar', async () => {
  for (const command of [
    'env -S \'"git"\' push origin main',
    'env -S \'"git"\' push --force origin main',
    'env -S\'"git"\' push origin main',
    '/usr/bin/env --split-string \'"git"\' push origin main',
    'env --split-string=\'"git"\' push --force origin main',
    'env --split=\'"git"\' push origin main',
    'env -iS \'"git"\' push origin main',
    "env -S 'git\\_push\\_origin\\_main'",
    "bash -c 'env -S \"git push origin main\"'",
  ]) expect(classifyBash(command)).toBe(Effect.UNKNOWN)
  expect(classifyBash('env LANG=C git push origin main')).toBe(Effect.EXTERNAL_WRITE)
  expect(classifyBash('env LANG=C git status')).toBe(Effect.LOCAL_EXECUTION)
  expect(classifyBash('env LANG=C git status --short')).toBe(Effect.LOCAL_EXECUTION)
  expect(classifyBash('env LANG=C git log --since=2026-01-01')).toBe(Effect.LOCAL_EXECUTION)
  expect(classifyBash('env -- git status --short')).toBe(Effect.LOCAL_EXECUTION)
  expect(classifyBash('env -u S git status --short')).toBe(Effect.LOCAL_EXECUTION)
  expect(classifyBash('env -uS git status --short')).toBe(Effect.LOCAL_EXECUTION)
  expect(classifyBash('env -C "my repo\'s copy" git status --short')).toBe(Effect.LOCAL_EXECUTION)
})

test('keeps literal operands out of recursive shell parsing', async () => {
  for (const command of [
    'git commit -m "fix: don\'t break quoting"',
    'git -C "my repo\'s copy" status',
    'git -C "my repo\'s copy" commit -m "it\'s fine; keep (literal) syntax"',
    'printf "%s" "an unmatched \' is literal"',
    "bash -c 'git status' \"my repo's copy\"",
  ]) expect(classifyBash(command)).toBe(Effect.LOCAL_EXECUTION)
  expect(classifyBash('git -C "my repo\'s copy" push origin main')).toBe(Effect.EXTERNAL_WRITE)
  expect(classifyBash('git -C "my repo\'s copy" push --force origin main')).toBe(Effect.DESTRUCTIVE)
})

test('inspects recognized shell command operands with a bounded depth', async () => {
  for (const shell of ['sh', 'bash', 'dash', 'ash', 'ksh', 'zsh', '/bin/bash']) {
    for (const options of ['-c', '-lc', '-xc', '+c', '-o pipefail -c']) {
      expect(classifyBash(shell + ' ' + options + " 'git push origin main'")).toBe(Effect.EXTERNAL_WRITE)
    }
  }
  expect(classifyBash("bash --noprofile --norc -c 'git push --force origin main'")).toBe(Effect.DESTRUCTIVE)
  expect(classifyBash("bash -c 'git -C \"my repo\" push origin main'")).toBe(Effect.EXTERNAL_WRITE)
  expect(classifyBash("bash -c 'git -C \"unfinished'")).toBe(Effect.UNKNOWN)
  expect(classifyBash('bash -c')).toBe(Effect.UNKNOWN)
  expect(classifyBash("bash -c -- 'git push origin main'")).toBe(Effect.UNKNOWN)
  expect(classifyBash("bash -c +x 'git push origin main'")).toBe(Effect.UNKNOWN)
})

test('keeps opaque executable string consumers behind live approval', async () => {
  for (const command of [
    "eval 'git push origin main'",
    "ssh host 'git push origin main'",
    'python -c \'import os; os.system("git push origin main")\'',
    'python3 -c \'import os; os.system("git push origin main")\'',
    'python3.12 -c \'import os; os.system("git push origin main")\'',
    "bash -c 'eval \"git push origin main\"'",
  ]) expect(classifyBash(command)).toBe(Effect.UNKNOWN)
  expect(classifyBash('python3 -m pytest -q')).toBe(Effect.LOCAL_EXECUTION)
})
