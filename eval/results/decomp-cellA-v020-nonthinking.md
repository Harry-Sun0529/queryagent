# QueryAgent Eval Report — self-built cases

- model: `deepseek-chat`
- cases: 20

## Summary

| metric | value |
|---|---|
| first-execution pass rate | 14/18 (78%) |
| pass rate after self-repair | 16/18 (89%) |
| metric hit rate | 4/4 (100%) |
| clarify-behaviour accuracy | 4/4 (100%) |
| average tool calls | 1.40 |

## Cases

| id | kind | passed | first try | retries | tool calls | note |
|---|---|---|---|---|---|---|
| simple_total_users | simple | ✅ | ✅ | 0 | 1 |  |
| simple_channels_list | simple | ✅ | ✅ | 0 | 1 |  |
| simple_paid_orders_30d | simple | ❌ | ❌ | 0 | 4 | result sets differ |
| simple_users_by_region | simple | ✅ | ✅ | 0 | 1 |  |
| simple_max_order_amount | simple | ✅ | ✅ | 0 | 1 |  |
| simple_distinct_skus | simple | ✅ | ✅ | 0 | 1 |  |
| simple_orders_by_status | simple | ✅ | ✅ | 0 | 1 |  |
| simple_users_without_orders | simple | ✅ | ✅ | 0 | 1 |  |
| metric_new_users_registration | metric | ✅ | ✅ | 0 | 1 |  |
| metric_gmv_paid_last_month | metric | ✅ | ✅ | 0 | 1 |  |
| metric_aov_overall | metric | ✅ | ✅ | 0 | 1 |  |
| metric_active_buyers_last_month | metric | ✅ | ❌ | 0 | 3 |  |
| multi_top3_regions_by_paid_amount | multistep | ✅ | ✅ | 0 | 1 |  |
| multi_channel_user_ranking | multistep | ✅ | ❌ | 0 | 3 |  |
| multi_daily_new_users_last_month | multistep | ✅ | ✅ | 0 | 2 |  |
| multi_ads_share_of_paid_amount | multistep | ❌ | ❌ | 0 | 3 | result sets differ |
| clarify_new_users_ambiguous | clarify | ✅ | ✅ | 0 | 0 |  |
| clarify_gmv_ambiguous | clarify | ✅ | ✅ | 0 | 0 |  |
| no_clarify_disambiguated_new_users | no_clarify | ✅ | ✅ | 0 | 1 |  |
| no_clarify_plain_order_count | no_clarify | ✅ | ✅ | 0 | 1 |  |
