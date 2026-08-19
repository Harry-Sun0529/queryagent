# QueryAgent Eval Report — public subset

- model: `deepseek-v4-flash`
- cases: 30

## Summary

| metric | value |
|---|---|
| first-execution pass rate | 10/30 (33%) |
| pass rate after self-repair | 16/30 (53%) |
| metric hit rate | n/a |
| clarify-behaviour accuracy | n/a |
| average tool calls | 2.70 |
| tokens per case (in+out) | 9,646 |
| prompt cache hit rate | 84% |
| latency per case | 9.0s |
| cost per case (upper bound) | $0.0021 |

## Cases

| id | kind | passed | first try | retries | tool calls | note |
|---|---|---|---|---|---|---|
| california_schools_37 | public | ❌ | ❌ | 0 | 5 | result sets differ |
| california_schools_39 | public | ✅ | ❌ | 0 | 6 |  |
| california_schools_41 | public | ❌ | ❌ | 0 | 7 | result sets differ |
| california_schools_45 | public | ✅ | ❌ | 0 | 5 |  |
| card_games_379 | public | ✅ | ✅ | 0 | 3 |  |
| card_games_397 | public | ❌ | ❌ | 0 | 5 | result sets differ |
| card_games_409 | public | ✅ | ✅ | 0 | 1 |  |
| card_games_422 | public | ✅ | ✅ | 0 | 1 |  |
| card_games_479 | public | ✅ | ✅ | 0 | 1 |  |
| codebase_community_581 | public | ✅ | ✅ | 0 | 1 |  |
| codebase_community_634 | public | ❌ | ❌ | 0 | 4 | result sets differ |
| codebase_community_640 | public | ❌ | ❌ | 0 | 5 | result sets differ |
| codebase_community_678 | public | ❌ | ❌ | 0 | 1 | result sets differ |
| codebase_community_701 | public | ❌ | ❌ | 0 | 0 | reference expected_sql failed (case bug?): interrupted |
| debit_card_specializing_1484 | public | ✅ | ❌ | 0 | 2 |  |
| financial_115 | public | ❌ | ❌ | 0 | 3 | result sets differ |
| financial_117 | public | ❌ | ❌ | 0 | 1 | result sets differ |
| formula_1_866 | public | ✅ | ❌ | 0 | 4 |  |
| formula_1_910 | public | ✅ | ✅ | 0 | 1 |  |
| formula_1_940 | public | ✅ | ❌ | 0 | 2 |  |
| formula_1_972 | public | ❌ | ❌ | 1 | 3 | result sets differ |
| formula_1_990 | public | ❌ | ❌ | 0 | 4 | result sets differ |
| student_club_1361 | public | ✅ | ✅ | 0 | 1 |  |
| student_club_1376 | public | ❌ | ❌ | 0 | 3 | result sets differ |
| student_club_1405 | public | ✅ | ✅ | 0 | 2 |  |
| superhero_719 | public | ✅ | ✅ | 0 | 1 |  |
| superhero_733 | public | ✅ | ✅ | 0 | 1 |  |
| superhero_751 | public | ❌ | ❌ | 0 | 1 | result sets differ |
| superhero_758 | public | ❌ | ❌ | 0 | 5 | result sets differ |
| thrombosis_prediction_1270 | public | ✅ | ❌ | 0 | 2 |  |

## Failing cases — SQL comparison

### california_schools_37

- question: What is the complete address of the school with the lowest excellence rate? Indicate the Street, City, Zip and State.
- expected: `SELECT T2.Street, T2.City, T2.State, T2.Zip FROM satscores AS T1 INNER JOIN schools AS T2 ON T1.cds = T2.CDSCode ORDER BY CAST(T1.NumGE1500 AS REAL) / T1.NumTstTakr ASC LIMIT 1`
- agent: `SELECT sc.Street, sc.City, sc.Zip, sc.State, sc.School, s.cds, s.sname, s.NumTstTakr, s.NumGE1500 FROM satscores s JOIN schools sc ON sc.CDSCode = s.cds WHERE s.rtype = 'S' AND s.NumTstTakr > 0 AND s.NumGE1500 IS NOT NULL AND CAST(s.NumGE1500 AS REAL) / s.NumTstTakr = 0 ORDER BY s.NumTstTakr DESC LIMIT 5;`

