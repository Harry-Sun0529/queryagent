# QueryAgent Eval Report — self-built cases

> 3 次连续运行中的一次代表性结果；跨运行区间见 [dual-model-analysis.md](dual-model-analysis.md)。DeepSeek 不提供 sampling seed，temperature 0 亦非逐比特确定。

- model: `deepseek-v4-flash`
- cases: 20

## Summary

| metric | value |
|---|---|
| first-execution pass rate | 13/18 (72%) |
| pass rate after self-repair | 18/18 (100%) |
| metric hit rate | 2/4 (50%) |
| clarify-behaviour accuracy | 4/4 (100%) |
| average tool calls | 1.30 |
| tokens per case (in+out) | 3,210 |
| prompt cache hit rate | 90% |
| latency per case | 3.9s |
| cost per case (upper bound) | $0.0007 |

## Cases

| id | kind | passed | first try | retries | tool calls | note |
|---|---|---|---|---|---|---|
| simple_total_users | simple | ✅ | ✅ | 0 | 1 |  |
| simple_channels_list | simple | ✅ | ✅ | 0 | 1 |  |
| simple_paid_orders_30d | simple | ✅ | ❌ | 0 | 4 |  |
| simple_users_by_region | simple | ✅ | ✅ | 0 | 1 |  |
| simple_max_order_amount | simple | ✅ | ✅ | 0 | 1 |  |
| simple_distinct_skus | simple | ✅ | ✅ | 0 | 1 |  |
| simple_orders_by_status | simple | ✅ | ✅ | 0 | 1 |  |
| simple_users_without_orders | simple | ✅ | ✅ | 0 | 1 |  |
| metric_new_users_registration | metric | ✅ | ✅ | 0 | 1 |  |
| metric_gmv_paid_last_month | metric | ✅ | ❌ | 0 | 2 |  |
| metric_aov_overall | metric | ✅ | ✅ | 0 | 1 |  |
| metric_active_buyers_last_month | metric | ✅ | ❌ | 0 | 2 |  |
| multi_top3_regions_by_paid_amount | multistep | ✅ | ✅ | 0 | 1 |  |
| multi_channel_user_ranking | multistep | ✅ | ❌ | 0 | 3 |  |
| multi_daily_new_users_last_month | multistep | ✅ | ✅ | 0 | 1 |  |
| multi_ads_share_of_paid_amount | multistep | ✅ | ✅ | 0 | 1 |  |
| clarify_new_users_ambiguous | clarify | ✅ | ✅ | 0 | 0 |  |
| clarify_gmv_ambiguous | clarify | ✅ | ✅ | 0 | 0 |  |
| no_clarify_disambiguated_new_users | no_clarify | ✅ | ✅ | 0 | 1 |  |
| no_clarify_plain_order_count | no_clarify | ✅ | ❌ | 0 | 2 |  |
