# QueryAgent Eval Report — public subset

- model: `deepseek-v4-flash`
- cases: 30

## Summary

| metric | value |
|---|---|
| first-execution pass rate | 9/30 (30%) |
| pass rate after self-repair | 14/30 (47%) |
| metric hit rate | n/a |
| clarify-behaviour accuracy | n/a |
| average tool calls | 2.97 |
| tokens per case (in+out) | 10,237 |
| prompt cache hit rate | 83% |
| latency per case | 11.1s |
| cost per case (upper bound) | $0.0025 |

## Cases

| id | kind | passed | first try | retries | tool calls | note |
|---|---|---|---|---|---|---|
| california_schools_72 | public | ❌ | ❌ | 0 | 6 | result sets differ |
| california_schools_85 | public | ❌ | ❌ | 0 | 3 | result sets differ |
| card_games_345 | public | ✅ | ✅ | 0 | 1 |  |
| card_games_346 | public | ✅ | ✅ | 0 | 4 |  |
| card_games_358 | public | ❌ | ❌ | 0 | 1 | result sets differ |
| card_games_368 | public | ✅ | ✅ | 0 | 1 |  |
| card_games_407 | public | ❌ | ❌ | 0 | 3 | result sets differ |
| card_games_412 | public | ❌ | ❌ | 0 | 6 | result sets differ |
| card_games_415 | public | ✅ | ❌ | 0 | 6 |  |
| card_games_480 | public | ❌ | ❌ | 0 | 5 | result sets differ |
| codebase_community_539 | public | ✅ | ❌ | 0 | 2 |  |
| codebase_community_685 | public | ❌ | ❌ | 0 | 4 | result sets differ |
| codebase_community_707 | public | ✅ | ✅ | 0 | 2 |  |
| debit_card_specializing_1481 | public | ❌ | ❌ | 0 | 5 | result sets differ |
| european_football_2_1079 | public | ❌ | ❌ | 0 | 2 | result sets differ |
| european_football_2_1134 | public | ✅ | ❌ | 0 | 2 |  |
| financial_128 | public | ✅ | ✅ | 0 | 1 |  |
| financial_169 | public | ❌ | ❌ | 0 | 4 | result sets differ |
| financial_189 | public | ❌ | ❌ | 0 | 8 | result sets differ |
| financial_93 | public | ✅ | ❌ | 0 | 2 |  |
| formula_1_906 | public | ❌ | ❌ | 0 | 2 | result sets differ |
| formula_1_955 | public | ❌ | ❌ | 0 | 3 | result sets differ |
| formula_1_977 | public | ✅ | ✅ | 0 | 2 |  |
| student_club_1317 | public | ✅ | ❌ | 0 | 8 |  |
| student_club_1346 | public | ✅ | ✅ | 0 | 1 |  |
| student_club_1409 | public | ✅ | ✅ | 0 | 1 |  |
| superhero_717 | public | ✅ | ✅ | 0 | 1 |  |
| thrombosis_prediction_1252 | public | ❌ | ❌ | 0 | 1 | result sets differ |
| thrombosis_prediction_1256 | public | ❌ | ❌ | 0 | 1 | result sets differ |
| toxicology_268 | public | ❌ | ❌ | 0 | 1 | result sets differ |

## Failing cases — SQL comparison

### california_schools_72

- question: How many students from the ages of 5 to 17 are enrolled at the State Special School school in Fremont for the 2014-2015 academic year?
- expected: `SELECT T1.`Enrollment (Ages 5-17)` FROM frpm AS T1 INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode WHERE T2.EdOpsCode = 'SSS' AND T2.City = 'Fremont' AND T1.`Academic Year` BETWEEN 2014 AND 2015`
- agent: `SELECT f."School Name", f."Enrollment (Ages 5-17)" FROM frpm f JOIN schools s ON s.CDSCode = f.CDSCode WHERE s.EdOpsCode = 'SSS' AND s.City = 'Fremont' AND f."Academic Year" = '2014-2015';`

### california_schools_85

