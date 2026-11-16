# Review Checklist

## Correctness

- Off-by-one errors in loops, slices, and pagination.
- Null/undefined/empty-collection handling on new paths.
- Error paths: is every thrown error caught, logged, or propagated deliberately?
- Async: missing `await`, unhandled promise rejections, race conditions.

## Regressions

- Are existing callers of a changed function still correct?
- Do default parameter or return-shape changes break consumers?
- Are migrations or schema changes backward compatible?

## Security

- Input validated before use in queries, shell commands, or file paths.
- No secrets, tokens, or credentials committed or logged.
- Authorization checked on new endpoints and actions.

## Resource use

- Files, sockets, cursors, and subscriptions closed on every path.
- No unbounded growth in caches, listeners, or in-memory collections.

## Tests

- Does the change include a test that fails without the fix?
- Are new branches covered, including the failure branches?

## Consistency

- Naming, structure, and error style match the surrounding code.
- No dead code, commented-out blocks, or leftover debug output.
