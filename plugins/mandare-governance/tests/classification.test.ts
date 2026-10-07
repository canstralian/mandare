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