- question: What is the Percent (%) Eligible Free (K-12) in the school administered by an administrator whose first name is Alusine. List the district code of the school.
- expected: `SELECT T1.`Free Meal Count (K-12)` * 100 / T1.`Enrollment (K-12)`, T1.`District Code` FROM frpm AS T1 INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode WHERE T2.AdmFName1 = 'Alusine'`
- agent: `SELECT f."District Code", f."Percent (%) Eligible Free (K-12)" FROM schools s JOIN frpm f ON s.CDSCode = f.CDSCode WHERE s.AdmFName1 = 'Alusine' OR s.AdmFName2 = 'Alusine' OR s.AdmFName3 = 'Alusine';`

### card_games_358

- question: What is the border color of card "Ancestor's Chosen"?
- expected: `SELECT DISTINCT borderColor FROM cards WHERE name = 'Ancestor''s Chosen'`
- agent: `SELECT borderColor FROM cards WHERE name = 'Ancestor''s Chosen';`

### card_games_407

- question: Lists all types of cards in German.
- expected: `SELECT T1.subtypes, T1.supertypes FROM cards AS T1 INNER JOIN foreign_data AS T2 ON T1.uuid = T2.uuid WHERE T2.language = 'German' AND T1.subtypes IS NOT NULL AND T1.supertypes IS NOT NULL`
- agent: `SELECT subtypes, supertypes, types, name FROM cards WHERE subtypes IS NOT NULL AND supertypes IS NOT NULL LIMIT 10`

### card_games_412

- question: What is the foreign name of the card in French of type Creature, normal layout and black border color, by artist Matthew D. Wilson?
- expected: `SELECT name FROM foreign_data WHERE uuid IN ( SELECT uuid FROM cards WHERE types = 'Creature' AND layout = 'normal' AND borderColor = 'black' AND artist = 'Matthew D. Wilson' ) AND language = 'French'`
- agent: `SELECT DISTINCT fd.name FROM cards c JOIN foreign_data fd ON fd.uuid = c.uuid WHERE c.artist = 'Matthew D. Wilson' AND c.type LIKE '%Creature%' AND c.layout = 'normal' AND c.borderColor = 'black' AND fd.language = 'French' ORDER BY fd.name`

### card_games_480

- question: What is the Italian flavor text of the card "Ancestor's Chosen"?
- expected: `SELECT T2.flavorText FROM cards AS T1 INNER JOIN foreign_data AS T2 ON T2.uuid = T1.uuid WHERE T1.name = 'Ancestor''s Chosen' AND T2.language = 'Italian'`
- agent: `SELECT c.setCode, s.name AS setName, c.number, f.flavorText, f.language FROM foreign_data f JOIN cards c ON c.uuid = f.uuid LEFT JOIN sets s ON s.code = c.setCode WHERE c.name = 'Ancestor''s Chosen' AND f.language = 'Italian';`

### codebase_community_685

- question: Identify the total views on the post 'Computer Game Datasets'. Name the user who posted it last time.
- expected: `SELECT T2.ViewCount, T3.DisplayName FROM postHistory AS T1 INNER JOIN posts AS T2 ON T1.PostId = T2.Id INNER JOIN users AS T3 ON T2.LastEditorUserId = T3.Id WHERE T1.Text = 'Computer Game Datasets'`
- agent: `SELECT Id, DisplayName, Reputation FROM users WHERE Id = 37`

### debit_card_specializing_1481