### california_schools_41

- question: List the names of virtual schools that are among the top 5 in their respective counties based on average reading scores.
- expected: `SELECT School FROM (SELECT T2.School,T1.AvgScrRead, RANK() OVER (PARTITION BY T2.County ORDER BY T1.AvgScrRead DESC) AS rnk FROM satscores AS T1 INNER JOIN schools AS T2 ON T1.cds = T2.CDSCode WHERE T2.Virtual = 'F' ) ranked_schools WHERE rnk <= 5`
- agent: `WITH ranked AS ( SELECT sc.CDSCode, sc.School, sc.County, s.AvgScrRead, ROW_NUMBER() OVER (PARTITION BY sc.County ORDER BY s.AvgScrRead DESC) AS rn FROM satscores s JOIN schools sc ON sc.CDSCode = s.cds WHERE s.rtype = 'S' AND s.AvgScrRead IS NOT NULL ) SELECT School, County, AvgScrRead, rn FROM ranked WHERE rn <= 5 ORDER BY County, rn`

### card_games_397

- question: What is the mana cost of cards with a normal layout, a 2003 frame version, with a black border color, and available in paper and mtgo?
- expected: `SELECT manaCost FROM cards WHERE availability = 'mtgo,paper' AND borderColor = 'black' AND frameVersion = 2003 AND layout = 'normal'`
- agent: `SELECT DISTINCT manaCost FROM cards WHERE layout = 'normal' AND frameVersion = '2003' AND borderColor = 'black' AND availability = 'mtgo,paper' ORDER BY manaCost LIMIT 200 OFFSET 400;`

### codebase_community_634

- question: Among posts by Harvey Motulsky and Noah Snyder, which one has higher popularity?
- expected: `SELECT T1.DisplayName FROM users AS T1 INNER JOIN postHistory AS T2 ON T1.Id = T2.UserId INNER JOIN posts AS T3 ON T2.PostId = T3.Id WHERE T1.DisplayName = 'Harvey Motulsky' OR T1.DisplayName = 'Noah Snyder' GROUP BY T1.DisplayName ORDER BY SUM(T3.ViewCount) DESC LIMIT 1`
- agent: `SELECT OwnerUserId, COUNT(*) AS num_posts, SUM(ViewCount) AS total_views FROM posts WHERE OwnerUserId IN (19, 25) GROUP BY OwnerUserId;`

### codebase_community_640

- question: Calculate the difference in view count from post posted by Mornington and view count from posts posted by Amos.
- expected: `SELECT SUM(IIF(T1.DisplayName = 'Mornington', T3.ViewCount, 0)) - SUM(IIF(T1.DisplayName = 'Amos', T3.ViewCount, 0)) AS diff FROM users AS T1 INNER JOIN postHistory AS T2 ON T1.Id = T2.UserId INNER JOIN posts AS T3 ON T3.Id = T2.PostId`
- agent: `SELECT (SELECT COALESCE(SUM(ViewCount), 0) FROM posts WHERE OwnerUserId = 55) AS amos_sum_via_userid, (SELECT COUNT(*) FROM posts WHERE OwnerUserId = 55) AS amos_post_count;`

### codebase_community_678

- question: Which post by Harvey Motulsky has the most views? Please give the id and title of this post.
- expected: `SELECT T2.Id, T2.Title FROM users AS T1 INNER JOIN posts AS T2 ON T1.Id = T2.OwnerUserId WHERE T1.DisplayName = 'Harvey Motulsky' ORDER BY T2.ViewCount DESC LIMIT 1`
- agent: `SELECT p.Id, p.Title, p.ViewCount FROM posts p JOIN users u ON p.OwnerUserId = u.Id WHERE u.DisplayName = 'Harvey Motulsky' ORDER BY p.ViewCount DESC LIMIT 1;`

### financial_115

