```markdown
# rif-runtime Development Patterns

> Auto-generated skill from repository analysis

## Overview
This skill teaches you the core development patterns and conventions used in the `rif-runtime` TypeScript codebase. You'll learn about file naming, import/export styles, commit message conventions, and how to write and run tests. This guide ensures consistency and maintainability when contributing to the repository.

## Coding Conventions

### File Naming
- Use **camelCase** for all file names.
  - Example: `myModule.ts`, `userService.test.ts`

### Import Style
- Use **relative imports** for all internal modules.
  - Example:
    ```typescript
    import { myFunction } from './utils';
    ```

### Export Style
- Use **named exports** rather than default exports.
  - Example:
    ```typescript
    // utils.ts
    export function myFunction() { ... }
    ```

### Commit Message Convention
- Follow the **conventional commit** format.
- Use the `fix` prefix for bug fixes.
  - Example: `fix: correct user authentication logic`
- Average commit message length is around 54 characters.

## Workflows

### Bug Fix Workflow
**Trigger:** When you need to fix a bug in the codebase  
**Command:** `/fix-bug`

1. Create a new branch for your fix.
2. Make the necessary code changes.
3. Write or update tests in a file matching `*.test.*`.
4. Commit your changes using the `fix:` prefix in the commit message.
   - Example: `fix: handle null values in data parser`
5. Push your branch and open a pull request.

## Testing Patterns

- Test files follow the `*.test.*` naming convention.
  - Example: `userService.test.ts`
- The testing framework is **unknown**, so check existing test files for patterns.
- Place related tests alongside the code they test, using the same camelCase naming.

#### Example Test File
```typescript
// mathUtils.test.ts
import { add } from './mathUtils';

describe('add', () => {
  it('should add two numbers', () => {
    expect(add(2, 3)).toBe(5);
  });
});
```

## Commands
| Command    | Purpose                          |
|------------|----------------------------------|
| /fix-bug   | Start the bug fix workflow       |
```