- question: What is the difference in the annual average consumption of the customers with the least amount of consumption paid in CZK for 2013 between SME and LAM, LAM and KAM, and KAM and SME?
- expected: `SELECT CAST(SUM(IIF(T1.Segment = 'SME', T2.Consumption, 0)) AS REAL) / COUNT(T1.CustomerID) - CAST(SUM(IIF(T1.Segment = 'LAM', T2.Consumption, 0)) AS REAL) / COUNT(T1.CustomerID) , CAST(SUM(IIF(T1.Segment = 'LAM', T2.Consumption, 0)) AS REAL) / COUNT(T1.CustomerID) - CAST(SUM(IIF(T1.Segment = 'KAM', T2.Consumption, 0)) AS REAL) / COUNT(T1.CustomerID) , CAST(SUM(IIF(T1.Segment = 'KAM', T2.Consumption, 0)) AS REAL) / COUNT(T1.CustomerID) - CAST(SUM(IIF(T1.Segment = 'SME', T2.Consumption, 0)) AS REAL) / COUNT(T1.CustomerID) FROM customers AS T1 INNER JOIN yearmonth AS T2 ON T1.CustomerID = T2.CustomerID WHERE T1.Currency = 'CZK' AND T2.Consumption = ( SELECT MIN(Consumption) FROM yearmonth ) AND T2.Date BETWEEN 201301 AND 201312`
- agent: `WITH czk_2013 AS ( SELECT c.CustomerID, c.Segment, SUM(ym.Consumption) AS total_consumption FROM customers c JOIN yearmonth ym ON c.CustomerID = ym.CustomerID WHERE c.Currency = 'CZK' AND c.Segment IN ('SME','LAM','KAM') AND ym.Date BETWEEN '201301' AND '201312' GROUP BY c.CustomerID, c.Segment ), min_per_segment AS ( SELECT Segment, MIN(total_consumption) AS min_consumption FROM czk_2013 GROUP BY Segment ), lowest_customers AS ( SELECT czk.Segment, czk.CustomerID, czk.total_consumption FROM czk_2013 czk JOIN min_per_segment mps ON czk.Segment = mps.Segment AND czk.total_consumption = mps.min_consumption ), annual_avg AS ( SELECT Segment, SUM(total_consumption) * 1.0 / COUNT(*) AS annual_avg FROM lowest_customers GROUP BY Segment ) SELECT ROUND(MAX(CASE WHEN Segment='SME' THEN annual_avg END) - MAX(CASE WHEN Segment='LAM' THEN annual_avg END), 4) AS SME_minus_LAM, ROUND(MAX(CASE WHEN Segment='LAM' THEN annual_avg END) - MAX(CASE WHEN Segment='KAM' THEN annual_avg END), 4) AS LAM_minus_KAM, ROUND(MAX(CASE WHEN Segment='KAM' THEN annual_avg END) - MAX(CASE WHEN Segment='SME' THEN annual_avg END), 4) AS KAM_minus_SME FROM annual_avg`

### european_football_2_1079

- question: Which player is the tallest?
- expected: `SELECT player_name FROM Player ORDER BY height DESC LIMIT 1`
- agent: `SELECT player_name, height FROM Player WHERE height = (SELECT MAX(height) FROM Player);`

### financial_169

- question: What was the growth rate of the total amount of loans across all accounts for a male client between 1996 and 1997?
- expected: `SELECT CAST((SUM(CASE WHEN STRFTIME('%Y', T1.date) = '1997' THEN T1.amount ELSE 0 END) - SUM(CASE WHEN STRFTIME('%Y', T1.date) = '1996' THEN T1.amount ELSE 0 END)) AS REAL) * 100 / SUM(CASE WHEN STRFTIME('%Y', T1.date) = '1996' THEN T1.amount ELSE 0 END) FROM loan AS T1 INNER JOIN account AS T2 ON T1.account_id = T2.account_id INNER JOIN disp AS T3 ON T3.account_id = T2.account_id INNER JOIN client AS T4 ON T4.client_id = T3.client_id WHERE T4.gender = 'M' AND T3.type = 'OWNER'`
- agent: `WITH male_loans AS ( SELECT l.amount, CAST(strftime('%Y', l.date) AS INTEGER) AS yr FROM loan l JOIN disp d ON d.account_id = l.account_id AND d.type = 'OWNER' JOIN client c ON c.client_id = d.client_id WHERE c.gender = 'M' AND strftime('%Y', l.date) IN ('1996','1997') ), sums AS ( SELECT SUM(CASE WHEN yr = 1996 THEN amount ELSE 0 END) AS s96, SUM(CASE WHEN yr = 1997 THEN amount ELSE 0 END) AS s97 FROM male_loans ) SELECT ROUND((s97 - s96) * 100.0 / s96, 2) AS growth_rate_pct FROM sums;`

### financial_189

- question: Name the account numbers of female clients who are oldest and have lowest average salary?
- expected: `SELECT T3.account_id FROM client AS T1 INNER JOIN district AS T2 ON T1.district_id = T2.district_id INNER JOIN account AS T3 ON T2.district_id = T3.district_id INNER JOIN disp AS T4 ON T1.client_id = T4.client_id AND T4.account_id = T3.account_id WHERE T1.gender = 'F' ORDER BY T1.birth_date ASC, T2.A11 ASC LIMIT 1`
- agent: `SELECT c.client_id, c.birth_date, d.A11, a.account_id FROM client c JOIN district d ON c.district_id = d.district_id JOIN disp dp ON c.client_id = dp.client_id JOIN account a ON dp.account_id = a.account_id WHERE c.gender = 'F' AND d.A11 = (SELECT MIN(A11) FROM district) ORDER BY c.birth_date`

