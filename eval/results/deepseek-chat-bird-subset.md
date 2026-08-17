# QueryAgent Eval Report — public subset

- model: `deepseek-chat`
- cases: 30

## Summary

| metric | value |
|---|---|
| first-execution pass rate | 10/30 (33%) |
| pass rate after self-repair | 14/30 (47%) |
| metric hit rate | n/a |
| clarify-behaviour accuracy | n/a |
| average tool calls | 2.83 |

## Cases

| id | kind | passed | first try | retries | tool calls | note |
|---|---|---|---|---|---|---|
| california_schools_37 | public | ❌ | ❌ | 0 | 5 | result sets differ |
| california_schools_39 | public | ✅ | ❌ | 0 | 4 |  |
| california_schools_41 | public | ❌ | ❌ | 0 | 8 | result sets differ |
| california_schools_45 | public | ✅ | ❌ | 0 | 3 |  |
| card_games_379 | public | ✅ | ✅ | 0 | 3 |  |
| card_games_397 | public | ❌ | ❌ | 0 | 2 | result sets differ |
| card_games_409 | public | ✅ | ✅ | 0 | 1 |  |
| card_games_422 | public | ❌ | ❌ | 0 | 2 | result sets differ |
| card_games_479 | public | ✅ | ✅ | 0 | 1 |  |
| codebase_community_581 | public | ❌ | ❌ | 0 | 1 | result sets differ |
| codebase_community_634 | public | ❌ | ❌ | 0 | 6 | result sets differ |
| codebase_community_640 | public | ❌ | ❌ | 0 | 8 | result sets differ |
| codebase_community_678 | public | ❌ | ❌ | 0 | 1 | result sets differ |
| codebase_community_701 | public | ❌ | ❌ | 0 | 0 | reference expected_sql failed (case bug?): interrupted |
| debit_card_specializing_1484 | public | ❌ | ❌ | 0 | 4 | result sets differ |
| financial_115 | public | ❌ | ❌ | 0 | 5 | result sets differ |
| financial_117 | public | ✅ | ✅ | 0 | 1 |  |
| formula_1_866 | public | ❌ | ❌ | 0 | 5 | result sets differ |
| formula_1_910 | public | ✅ | ✅ | 0 | 1 |  |
| formula_1_940 | public | ✅ | ❌ | 0 | 5 |  |
| formula_1_972 | public | ❌ | ❌ | 1 | 2 | result sets differ |
| formula_1_990 | public | ❌ | ❌ | 0 | 3 | result sets differ |
| student_club_1361 | public | ✅ | ✅ | 0 | 1 |  |
| student_club_1376 | public | ❌ | ❌ | 0 | 1 | result sets differ |
| student_club_1405 | public | ✅ | ✅ | 0 | 2 |  |
| superhero_719 | public | ✅ | ✅ | 0 | 1 |  |
| superhero_733 | public | ✅ | ✅ | 0 | 1 |  |
| superhero_751 | public | ❌ | ❌ | 0 | 1 | result sets differ |
| superhero_758 | public | ✅ | ❌ | 0 | 5 |  |
| thrombosis_prediction_1270 | public | ✅ | ✅ | 0 | 2 |  |
