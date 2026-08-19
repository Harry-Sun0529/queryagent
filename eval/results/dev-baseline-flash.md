# QueryAgent Eval Report — public subset

- model: `deepseek-v4-flash`
- cases: 30

## Summary

| metric | value |
|---|---|
| first-execution pass rate | 7/30 (23%) |
| pass rate after self-repair | 10/30 (33%) |
| metric hit rate | n/a |
| clarify-behaviour accuracy | n/a |
| average tool calls | 3.03 |
| tokens per case (in+out) | 12,441 |
| prompt cache hit rate | 82% |
| latency per case | 13.4s |
| cost per case (upper bound) | $0.0031 |

## Cases

| id | kind | passed | first try | retries | tool calls | note |
|---|---|---|---|---|---|---|
| california_schools_72 | public | ❌ | ❌ | 0 | 5 | result sets differ |
| california_schools_85 | public | ❌ | ❌ | 0 | 3 | result sets differ |
| card_games_345 | public | ❌ | ❌ | 0 | 2 | result sets differ |
| card_games_346 | public | ✅ | ✅ | 0 | 3 |  |
| card_games_358 | public | ❌ | ❌ | 0 | 1 | result sets differ |
| card_games_368 | public | ✅ | ✅ | 0 | 1 |  |
| card_games_407 | public | ❌ | ❌ | 0 | 7 | result sets differ |
| card_games_412 | public | ❌ | ❌ | 0 | 6 | result sets differ |
| card_games_415 | public | ❌ | ❌ | 0 | 3 | result sets differ |
| card_games_480 | public | ❌ | ❌ | 0 | 5 | result sets differ |
| codebase_community_539 | public | ❌ | ❌ | 0 | 1 | result sets differ |
| codebase_community_685 | public | ❌ | ❌ | 1 | 5 | result sets differ |
| codebase_community_707 | public | ❌ | ❌ | 0 | 1 | result sets differ |
| debit_card_specializing_1481 | public | ❌ | ❌ | 0 | 5 | result sets differ |
| european_football_2_1079 | public | ❌ | ❌ | 0 | 1 | result sets differ |
| european_football_2_1134 | public | ✅ | ❌ | 0 | 2 |  |
| financial_128 | public | ✅ | ✅ | 0 | 1 |  |
| financial_169 | public | ❌ | ❌ | 0 | 4 | result sets differ |
| financial_189 | public | ❌ | ❌ | 0 | 8 | result sets differ |
| financial_93 | public | ✅ | ❌ | 0 | 2 |  |
| formula_1_906 | public | ❌ | ❌ | 0 | 5 | result sets differ |
| formula_1_955 | public | ❌ | ❌ | 1 | 5 | result sets differ |
| formula_1_977 | public | ✅ | ✅ | 0 | 1 |  |
| student_club_1317 | public | ✅ | ❌ | 0 | 6 |  |
| student_club_1346 | public | ✅ | ✅ | 0 | 1 |  |
| student_club_1409 | public | ✅ | ✅ | 0 | 1 |  |
| superhero_717 | public | ✅ | ✅ | 0 | 1 |  |
| thrombosis_prediction_1252 | public | ❌ | ❌ | 0 | 1 | result sets differ |
| thrombosis_prediction_1256 | public | ❌ | ❌ | 0 | 3 | result sets differ |
| toxicology_268 | public | ❌ | ❌ | 0 | 1 | result sets differ |