### formula_1_906

- question: Which was Lewis Hamilton first race? What was his points recorded for his first race event?
- expected: `SELECT T1.name, T2.points FROM races AS T1 INNER JOIN driverStandings AS T2 ON T2.raceId = T1.raceId INNER JOIN drivers AS T3 ON T3.driverId = T2.driverId WHERE T3.forename = 'Lewis' AND T3.surname = 'Hamilton' ORDER BY T1.year ASC LIMIT 1`
- agent: `SELECT r.year, r.round, r.name AS race_name, res.positionOrder, res.points, res.statusId, st.status FROM drivers d JOIN results res ON res.driverId = d.driverId JOIN races r ON r.raceId = res.raceId JOIN status st ON st.statusId = res.statusId WHERE d.forename = 'Lewis' AND d.surname = 'Hamilton' AND r.year = 2007 ORDER BY r.round ASC;`

### formula_1_955

- question: What is the average time in seconds of champion for each year, before year 1975?
- expected: `WITH time_in_seconds AS ( SELECT T2.year, T2.raceId, T1.positionOrder, CASE WHEN T1.positionOrder = 1 THEN (CAST(SUBSTR(T1.time, 1, 1) AS REAL) * 3600) + (CAST(SUBSTR(T1.time, 3, 2) AS REAL) * 60) + CAST(SUBSTR(T1.time, 6,2) AS REAL ) + CAST(SUBSTR(T1.time, 9) AS REAL)/1000 ELSE 0 END AS time_seconds FROM results AS T1 INNER JOIN races AS T2 ON T1.raceId = T2.raceId WHERE T1.time IS NOT NULL ), champion_time AS ( SELECT year, raceId, time_seconds FROM time_in_seconds WHERE positionOrder = 1 ) SELECT year, AVG(time_seconds) FROM champion_time WHERE year < 1975 GROUP BY year HAVING AVG(time_seconds) IS NOT NULL`
- agent: `SELECT CASE WHEN time LIKE '+%' THEN 'plus' WHEN time GLOB '*:*:*.*' THEN 'three-part' WHEN time GLOB '*:*.*' THEN 'two-part' ELSE 'other' END AS pat, COUNT(*) AS cnt, MIN(time) AS mn, MAX(time) AS mx FROM results WHERE time IS NOT NULL GROUP BY pat`

### thrombosis_prediction_1252

- question: Among the patients with a normal Ig G level, how many of them have symptoms?
- expected: `SELECT COUNT(T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID INNER JOIN Examination AS T3 ON T3.ID = T2.ID WHERE T2.IGG BETWEEN 900 AND 2000 AND T3.Symptoms IS NOT NULL`
- agent: `SELECT COUNT(DISTINCT e.ID) AS patient_count FROM Laboratory l JOIN Examination e ON l.ID = e.ID WHERE l.IGG > 900 AND l.IGG < 2000 AND e.Symptoms IS NOT NULL;`

### thrombosis_prediction_1256

- question: How many patients with a abnormal C-reactive protein don't have their data recorded?
- expected: `SELECT COUNT(T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE (T2.CRP = '+' ) AND T1.Description IS NULL`
- agent: `SELECT COUNT(DISTINCT p.ID) AS patient_count FROM Patient p JOIN Laboratory l ON p.ID = l.ID WHERE l.CRP = '+' AND p.Description IS NULL;`

### toxicology_268

- question: What are the elements for bond id TR001_10_11?
- expected: `SELECT T2.element FROM connected AS T1 INNER JOIN atom AS T2 ON T1.atom_id = T2.atom_id WHERE T1.bond_id = 'TR001_10_11'`
- agent: `SELECT a1.element AS element_1, a2.element AS element_2 FROM bond b JOIN connected c ON c.bond_id = b.bond_id JOIN atom a1 ON a1.atom_id = c.atom_id JOIN atom a2 ON a2.atom_id = c.atom_id2 WHERE b.bond_id = 'TR001_10_11'`