- question: For the branch which located in the south Bohemia with biggest number of inhabitants, what is the percentage of the male clients?
- expected: `SELECT CAST(SUM(T1.gender = 'M') AS REAL) * 100 / COUNT(T1.client_id) FROM client AS T1 INNER JOIN district AS T2 ON T1.district_id = T2.district_id WHERE T2.A3 = 'south Bohemia' GROUP BY T2.A4 ORDER BY T2.A4 DESC LIMIT 1`
- agent: `SELECT COUNT(*) AS total_clients, SUM(CASE WHEN gender = 'M' THEN 1 ELSE 0 END) AS male_clients, ROUND(100.0 * SUM(CASE WHEN gender = 'M' THEN 1 ELSE 0 END) / COUNT(*), 2) AS male_pct FROM client WHERE district_id = (SELECT district_id FROM district WHERE A3 = 'south Bohemia' ORDER BY A4 DESC LIMIT 1);`

### financial_117

- question: What is the percentage of loan amount that has been fully paid with no issue.
- expected: `SELECT (CAST(SUM(CASE WHEN status = 'A' THEN amount ELSE 0 END) AS REAL) * 100) / SUM(amount) FROM loan`
- agent: `SELECT ROUND(100.0 * SUM(CASE WHEN status = 'A' THEN amount ELSE 0 END) / SUM(amount), 2) AS pct_fully_paid FROM loan;`

### formula_1_972

- question: Which drivers who were born in 1971 and has the fastest lap time on the race? Give id and code of these drivers.
- expected: `SELECT T2.driverId, T2.code FROM results AS T1 INNER JOIN drivers AS T2 on T1.driverId = T2.driverId WHERE STRFTIME('%Y', T2.dob) = '1971' AND T1.fastestLapTime IS NOT NULL`
- agent: `SELECT driverId, code, forename, surname, dob FROM drivers WHERE driverId IN (14, 35, 37, 69);`

### formula_1_990

- question: What is the constructor reference name of the champion in the 2009 Singapore Grand Prix? Please give its website.
- expected: `SELECT T3.constructorRef, T3.url FROM results AS T1 INNER JOIN races AS T2 on T1.raceId = T2.raceId INNER JOIN constructors AS T3 on T1.constructorId = T3.constructorId WHERE T2.name = 'Singapore Grand Prix' AND T2.year = 2009 AND T1.time LIKE '_:%:__.___'`
- agent: `SELECT driverId, forename, surname FROM drivers WHERE driverId = 1;`

### student_club_1376

- question: Among all the closed events, which event has the highest spend-to-budget ratio?
- expected: `SELECT T2.event_name FROM budget AS T1 INNER JOIN event AS T2 ON T1.link_to_event = T2.event_id WHERE T2.status = 'Closed' ORDER BY T1.spent / T1.amount DESC LIMIT 1`
- agent: `SELECT e.event_name, b.spent, b.amount, (b.spent * 1.0 / b.amount) AS ratio FROM budget b JOIN event e ON e.event_id = b.link_to_event WHERE e.status = 'Closed' ORDER BY ratio DESC`

### superhero_751

- question: List down at least five superpowers of male superheroes.
- expected: `SELECT T3.power_name FROM superhero AS T1 INNER JOIN hero_power AS T2 ON T1.id = T2.hero_id INNER JOIN superpower AS T3 ON T3.id = T2.power_id INNER JOIN gender AS T4 ON T4.id = T1.gender_id WHERE T4.gender = 'Male' LIMIT 5`
- agent: `SELECT DISTINCT sp.power_name FROM superhero s JOIN gender g ON s.gender_id = g.id JOIN hero_power hp ON hp.hero_id = s.id JOIN superpower sp ON hp.power_id = sp.id WHERE g.gender = 'Male' ORDER BY sp.power_name;`

### superhero_758

- question: Provide the hair colour of the human superhero who is 185 cm tall.
- expected: `SELECT DISTINCT T3.colour FROM superhero AS T1 INNER JOIN race AS T2 ON T1.race_id = T2.id INNER JOIN colour AS T3 ON T1.hair_colour_id = T3.id WHERE T1.height_cm = 185 AND T2.race = 'Human'`
- agent: `SELECT s.superhero_name, c.colour FROM superhero s JOIN race r ON s.race_id = r.id JOIN colour c ON s.hair_colour_id = c.id WHERE r.race = 'Human' AND s.height_cm = 185 ORDER BY s.superhero_name;`

