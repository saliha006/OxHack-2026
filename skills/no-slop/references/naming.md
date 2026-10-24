# Naming - detail

Evidence: full-word names beat single letters/abbreviations for comprehension (Hofmeister et al., SANER 2017:
~19% faster defect finding; Schankin et al., ICPC 2018: ~14% faster on semantic defects). But *just making
names longer* does not help - choosing the right concepts does (Feitelson et al., TSE 2021; Alpern et al. 2024).
So: aim for the right concept words, not more words.

## Build a name in three steps (Feitelson model)
1. **Pick the concepts** the reader needs (what it is, its role, its unit if ambiguous).
2. **Pick one word per concept**, using the codebase's existing vocabulary.
3. **Assemble** in the language's convention (snake_case, camelCase, ...).

## Length by scope
| Scope | Guide | Examples |
|---|---|---|
| ≤3-line loop / lambda / math | 1 letter OK | `i`, `x`, `k, v` |
| Local, short function | 1-2 words | `row`, `retry_delay` |
| Function params, fields | 1-3 words, units if ambiguous | `timeout_ms`, `owner_id` |
| Module/public/exported | Full, unambiguous in isolation | `parse_invoice`, `MAX_BATCH_SIZE` |

Context counts as part of the name: `Invoice.total` not `Invoice.invoice_total`; `users.by_email(e)` not
`users.get_user_by_email_address(email_address)`.

## Smells → fixes
| Smell | Example | Fix |
|---|---|---|
| AI-verbose / restates context | `add_two_numbers_together`, `user_list_array` | `add`, `users` |
| Type in name | `name_str`, `items_list` | `name`, `items` |
| Vague noun | `data`, `result`, `info`, `obj`, `manager`, `helper` | what it actually holds: `rows`, `invoice` |
| Cryptic abbreviation | `usrCnt`, `cfgMgr`, `tmp2` | `user_count`, `config` |
| Numbered siblings | `handler2`, `process_new` | name the difference: `retry_handler` |
| Lying name | `get_x` that writes, `is_valid` that throws | rename to the real behaviour |
| Negative boolean | `not_disabled` | `enabled` |
| Synonym drift | `fetch_user` + `load_order` + `get_item` for same op | one verb everywhere |

Keep well-known domain abbreviations (`id`, `url`, `http`, `db`, `ms`) and project conventions.
Renames of public/exported names are interface changes → flag (SKILL §6).
