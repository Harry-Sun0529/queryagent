# QueryAgent Eval Report — self-built cases

> 3 轮中的一次代表性结果；跨轮区间见 README。旧的 20 题样本报告已随扩充移除，
> 其数字保留在 CHANGELOG 的历史条目中。

- model: `deepseek-v4-flash`
- cases: 36

## Summary

| metric | value |
|---|---|
| first-execution pass rate | 22/28 (79%) |
| pass rate after self-repair | 27/28 (96%) |
| metric hit rate | 8/8 (100%) |
| clarify-behaviour accuracy | 16/16 (100%) |
| average tool calls | 1.19 |
| tokens per case (in+out) | 3,532 |
| prompt cache hit rate | 85% |
| latency per case | 4.5s |
| cost per case (upper bound) | $0.0009 |
| unmeasured (upstream unreachable) | 0 |

## Cases

| id | kind | passed | first try | retries | tool calls | note |
|---|---|---|---|---|---|---|
| simple_total_users | simple | ✅ | ✅ | 0 | 1 |  |
| simple_channels_list | simple | ✅ | ✅ | 0 | 1 |  |
| simple_paid_orders_30d | simple | ❌ | ❌ | 0 | 5 | result sets differ |
| simple_users_by_region | simple | ✅ | ✅ | 0 | 1 |  |
| simple_max_order_amount | simple | ✅ | ✅ | 0 | 1 |  |
| simple_distinct_skus | simple | ✅ | ✅ | 0 | 1 |  |
| simple_orders_by_status | simple | ✅ | ✅ | 0 | 1 |  |
| simple_users_without_orders | simple | ✅ | ✅ | 0 | 1 |  |
| metric_new_users_registration | metric | ✅ | ✅ | 0 | 1 |  |
| metric_gmv_paid_last_month | metric | ✅ | ✅ | 0 | 1 |  |
| metric_aov_overall | metric | ✅ | ✅ | 0 | 1 |  |
| metric_active_buyers_last_month | metric | ✅ | ❌ | 0 | 2 |  |
| multi_top3_regions_by_paid_amount | multistep | ✅ | ✅ | 0 | 1 |  |
| multi_channel_user_ranking | multistep | ✅ | ❌ | 0 | 3 |  |
| multi_daily_new_users_last_month | multistep | ✅ | ✅ | 0 | 1 |  |
| multi_ads_share_of_paid_amount | multistep | ✅ | ✅ | 0 | 1 |  |
| clarify_new_users_ambiguous | clarify | ✅ | ✅ | 0 | 0 |  |
| clarify_gmv_ambiguous | clarify | ✅ | ✅ | 0 | 0 |  |
| no_clarify_disambiguated_new_users | no_clarify | ✅ | ✅ | 0 | 1 |  |
| no_clarify_plain_order_count | no_clarify | ✅ | ❌ | 0 | 3 |  |
| metric_refund_rate_by_count | metric | ✅ | ✅ | 0 | 1 |  |
| metric_repurchase_full_period | metric | ✅ | ✅ | 0 | 1 |  |
| metric_gmv_by_region_paid | metric | ✅ | ✅ | 0 | 1 |  |
| metric_new_users_by_channel_registration | metric | ✅ | ❌ | 0 | 4 |  |
| clarify_aov_ambiguous | clarify | ✅ | ✅ | 0 | 0 |  |
| clarify_active_buyers_ambiguous | clarify | ✅ | ✅ | 0 | 0 |  |
| clarify_refund_rate_ambiguous | clarify | ✅ | ✅ | 0 | 0 |  |
| clarify_repurchase_ambiguous | clarify | ✅ | ✅ | 0 | 0 |  |
| clarify_new_users_by_channel | clarify | ✅ | ✅ | 0 | 0 |  |
| clarify_gmv_reconciliation | clarify | ✅ | ✅ | 0 | 0 |  |
| no_clarify_aov_by_order | no_clarify | ✅ | ✅ | 0 | 1 |  |
| no_clarify_refund_by_order_count | no_clarify | ✅ | ✅ | 0 | 1 |  |
| no_clarify_active_buyers_paid_only | no_clarify | ✅ | ❌ | 0 | 4 |  |
| no_clarify_region_lookup | no_clarify | ✅ | ✅ | 0 | 1 |  |
| no_clarify_sku_count | no_clarify | ✅ | ✅ | 0 | 1 |  |
| no_clarify_max_amount | no_clarify | ✅ | ✅ | 0 | 1 |  |

## Failing cases — SQL comparison

### simple_paid_orders_30d

- question: 已支付订单里，最后一笔订单往前 30 天内（含当天）一共有多少笔已支付订单？
- expected: `SELECT count(*) FROM orders WHERE status = 'paid' AND created_at >= datetime((SELECT max(created_at) FROM orders), '-30 day')`
- agent: `SELECT DATE(MAX(created_at)) AS last_date, DATE(MAX(created_at), '-30 days') AS window_start FROM orders WHERE status = 'paid';`

