# QueryAgent Eval Report — self-built cases

- model: `deepseek-v4-flash`
- cases: 36
- scoring: v2 (query trajectory and completion reported separately)
- Natural-language answer correctness is not measured.

## Summary

| metric | value |
|---|---|
| first-execution pass rate | 20/28 (71%) |
| query-trajectory hit rate | 25/28 (89%) |
| completed with SQL hit | 24/28 (86%) |
| metric hit rate | 6/8 (75%) |
| clarify-behaviour accuracy | 16/16 (100%) |
| average tool calls | 1.11 |
| tokens per case (in+out) | 3,722 |
| prompt cache hit rate | 84% |
| latency per case | 4.9s |
| cost per case (upper bound) | $0.0010 |
| unmeasured (upstream unreachable) | 0 |

## Cases

| id | kind | SQL hit | first try | retries | tool calls | note |
|---|---|---|---|---|---|---|
| simple_total_users | simple | ✅ | ✅ | 0 | 1 |  |
| simple_channels_list | simple | ✅ | ✅ | 0 | 1 |  |
| simple_paid_orders_30d | simple | ❌ | ❌ | 0 | 5 | result sets differ |
| simple_users_by_region | simple | ✅ | ✅ | 0 | 1 |  |
| simple_max_order_amount | simple | ✅ | ✅ | 0 | 1 |  |
| simple_distinct_skus | simple | ✅ | ✅ | 0 | 1 |  |
| simple_orders_by_status | simple | ✅ | ✅ | 0 | 1 |  |
| simple_users_without_orders | simple | ❌ | ❌ | 0 | 1 | result sets differ |
| metric_new_users_registration | metric | ✅ | ✅ | 0 | 1 |  |
| metric_gmv_paid_last_month | metric | ✅ | ❌ | 0 | 2 |  |
| metric_aov_overall | metric | ✅ | ✅ | 0 | 1 |  |
| metric_active_buyers_last_month | metric | ✅ | ❌ | 0 | 2 |  |
| multi_top3_regions_by_paid_amount | multistep | ✅ | ✅ | 0 | 1 |  |
| multi_channel_user_ranking | multistep | ✅ | ❌ | 0 | 2 |  |
| multi_daily_new_users_last_month | multistep | ✅ | ✅ | 0 | 2 | multiple SQL statements are not allowed (2 found); send exactly one SELECT |
| multi_ads_share_of_paid_amount | multistep | ✅ | ✅ | 0 | 1 |  |
| clarify_new_users_ambiguous | clarify | ✅ | ✅ | 0 | 0 |  |
| clarify_gmv_ambiguous | clarify | ✅ | ✅ | 0 | 0 |  |
| no_clarify_disambiguated_new_users | no_clarify | ✅ | ✅ | 0 | 1 |  |
| no_clarify_plain_order_count | no_clarify | ✅ | ❌ | 0 | 3 |  |
| metric_refund_rate_by_count | metric | ✅ | ✅ | 0 | 1 |  |
| metric_repurchase_full_period | metric | ❌ | ❌ | 0 | 1 | result sets differ |
| metric_gmv_by_region_paid | metric | ✅ | ✅ | 0 | 1 |  |
| metric_new_users_by_channel_registration | metric | ✅ | ✅ | 0 | 1 |  |
| clarify_aov_ambiguous | clarify | ✅ | ✅ | 0 | 0 |  |
| clarify_active_buyers_ambiguous | clarify | ✅ | ✅ | 0 | 0 |  |
| clarify_refund_rate_ambiguous | clarify | ✅ | ✅ | 0 | 0 |  |
| clarify_repurchase_ambiguous | clarify | ✅ | ✅ | 0 | 0 |  |
| clarify_new_users_by_channel | clarify | ✅ | ✅ | 0 | 0 |  |
| clarify_gmv_reconciliation | clarify | ✅ | ✅ | 0 | 0 |  |
| no_clarify_aov_by_order | no_clarify | ✅ | ✅ | 0 | 1 |  |
| no_clarify_refund_by_order_count | no_clarify | ✅ | ✅ | 0 | 1 |  |
| no_clarify_active_buyers_paid_only | no_clarify | ✅ | ❌ | 0 | 3 |  |
| no_clarify_region_lookup | no_clarify | ✅ | ✅ | 0 | 1 |  |
| no_clarify_sku_count | no_clarify | ✅ | ✅ | 0 | 1 |  |
| no_clarify_max_amount | no_clarify | ✅ | ✅ | 0 | 1 |  |

## Failing cases — SQL comparison

### simple_paid_orders_30d

- question: 已支付订单里，最后一笔订单往前 30 天内（含当天）一共有多少笔已支付订单？
- expected: `SELECT count(*) FROM orders WHERE status = 'paid' AND created_at >= datetime((SELECT max(created_at) FROM orders), '-30 day')`
- agent: `WITH last_paid AS ( SELECT date(MAX(created_at)) AS last_day FROM orders WHERE status = 'paid' ) SELECT last_day, (SELECT COUNT(*) FROM orders WHERE status = 'paid' AND date(created_at) BETWEEN date(last_day, '-29 days') AND last_day) AS cnt_30d, (SELECT COUNT(*) FROM orders WHERE status = 'paid' AND date(created_at) BETWEEN date(last_day, '-30 days') AND last_day) AS cnt_31d FROM last_paid`

### simple_users_without_orders

- question: 有多少用户从来没有下过单？
- expected: `SELECT count(*) FROM users WHERE first_order_at IS NULL`
- agent: `SELECT (SELECT COUNT(*) FROM users WHERE first_order_at IS NULL) AS null_first_order, (SELECT COUNT(*) FROM users u WHERE NOT EXISTS (SELECT 1 FROM orders o WHERE o.user_id = u.id)) AS no_orders, (SELECT COUNT(*) FROM users) AS total_users, (SELECT COUNT(DISTINCT user_id) FROM orders) AS users_with_orders`

### metric_repurchase_full_period

- question: 按全期口径，复购率是多少？（保留 4 位小数）
- expected: `SELECT round( (SELECT count(*) FROM (SELECT user_id FROM orders WHERE status = 'paid' GROUP BY user_id HAVING count(*) >= 2)) * 1.0 / (SELECT count(DISTINCT user_id) FROM orders WHERE status = 'paid'), 4)`
- agent: `WITH paid_orders AS ( SELECT user_id, COUNT(DISTINCT id) AS order_cnt FROM orders WHERE status = 'paid' GROUP BY user_id ) SELECT SUM(CASE WHEN order_cnt >= 2 THEN 1 ELSE 0 END) AS repeat_buyers, COUNT(*) AS total_buyers, ROUND(1.0 * SUM(CASE WHEN order_cnt >= 2 THEN 1 ELSE 0 END) / COUNT(*), 4) AS repurchase_rate FROM paid_orders;`

