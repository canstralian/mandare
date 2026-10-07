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
