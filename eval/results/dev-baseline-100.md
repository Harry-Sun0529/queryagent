# QueryAgent Eval Report — public subset

- model: `deepseek-v4-flash`
- cases: 100

## Summary

| metric | value |
|---|---|
| first-execution pass rate | 39/100 (39%) |
| pass rate after self-repair | 49/100 (49%) |
| metric hit rate | n/a |
| clarify-behaviour accuracy | n/a |
| average tool calls | 2.69 |
| tokens per case (in+out) | 9,612 |
| prompt cache hit rate | 88% |
| latency per case | 12.4s |
| cost per case (upper bound) | $0.0022 |

## Cases

| id | kind | passed | first try | retries | tool calls | note |
|---|---|---|---|---|---|---|
| california_schools_36 | public | ❌ | ❌ | 0 | 5 | result sets differ |
| california_schools_37 | public | ❌ | ❌ | 0 | 8 | result sets differ |
| california_schools_39 | public | ❌ | ❌ | 0 | 2 | result sets differ |
| california_schools_41 | public | ❌ | ❌ | 0 | 4 | result sets differ |
| california_schools_45 | public | ❌ | ❌ | 0 | 2 | result sets differ |
| california_schools_72 | public | ✅ | ✅ | 0 | 4 |  |
| california_schools_85 | public | ❌ | ❌ | 0 | 3 | result sets differ |
| card_games_340 | public | ❌ | ❌ | 0 | 2 | result sets differ |
| card_games_345 | public | ✅ | ✅ | 0 | 1 |  |
| card_games_346 | public | ✅ | ✅ | 0 | 3 |  |
| card_games_358 | public | ❌ | ❌ | 0 | 1 | result sets differ |
| card_games_368 | public | ✅ | ✅ | 0 | 1 |  |
| card_games_379 | public | ✅ | ✅ | 0 | 8 |  |
| card_games_397 | public | ❌ | ❌ | 0 | 4 | result sets differ |
| card_games_407 | public | ❌ | ❌ | 0 | 8 | result sets differ |
| card_games_409 | public | ✅ | ✅ | 0 | 1 |  |
| card_games_412 | public | ❌ | ❌ | 0 | 6 | result sets differ |
| card_games_415 | public | ✅ | ❌ | 0 | 4 |  |
| card_games_422 | public | ❌ | ❌ | 1 | 4 | result sets differ |
| card_games_459 | public | ❌ | ❌ | 0 | 1 | result sets differ |
| card_games_468 | public | ✅ | ✅ | 0 | 1 |  |
| card_games_479 | public | ✅ | ✅ | 0 | 1 |  |
| card_games_480 | public | ❌ | ❌ | 0 | 8 | result sets differ |
| codebase_community_539 | public | ✅ | ✅ | 0 | 1 |  |
| codebase_community_557 | public | ❌ | ❌ | 0 | 1 | result sets differ |
| codebase_community_573 | public | ✅ | ✅ | 0 | 1 |  |
| codebase_community_581 | public | ✅ | ✅ | 0 | 1 |  |
| codebase_community_604 | public | ❌ | ❌ | 0 | 1 | result sets differ |
| codebase_community_633 | public | ❌ | ❌ | 0 | 6 | result sets differ |
| codebase_community_634 | public | ❌ | ❌ | 0 | 6 | result sets differ |
| codebase_community_640 | public | ❌ | ❌ | 0 | 8 | result sets differ |
| codebase_community_678 | public | ✅ | ✅ | 0 | 1 |  |
| codebase_community_685 | public | ❌ | ❌ | 1 | 5 | result sets differ |
| codebase_community_701 | public | ❌ | ❌ | 0 | 2 | reference expected_sql failed (case bug?): interrupted |
| codebase_community_707 | public | ✅ | ✅ | 0 | 3 |  |
| debit_card_specializing_1481 | public | ❌ | ❌ | 0 | 7 | result sets differ |
| debit_card_specializing_1484 | public | ❌ | ❌ | 0 | 2 | result sets differ |
| european_football_2_1030 | public | ✅ | ✅ | 0 | 1 |  |
| european_football_2_1079 | public | ❌ | ❌ | 0 | 1 | result sets differ |
| european_football_2_1134 | public | ❌ | ❌ | 0 | 3 | result sets differ |
| european_football_2_1135 | public | ❌ | ❌ | 0 | 4 | result sets differ |
| financial_115 | public | ❌ | ❌ | 0 | 3 | result sets differ |
| financial_117 | public | ❌ | ❌ | 0 | 1 | result sets differ |
| financial_128 | public | ❌ | ❌ | 0 | 2 | result sets differ |
| financial_159 | public | ❌ | ❌ | 0 | 1 | result sets differ |
| financial_168 | public | ❌ | ❌ | 0 | 1 | result sets differ |
| financial_169 | public | ❌ | ❌ | 0 | 6 | result sets differ |
| financial_189 | public | ❌ | ❌ | 0 | 7 | result sets differ |
| financial_92 | public | ✅ | ❌ | 0 | 3 |  |
| financial_93 | public | ✅ | ❌ | 0 | 2 |  |
| financial_95 | public | ✅ | ❌ | 0 | 6 |  |
| formula_1_866 | public | ✅ | ✅ | 0 | 6 |  |
| formula_1_869 | public | ✅ | ✅ | 0 | 1 |  |
| formula_1_877 | public | ❌ | ❌ | 0 | 1 | result sets differ |
| formula_1_897 | public | ❌ | ❌ | 0 | 1 | result sets differ |
| formula_1_906 | public | ❌ | ❌ | 0 | 2 | result sets differ |
| formula_1_909 | public | ✅ | ✅ | 0 | 1 |  |
| formula_1_910 | public | ✅ | ✅ | 0 | 1 |  |
| formula_1_940 | public | ✅ | ❌ | 0 | 2 |  |
| formula_1_955 | public | ❌ | ❌ | 0 | 8 | result sets differ |
| formula_1_960 | public | ✅ | ✅ | 0 | 1 |  |
| formula_1_972 | public | ❌ | ❌ | 0 | 1 | result sets differ |
| formula_1_977 | public | ✅ | ✅ | 0 | 1 |  |
| formula_1_990 | public | ❌ | ❌ | 0 | 4 | result sets differ |
| student_club_1317 | public | ✅ | ❌ | 0 | 8 |  |
| student_club_1346 | public | ✅ | ✅ | 0 | 1 |  |
| student_club_1350 | public | ❌ | ❌ | 0 | 2 | result sets differ |
| student_club_1352 | public | ✅ | ✅ | 0 | 1 |  |
| student_club_1361 | public | ✅ | ❌ | 0 | 2 |  |
| student_club_1376 | public | ❌ | ❌ | 0 | 1 | result sets differ |
| student_club_1378 | public | ✅ | ✅ | 0 | 1 |  |
| student_club_1399 | public | ❌ | ❌ | 0 | 3 | result sets differ |
| student_club_1405 | public | ✅ | ✅ | 0 | 1 |  |
| student_club_1409 | public | ✅ | ✅ | 0 | 1 |  |
| student_club_1422 | public | ❌ | ❌ | 0 | 1 | result sets differ |
| student_club_1426 | public | ✅ | ✅ | 0 | 1 |  |
| superhero_717 | public | ✅ | ✅ | 0 | 1 |  |
| superhero_719 | public | ✅ | ✅ | 0 | 1 |  |
| superhero_728 | public | ❌ | ❌ | 0 | 1 | result sets differ |
| superhero_730 | public | ❌ | ❌ | 0 | 6 | result sets differ |
| superhero_733 | public | ✅ | ✅ | 0 | 1 |  |
| superhero_751 | public | ❌ | ❌ | 0 | 1 | result sets differ |
| superhero_758 | public | ✅ | ❌ | 0 | 5 |  |
| superhero_765 | public | ✅ | ✅ | 0 | 1 |  |
| superhero_806 | public | ✅ | ✅ | 0 | 1 |  |
| thrombosis_prediction_1168 | public | ❌ | ❌ | 0 | 6 | result sets differ |
| thrombosis_prediction_1195 | public | ✅ | ✅ | 0 | 1 |  |
| thrombosis_prediction_1201 | public | ✅ | ✅ | 0 | 2 |  |
| thrombosis_prediction_1209 | public | ✅ | ✅ | 0 | 6 |  |
| thrombosis_prediction_1252 | public | ❌ | ❌ | 0 | 2 | result sets differ |
| thrombosis_prediction_1256 | public | ❌ | ❌ | 0 | 1 | result sets differ |
| thrombosis_prediction_1270 | public | ✅ | ✅ | 0 | 1 |  |
| toxicology_200 | public | ✅ | ✅ | 0 | 1 |  |
| toxicology_206 | public | ✅ | ✅ | 0 | 2 |  |
| toxicology_212 | public | ❌ | ❌ | 0 | 1 | result sets differ |
| toxicology_228 | public | ✅ | ❌ | 0 | 2 |  |
| toxicology_242 | public | ✅ | ✅ | 0 | 1 |  |
| toxicology_268 | public | ✅ | ❌ | 0 | 2 |  |
| toxicology_282 | public | ❌ | ❌ | 0 | 1 | result sets differ |
| toxicology_327 | public | ✅ | ✅ | 0 | 1 |  |

## Failing cases — SQL comparison

### california_schools_36

- question: Under whose administration is the school with the highest number of students scoring 1500 or more on the SAT? Indicate their full names.
- expected: `SELECT T2.AdmFName1, T2.AdmLName1, T2.AdmFName2, T2.AdmLName2, T2.AdmFName3, T2.AdmLName3 FROM satscores AS T1 INNER JOIN schools AS T2 ON T1.cds = T2.CDSCode ORDER BY T1.NumGE1500 DESC LIMIT 1`
- agent: `SELECT CDSCode, School, AdmFName1, AdmLName1, AdmFName2, AdmLName2, AdmFName3, AdmLName3 FROM schools WHERE CDSCode = '38684783833407'`

### california_schools_37

- question: What is the complete address of the school with the lowest excellence rate? Indicate the Street, City, Zip and State.
- expected: `SELECT T2.Street, T2.City, T2.State, T2.Zip FROM satscores AS T1 INNER JOIN schools AS T2 ON T1.cds = T2.CDSCode ORDER BY CAST(T1.NumGE1500 AS REAL) / T1.NumTstTakr ASC LIMIT 1`
- agent: `SELECT CDSCode, School, Street, City, Zip, State FROM schools WHERE CDSCode IN ('16739321630953','19648401936475','43694274330668') OR School LIKE '%Avenal%'`

### california_schools_39

- question: What is the average number of test takers from Fresno schools that opened between 1/1/1980 and 12/31/1980?
- expected: `SELECT AVG(T1.NumTstTakr) FROM satscores AS T1 INNER JOIN schools AS T2 ON T1.cds = T2.CDSCode WHERE strftime('%Y', T2.OpenDate) = '1980' AND T2.County = 'Fresno'`
- agent: `SELECT sc.CDSCode, sc.School, sc.OpenDate, s.sname, s.NumTstTakr FROM satscores s JOIN schools sc ON s.cds = sc.CDSCode WHERE sc.County = 'Fresno' AND sc.OpenDate BETWEEN '1980-01-01' AND '1980-12-31' ORDER BY sc.OpenDate LIMIT 10;`

### california_schools_41

- question: List the names of virtual schools that are among the top 5 in their respective counties based on average reading scores.
- expected: `SELECT School FROM (SELECT T2.School,T1.AvgScrRead, RANK() OVER (PARTITION BY T2.County ORDER BY T1.AvgScrRead DESC) AS rnk FROM satscores AS T1 INNER JOIN schools AS T2 ON T1.cds = T2.CDSCode WHERE T2.Virtual = 'F' ) ranked_schools WHERE rnk <= 5`
- agent: `WITH ranked AS ( SELECT sc.School AS school_name, sc.County AS county, sa.AvgScrRead AS avg_read, RANK() OVER (PARTITION BY sc.County ORDER BY sa.AvgScrRead DESC) AS rnk FROM schools sc JOIN satscores sa ON sa.cds = sc.CDSCode WHERE sc.Virtual = 'F' AND sa.rtype = 'S' AND sa.AvgScrRead IS NOT NULL ) SELECT county, school_name, avg_read, rnk FROM ranked WHERE rnk <= 5 ORDER BY county, rnk;`

### california_schools_45

- question: What is the average writing score of each of the schools managed by Ricci Ulrich? List the schools and the corresponding average writing scores.
- expected: `SELECT T2.School, T1.AvgScrWrite FROM satscores AS T1 INNER JOIN schools AS T2 ON T1.cds = T2.CDSCode WHERE T2.AdmFName1 = 'Ricci' AND T2.AdmLName1 = 'Ulrich'`
- agent: `SELECT cds, rtype, sname, dname, cname, enroll12, NumTstTakr, AvgScrRead, AvgScrMath, AvgScrWrite, NumGE1500 FROM satscores WHERE cds = '10621171030501'`

### california_schools_85

- question: What is the Percent (%) Eligible Free (K-12) in the school administered by an administrator whose first name is Alusine. List the district code of the school.
- expected: `SELECT T1.`Free Meal Count (K-12)` * 100 / T1.`Enrollment (K-12)`, T1.`District Code` FROM frpm AS T1 INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode WHERE T2.AdmFName1 = 'Alusine'`
- agent: `SELECT f."District Code", ROUND(f."Free Meal Count (K-12)" / f."Enrollment (K-12)" * 100.0, 2) AS pct_free FROM frpm f WHERE f.CDSCode = '19648576108609'`

### card_games_340

- question: Which are the cards that have incredibly powerful foils.
- expected: `SELECT id FROM cards WHERE cardKingdomFoilId IS NOT NULL AND cardKingdomId IS NOT NULL`
- agent: `SELECT COUNT(*) AS total_cards, COUNT(DISTINCT name) AS distinct_names FROM cards WHERE cardKingdomFoilId IS NOT NULL AND cardKingdomId IS NOT NULL;`

### card_games_358

- question: What is the border color of card "Ancestor's Chosen"?
- expected: `SELECT DISTINCT borderColor FROM cards WHERE name = 'Ancestor''s Chosen'`
- agent: `SELECT borderColor FROM cards WHERE name = 'Ancestor''s Chosen';`

### card_games_397

- question: What is the mana cost of cards with a normal layout, a 2003 frame version, with a black border color, and available in paper and mtgo?
- expected: `SELECT manaCost FROM cards WHERE availability = 'mtgo,paper' AND borderColor = 'black' AND frameVersion = 2003 AND layout = 'normal'`
- agent: `SELECT manaCost, COUNT(*) AS cnt FROM cards WHERE layout = 'normal' AND frameVersion = '2003' AND borderColor = 'black' AND availability = 'mtgo,paper' GROUP BY manaCost ORDER BY cnt DESC LIMIT 10;`

### card_games_407

- question: Lists all types of cards in German.
- expected: `SELECT T1.subtypes, T1.supertypes FROM cards AS T1 INNER JOIN foreign_data AS T2 ON T1.uuid = T2.uuid WHERE T2.language = 'German' AND T1.subtypes IS NOT NULL AND T1.supertypes IS NOT NULL`
- agent: `WITH RECURSIVE split(uuid, subtype, rest) AS ( SELECT c.uuid, '', c.subtypes || ',' FROM cards c JOIN foreign_data fd ON c.uuid = fd.uuid WHERE fd.language = 'German' AND c.subtypes IS NOT NULL AND c.supertypes IS NOT NULL UNION ALL SELECT uuid, substr(rest, 1, instr(rest, ',') - 1), substr(rest, instr(rest, ',') + 1) FROM split WHERE rest <> '' ) SELECT COUNT(DISTINCT subtype) FROM split WHERE subtype <> ''`

### card_games_412

- question: What is the foreign name of the card in French of type Creature, normal layout and black border color, by artist Matthew D. Wilson?
- expected: `SELECT name FROM foreign_data WHERE uuid IN ( SELECT uuid FROM cards WHERE types = 'Creature' AND layout = 'normal' AND borderColor = 'black' AND artist = 'Matthew D. Wilson' ) AND language = 'French'`
- agent: `SELECT DISTINCT fd.type FROM cards c JOIN foreign_data fd ON fd.uuid = c.uuid WHERE c.types = 'Creature' AND c.layout = 'normal' AND c.borderColor = 'black' AND c.artist = 'Matthew D. Wilson' AND fd.language = 'French' LIMIT 20;`

### card_games_422

- question: What is the language of the card with the multiverse number 149934?
- expected: `SELECT language FROM foreign_data WHERE multiverseid = 149934`
- agent: `SELECT name, multiverseId, setCode FROM cards WHERE uuid = '5f8287b1-5bb6-5f4c-ad17-316a40d5bb0c';`

### card_games_459

- question: Which card costs more converted mana, "Serra Angel" or "Shrine Keeper"?
- expected: `SELECT name FROM cards WHERE name IN ('Serra Angel', 'Shrine Keeper') ORDER BY convertedManaCost DESC LIMIT 1`
- agent: `SELECT name, convertedManaCost FROM cards WHERE name IN ('Serra Angel', 'Shrine Keeper') GROUP BY name, convertedManaCost;`

### card_games_480

- question: What is the Italian flavor text of the card "Ancestor's Chosen"?
- expected: `SELECT T2.flavorText FROM cards AS T1 INNER JOIN foreign_data AS T2 ON T2.uuid = T1.uuid WHERE T1.name = 'Ancestor''s Chosen' AND T2.language = 'Italian'`
- agent: `SELECT c.name, c.setCode, c.flavorText, c.uuid FROM cards c WHERE c.uuid IN ('5f8287b1-5bb6-5f4c-ad17-316a40d5bb0c', '7a7e2e9b-93ad-5616-8e3f-ed53a06acfd4');`

### codebase_community_557

- question: Among the posts with a score of over 5, what is the percentage of them being owned by an elder user?
- expected: `SELECT CAST(SUM(IIF(T2.Age > 65, 1, 0)) AS REAL) * 100 / COUNT(T1.Id) FROM posts AS T1 INNER JOIN users AS T2 ON T1.OwnerUserId = T2.Id WHERE T1.Score > 5`
- agent: `SELECT COUNT(*) AS total_posts, SUM(CASE WHEN u.Age > 65 THEN 1 ELSE 0 END) AS elder_owned_posts, 100.0 * SUM(CASE WHEN u.Age > 65 THEN 1 ELSE 0 END) / COUNT(*) AS percentage FROM posts p LEFT JOIN users u ON p.OwnerUserId = u.Id WHERE p.Score > 5;`

### codebase_community_604

- question: What is the average of the up votes and the average user age for users creating more than 10 posts?
- expected: `SELECT AVG(T1.UpVotes), AVG(T1.Age) FROM users AS T1 INNER JOIN ( SELECT OwnerUserId, COUNT(*) AS post_count FROM posts GROUP BY OwnerUserId HAVING post_count > 10) AS T2 ON T1.Id = T2.OwnerUserId`
- agent: `WITH user_posts AS ( SELECT OwnerUserId AS UserId FROM posts WHERE OwnerUserId IS NOT NULL GROUP BY OwnerUserId HAVING COUNT(*) > 10 ) SELECT SUM(u.UpVotes) * 1.0 / COUNT(u.Id) AS avg_upvotes, SUM(u.Age) * 1.0 / COUNT(u.Id) AS avg_age FROM user_posts up JOIN users u ON u.Id = up.UserId;`

### codebase_community_633

- question: Which post by slashnick has the most answers count? State the post ID.
- expected: `SELECT T2.PostId FROM users AS T1 INNER JOIN postHistory AS T2 ON T1.Id = T2.UserId INNER JOIN posts AS T3 ON T2.PostId = T3.Id WHERE T1.DisplayName = 'slashnick' ORDER BY T3.AnswerCount DESC LIMIT 1`
- agent: `SELECT Id, PostTypeId, AnswerCount, OwnerUserId, OwnerDisplayName, Title FROM posts WHERE OwnerUserId = 16 OR OwnerDisplayName LIKE '%slashnick%' OR OwnerDisplayName LIKE '%Slashnick%';`

### codebase_community_634

- question: Among posts by Harvey Motulsky and Noah Snyder, which one has higher popularity?
- expected: `SELECT T1.DisplayName FROM users AS T1 INNER JOIN postHistory AS T2 ON T1.Id = T2.UserId INNER JOIN posts AS T3 ON T2.PostId = T3.Id WHERE T1.DisplayName = 'Harvey Motulsky' OR T1.DisplayName = 'Noah Snyder' GROUP BY T1.DisplayName ORDER BY SUM(T3.ViewCount) DESC LIMIT 1`
- agent: `SELECT u.DisplayName, COUNT(p.Id) AS NumPosts, COALESCE(SUM(p.ViewCount), 0) AS TotalViewCount FROM users u LEFT JOIN posts p ON p.OwnerUserId = u.Id WHERE u.DisplayName IN ('Harvey Motulsky', 'Noah Snyder') GROUP BY u.Id, u.DisplayName ORDER BY TotalViewCount DESC`

### codebase_community_640

- question: Calculate the difference in view count from post posted by Mornington and view count from posts posted by Amos.
- expected: `SELECT SUM(IIF(T1.DisplayName = 'Mornington', T3.ViewCount, 0)) - SUM(IIF(T1.DisplayName = 'Amos', T3.ViewCount, 0)) AS diff FROM users AS T1 INNER JOIN postHistory AS T2 ON T1.Id = T2.UserId INNER JOIN posts AS T3 ON T3.Id = T2.PostId`
- agent: `SELECT u.DisplayName, COALESCE(SUM(p.ViewCount), 0) AS total_views FROM users u LEFT JOIN posts p ON p.OwnerUserId = u.Id WHERE u.DisplayName IN ('mornington', 'Amos') GROUP BY u.DisplayName`

### codebase_community_685

- question: Identify the total views on the post 'Computer Game Datasets'. Name the user who posted it last time.
- expected: `SELECT T2.ViewCount, T3.DisplayName FROM postHistory AS T1 INNER JOIN posts AS T2 ON T1.PostId = T2.Id INNER JOIN users AS T3 ON T2.LastEditorUserId = T3.Id WHERE T1.Text = 'Computer Game Datasets'`
- agent: `SELECT Id, DisplayName, Reputation FROM users WHERE Id IN (37, 88)`

### debit_card_specializing_1481

- question: What is the difference in the annual average consumption of the customers with the least amount of consumption paid in CZK for 2013 between SME and LAM, LAM and KAM, and KAM and SME?
- expected: `SELECT CAST(SUM(IIF(T1.Segment = 'SME', T2.Consumption, 0)) AS REAL) / COUNT(T1.CustomerID) - CAST(SUM(IIF(T1.Segment = 'LAM', T2.Consumption, 0)) AS REAL) / COUNT(T1.CustomerID) , CAST(SUM(IIF(T1.Segment = 'LAM', T2.Consumption, 0)) AS REAL) / COUNT(T1.CustomerID) - CAST(SUM(IIF(T1.Segment = 'KAM', T2.Consumption, 0)) AS REAL) / COUNT(T1.CustomerID) , CAST(SUM(IIF(T1.Segment = 'KAM', T2.Consumption, 0)) AS REAL) / COUNT(T1.CustomerID) - CAST(SUM(IIF(T1.Segment = 'SME', T2.Consumption, 0)) AS REAL) / COUNT(T1.CustomerID) FROM customers AS T1 INNER JOIN yearmonth AS T2 ON T1.CustomerID = T2.CustomerID WHERE T1.Currency = 'CZK' AND T2.Consumption = ( SELECT MIN(Consumption) FROM yearmonth ) AND T2.Date BETWEEN 201301 AND 201312`
- agent: `WITH per_customer AS ( SELECT c.Segment, c.CustomerID, SUM(ym.Consumption) AS total FROM yearmonth ym JOIN customers c ON c.CustomerID = ym.CustomerID WHERE c.Currency = 'CZK' AND ym.Date BETWEEN '201301' AND '201312' GROUP BY c.Segment, c.CustomerID ), min_per_segment AS ( SELECT Segment, MIN(total) AS min_total FROM per_customer GROUP BY Segment ), avg_per_segment AS ( SELECT pc.Segment, SUM(pc.total)/COUNT(*) AS annual_avg FROM per_customer pc JOIN min_per_segment ms ON pc.Segment = ms.Segment AND pc.total = ms.min_total GROUP BY pc.Segment ) SELECT ROUND((SELECT annual_avg FROM avg_per_segment WHERE Segment='SME') - (SELECT annual_avg FROM avg_per_segment WHERE Segment='LAM'), 2) AS SME_minus_LAM, ROUND((SELECT annual_avg FROM avg_per_segment WHERE Segment='LAM') - (SELECT annual_avg FROM avg_per_segment WHERE Segment='KAM'), 2) AS LAM_minus_KAM, ROUND((SELECT annual_avg FROM avg_per_segment WHERE Segment='KAM') - (SELECT annual_avg FROM avg_per_segment WHERE Segment='SME'), 2) AS KAM_minus_SME`

### debit_card_specializing_1484

- question: How many more "discount" gas stations does the Czech Republic have compared to Slovakia?
- expected: `SELECT SUM(IIF(Country = 'CZE', 1, 0)) - SUM(IIF(Country = 'SVK', 1, 0)) FROM gasstations WHERE Segment = 'Discount'`
- agent: `SELECT SUM(CASE WHEN Country = 'CZE' THEN 1 ELSE 0 END) AS cze_discount, SUM(CASE WHEN Country = 'SVK' THEN 1 ELSE 0 END) AS svk_discount, SUM(CASE WHEN Country = 'CZE' THEN 1 ELSE 0 END) - SUM(CASE WHEN Country = 'SVK' THEN 1 ELSE 0 END) AS difference FROM gasstations WHERE Segment = 'Discount' AND Country IN ('CZE', 'SVK')`

### european_football_2_1079

- question: Which player is the tallest?
- expected: `SELECT player_name FROM Player ORDER BY height DESC LIMIT 1`
- agent: `SELECT player_name, height FROM Player WHERE height = (SELECT MAX(height) FROM Player);`

### european_football_2_1134

- question: What is the difference between players 6 and 23's jumping scores?
- expected: `SELECT SUM(CASE WHEN t1.id = 6 THEN t1.jumping ELSE 0 END) - SUM(CASE WHEN t1.id = 23 THEN t1.jumping ELSE 0 END) FROM Player_Attributes AS t1`
- agent: `WITH latest AS ( SELECT pa.player_api_id, pa.jumping FROM Player_Attributes pa JOIN Player p ON p.player_api_id = pa.player_api_id WHERE p.id IN (6, 23) AND pa.date = (SELECT MAX(pa2.date) FROM Player_Attributes pa2 WHERE pa2.player_api_id = pa.player_api_id) ) SELECT (SELECT jumping FROM latest WHERE player_api_id = (SELECT player_api_id FROM Player WHERE id = 6)) - (SELECT jumping FROM latest WHERE player_api_id = (SELECT player_api_id FROM Player WHERE id = 23)) AS difference`

### european_football_2_1135

- question: Please provide top four football players' IDs who are among the lowest potential players and prefer to use the right foot when attacking.
- expected: `SELECT id FROM Player_Attributes WHERE preferred_foot = 'right' ORDER BY potential ASC LIMIT 4`
- agent: `SELECT id, player_api_id, player_name FROM Player WHERE player_api_id = 41496`

### financial_115

- question: For the branch which located in the south Bohemia with biggest number of inhabitants, what is the percentage of the male clients?
- expected: `SELECT CAST(SUM(T1.gender = 'M') AS REAL) * 100 / COUNT(T1.client_id) FROM client AS T1 INNER JOIN district AS T2 ON T1.district_id = T2.district_id WHERE T2.A3 = 'south Bohemia' GROUP BY T2.A4 ORDER BY T2.A4 DESC LIMIT 1`
- agent: `SELECT COUNT(*) AS total_clients, SUM(CASE WHEN gender = 'M' THEN 1 ELSE 0 END) AS male_clients, ROUND(100.0 * SUM(CASE WHEN gender = 'M' THEN 1 ELSE 0 END) / COUNT(*), 2) AS male_pct FROM client WHERE district_id = 14`

### financial_117

- question: What is the percentage of loan amount that has been fully paid with no issue.
- expected: `SELECT (CAST(SUM(CASE WHEN status = 'A' THEN amount ELSE 0 END) AS REAL) * 100) / SUM(amount) FROM loan`
- agent: `SELECT ROUND(100.0 * SUM(CASE WHEN status = 'A' THEN amount ELSE 0 END) / SUM(amount), 2) AS pct_fully_paid FROM loan;`

### financial_128

- question: List the top nine districts, by descending order, from the highest to the lowest, the number of female account holders.
- expected: `SELECT T2.A2, COUNT(T1.client_id) FROM client AS T1 INNER JOIN district AS T2 ON T1.district_id = T2.district_id WHERE T1.gender = 'F' GROUP BY T2.district_id, T2.A2 ORDER BY COUNT(T1.client_id) DESC LIMIT 9`
- agent: `SELECT d.A2 AS district, COUNT(DISTINCT c.client_id) AS female_holders FROM disp di JOIN client c ON di.client_id = c.client_id JOIN account a ON di.account_id = a.account_id JOIN district d ON a.district_id = d.district_id WHERE c.gender = 'F' GROUP BY d.A2 ORDER BY female_holders DESC LIMIT 9`

### financial_159

- question: List all the withdrawals in cash transactions that the client with the id 3356 makes.
- expected: `SELECT T4.trans_id FROM client AS T1 INNER JOIN disp AS T2 ON T1.client_id = T2.client_id INNER JOIN account AS T3 ON T2.account_id = T3.account_id INNER JOIN trans AS T4 ON T3.account_id = T4.account_id WHERE T1.client_id = 3356 AND T4.operation = 'VYBER'`
- agent: `SELECT t.trans_id, t.account_id, t.date, t.amount, t.balance, t.k_symbol FROM trans t JOIN disp d ON d.account_id = t.account_id JOIN client c ON c.client_id = d.client_id WHERE c.client_id = 3356 AND t.operation = 'VYBER' ORDER BY t.date, t.trans_id;`

### financial_168

- question: What percentage of clients who opened their accounts in the district with an average salary of over 10000 are women?
- expected: `SELECT CAST(SUM(T2.gender = 'F') AS REAL) * 100 / COUNT(T2.client_id) FROM district AS T1 INNER JOIN client AS T2 ON T1.district_id = T2.district_id WHERE T1.A11 > 10000`
- agent: `WITH eligible_clients AS ( SELECT DISTINCT c.client_id, c.gender FROM client c JOIN disp d ON d.client_id = c.client_id JOIN account a ON a.account_id = d.account_id JOIN district di ON di.district_id = a.district_id WHERE di.A11 > 10000 ) SELECT COUNT(*) AS total_clients, SUM(CASE WHEN gender = 'F' THEN 1 ELSE 0 END) AS women, 100.0 * SUM(CASE WHEN gender = 'F' THEN 1 ELSE 0 END) / COUNT(*) AS pct_women FROM eligible_clients;`

### financial_169

- question: What was the growth rate of the total amount of loans across all accounts for a male client between 1996 and 1997?
- expected: `SELECT CAST((SUM(CASE WHEN STRFTIME('%Y', T1.date) = '1997' THEN T1.amount ELSE 0 END) - SUM(CASE WHEN STRFTIME('%Y', T1.date) = '1996' THEN T1.amount ELSE 0 END)) AS REAL) * 100 / SUM(CASE WHEN STRFTIME('%Y', T1.date) = '1996' THEN T1.amount ELSE 0 END) FROM loan AS T1 INNER JOIN account AS T2 ON T1.account_id = T2.account_id INNER JOIN disp AS T3 ON T3.account_id = T2.account_id INNER JOIN client AS T4 ON T4.client_id = T3.client_id WHERE T4.gender = 'M' AND T3.type = 'OWNER'`
- agent: `WITH male_accounts AS ( SELECT DISTINCT d.account_id FROM disp d JOIN client c ON c.client_id = d.client_id WHERE c.gender = 'M' ), totals AS ( SELECT SUM(CASE WHEN substr(l.date,1,4) = '1996' THEN l.amount ELSE 0 END) AS amt_1996, SUM(CASE WHEN substr(l.date,1,4) = '1997' THEN l.amount ELSE 0 END) AS amt_1997 FROM loan l WHERE l.account_id IN (SELECT account_id FROM male_accounts) AND substr(l.date,1,4) IN ('1996','1997') ) SELECT amt_1996, amt_1997, ROUND((amt_1997 - amt_1996) * 100.0 / amt_1996, 2) AS growth_pct FROM totals;`

### financial_189

- question: Name the account numbers of female clients who are oldest and have lowest average salary?
- expected: `SELECT T3.account_id FROM client AS T1 INNER JOIN district AS T2 ON T1.district_id = T2.district_id INNER JOIN account AS T3 ON T2.district_id = T3.district_id INNER JOIN disp AS T4 ON T1.client_id = T4.client_id AND T4.account_id = T3.account_id WHERE T1.gender = 'F' ORDER BY T1.birth_date ASC, T2.A11 ASC LIMIT 1`
- agent: `SELECT type, COUNT(*) FROM disp GROUP BY type`

### formula_1_877

- question: For all the drivers who finished the game in race No. 872, who is the youngest?
- expected: `SELECT T1.forename, T1.surname FROM drivers AS T1 INNER JOIN results AS T2 ON T2.driverId = T1.driverId WHERE T2.raceId = 872 AND T2.time IS NOT NULL ORDER BY T1.dob DESC LIMIT 1`
- agent: `SELECT d.forename, d.surname, d.dob FROM results r JOIN drivers d ON d.driverId = r.driverId WHERE r.raceId = 872 AND r.time IS NOT NULL ORDER BY d.dob DESC LIMIT 1;`

### formula_1_897

- question: Name the driver with the most winning. Mention his nationality and what is his maximum point scores.
- expected: `SELECT T1.forename, T1.surname, T1.nationality, MAX(T2.points) FROM drivers AS T1 INNER JOIN driverStandings AS T2 ON T2.driverId = T1.driverId WHERE T2.wins >= 1 GROUP BY T1.forename, T1.surname, T1.nationality ORDER BY COUNT(T2.wins) DESC LIMIT 1`
- agent: `WITH wins AS ( SELECT driverId, COUNT(*) AS win_count FROM results WHERE positionOrder = 1 GROUP BY driverId ), max_wins AS ( SELECT MAX(win_count) AS max_win_count FROM wins ) SELECT d.forename || ' ' || d.surname AS driver_name, d.nationality, w.win_count, MAX(r.points) AS max_points_single_race FROM wins w JOIN max_wins mw ON w.win_count = mw.max_win_count JOIN drivers d ON d.driverId = w.driverId JOIN results r ON r.driverId = w.driverId GROUP BY d.driverId, d.forename, d.surname, d.nationality, w.win_count;`

### formula_1_906

- question: Which was Lewis Hamilton first race? What was his points recorded for his first race event?
- expected: `SELECT T1.name, T2.points FROM races AS T1 INNER JOIN driverStandings AS T2 ON T2.raceId = T1.raceId INNER JOIN drivers AS T3 ON T3.driverId = T2.driverId WHERE T3.forename = 'Lewis' AND T3.surname = 'Hamilton' ORDER BY T1.year ASC LIMIT 1`
- agent: `SELECT r.year, r.round, r.name, res.points, res.position FROM drivers d JOIN results res ON d.driverId = res.driverId JOIN races r ON res.raceId = r.raceId WHERE d.forename = 'Lewis' AND d.surname = 'Hamilton' AND r.year = 2007 ORDER BY r.round ASC;`

### formula_1_955

- question: What is the average time in seconds of champion for each year, before year 1975?
- expected: `WITH time_in_seconds AS ( SELECT T2.year, T2.raceId, T1.positionOrder, CASE WHEN T1.positionOrder = 1 THEN (CAST(SUBSTR(T1.time, 1, 1) AS REAL) * 3600) + (CAST(SUBSTR(T1.time, 3, 2) AS REAL) * 60) + CAST(SUBSTR(T1.time, 6,2) AS REAL ) + CAST(SUBSTR(T1.time, 9) AS REAL)/1000 ELSE 0 END AS time_seconds FROM results AS T1 INNER JOIN races AS T2 ON T1.raceId = T2.raceId WHERE T1.time IS NOT NULL ), champion_time AS ( SELECT year, raceId, time_seconds FROM time_in_seconds WHERE positionOrder = 1 ) SELECT year, AVG(time_seconds) FROM champion_time WHERE year < 1975 GROUP BY year HAVING AVG(time_seconds) IS NOT NULL`
- agent: `WITH last_race AS ( SELECT year, MAX(round) AS max_round FROM races WHERE year < 1975 GROUP BY year ), champ AS ( SELECT DISTINCT r.year, ds.driverId FROM races r JOIN driverStandings ds ON ds.raceId = r.raceId JOIN last_race lr ON lr.year = r.year AND lr.max_round = r.round WHERE r.year < 1975 AND ds.position = 1 ), champ_times AS ( SELECT c.year, res.time, CAST(substr(res.time, 1, instr(res.time, ':') - 1) AS REAL) * 3600 + CAST(substr(substr(res.time, instr(res.time, ':') + 1), 1, instr(substr(res.time, instr(res.time, ':') + 1), ':') - 1) AS REAL) * 60 + CAST(substr(substr(res.time, instr(res.time, ':') + 1), instr(substr(res.time, instr(res.time, ':') + 1), ':') + 1) AS REAL) AS seconds FROM champ c JOIN races r ON r.year = c.year JOIN results res ON res.raceId = r.raceId AND res.driverId = c.driverId WHERE res.time IS NOT NULL AND res.time LIKE '%:%:%' ) SELECT year, COUNT(*) AS n, ROUND(AVG(seconds), 3) AS avg_seconds FROM champ_times GROUP BY year ORDER BY year`

### formula_1_972

- question: Which drivers who were born in 1971 and has the fastest lap time on the race? Give id and code of these drivers.
- expected: `SELECT T2.driverId, T2.code FROM results AS T1 INNER JOIN drivers AS T2 on T1.driverId = T2.driverId WHERE STRFTIME('%Y', T2.dob) = '1971' AND T1.fastestLapTime IS NOT NULL`
- agent: `SELECT DISTINCT d.driverId, d.code FROM drivers d JOIN results r ON d.driverId = r.driverId WHERE CAST(strftime('%Y', d.dob) AS INTEGER) = 1971 AND r.fastestLapTime IS NOT NULL AND r.fastestLapTime != '' ORDER BY d.driverId;`

### formula_1_990

- question: What is the constructor reference name of the champion in the 2009 Singapore Grand Prix? Please give its website.
- expected: `SELECT T3.constructorRef, T3.url FROM results AS T1 INNER JOIN races AS T2 on T1.raceId = T2.raceId INNER JOIN constructors AS T3 on T1.constructorId = T3.constructorId WHERE T2.name = 'Singapore Grand Prix' AND T2.year = 2009 AND T1.time LIKE '_:%:__.___'`
- agent: `WITH champ AS ( SELECT driverId, constructorId FROM results WHERE raceId = 14 AND time IS NOT NULL ORDER BY time DESC LIMIT 1 ) SELECT c.constructorRef, c.name, c.url, d.forename, d.surname FROM champ JOIN constructors c ON c.constructorId = champ.constructorId JOIN drivers d ON d.driverId = champ.driverId;`

### student_club_1350

- question: What is the status of the event which bought "Post Cards, Posters" on 2019/8/20?
- expected: `SELECT T1.event_status FROM budget AS T1 INNER JOIN expense AS T2 ON T1.budget_id = T2.link_to_budget WHERE T2.expense_description = 'Post Cards, Posters' AND T2.expense_date = '2019-08-20'`
- agent: `SELECT e.expense_id, e.expense_description, e.expense_date, e.link_to_budget, b.budget_id, b.event_status FROM expense e LEFT JOIN budget b ON e.link_to_budget = b.budget_id WHERE e.expense_description LIKE '%Post Cards%' OR e.expense_date LIKE '%2019-8%' OR e.expense_date LIKE '%2019/8%'`

### student_club_1376

- question: Among all the closed events, which event has the highest spend-to-budget ratio?
- expected: `SELECT T2.event_name FROM budget AS T1 INNER JOIN event AS T2 ON T1.link_to_event = T2.event_id WHERE T2.status = 'Closed' ORDER BY T1.spent / T1.amount DESC LIMIT 1`
- agent: `SELECT e.event_name, b.spent, b.amount, b.spent * 1.0 / b.amount AS ratio FROM event e JOIN budget b ON b.link_to_event = e.event_id WHERE e.status = 'Closed' ORDER BY ratio DESC LIMIT 5`

### student_club_1399

- question: Did Maya Mclean attend the 'Women's Soccer' event?
- expected: `SELECT CASE WHEN T3.event_name = 'Women''s Soccer' THEN 'YES' END AS result FROM member AS T1 INNER JOIN attendance AS T2 ON T1.member_id = T2.link_to_member INNER JOIN event AS T3 ON T2.link_to_event = T3.event_id WHERE T1.first_name = 'Maya' AND T1.last_name = 'Mclean'`
- agent: `SELECT a.link_to_member, a.link_to_event FROM attendance a WHERE a.link_to_member = 'recZ4PkGERzl9ziHO' AND a.link_to_event = 'rec2N69DMcrqN9PJC';`

### student_club_1422

- question: State the category of events were held at MU 215.
- expected: `SELECT DISTINCT T2.category FROM event AS T1 INNER JOIN budget AS T2 ON T1.event_id = T2.link_to_event WHERE T1.location = 'MU 215'`
- agent: `SELECT DISTINCT type FROM event WHERE location = 'MU 215';`

### superhero_728

- question: Rank superheroes from Marvel Comics by their eye color popularity, starting with the most common color.
- expected: `SELECT colour.colour AS EyeColor, COUNT(superhero.id) AS Count, RANK() OVER (ORDER BY COUNT(superhero.id) DESC) AS PopularityRank FROM superhero INNER JOIN colour ON superhero.eye_colour_id = colour.id INNER JOIN publisher ON superhero.publisher_id = publisher.id WHERE publisher.publisher_name = 'Marvel Comics' GROUP BY colour.colour`
- agent: `SELECT c.colour, COUNT(s.id) AS hero_count FROM superhero s JOIN publisher p ON s.publisher_id = p.id JOIN colour c ON s.eye_colour_id = c.id WHERE p.publisher_name = 'Marvel Comics' GROUP BY c.colour ORDER BY hero_count DESC, c.colour`

### superhero_730

- question: List the superheroes from Marvel Comics who have the super power of 'Super Strength'.
- expected: `SELECT superhero_name FROM superhero AS T1 WHERE EXISTS (SELECT 1 FROM hero_power AS T2 INNER JOIN superpower AS T3 ON T2.power_id = T3.id WHERE T3.power_name = 'Super Strength' AND T1.id = T2.hero_id)AND EXISTS (SELECT 1 FROM publisher AS T4 WHERE T4.publisher_name = 'Marvel Comics' AND T1.publisher_id = T4.id)`
- agent: `SELECT s.superhero_name, COUNT(DISTINCT s.id) AS cnt FROM superhero s JOIN publisher p ON s.publisher_id = p.id JOIN hero_power hp ON s.id = hp.hero_id JOIN superpower sp ON hp.power_id = sp.id WHERE p.publisher_name = 'Marvel Comics' AND sp.power_name = 'Super Strength' GROUP BY s.superhero_name HAVING COUNT(DISTINCT s.id) > 1;`

### superhero_751

- question: List down at least five superpowers of male superheroes.
- expected: `SELECT T3.power_name FROM superhero AS T1 INNER JOIN hero_power AS T2 ON T1.id = T2.hero_id INNER JOIN superpower AS T3 ON T3.id = T2.power_id INNER JOIN gender AS T4 ON T4.id = T1.gender_id WHERE T4.gender = 'Male' LIMIT 5`
- agent: `SELECT DISTINCT sp.power_name FROM superhero s JOIN gender g ON s.gender_id = g.id JOIN hero_power hp ON hp.hero_id = s.id JOIN superpower sp ON sp.id = hp.power_id WHERE g.gender = 'Male' ORDER BY sp.power_name;`

### thrombosis_prediction_1168

- question: The oldest SJS patient's medical laboratory work was completed on what date, and what age was the patient when they initially arrived at the hospital?
- expected: `SELECT T1.Date, STRFTIME('%Y', T2.`First Date`) - STRFTIME('%Y', T2.Birthday),T2.Birthday FROM Laboratory AS T1 INNER JOIN Patient AS T2 ON T1.ID = T2.ID WHERE T2.Diagnosis = 'SJS' AND T2.Birthday IS NOT NULL ORDER BY T2.Birthday ASC LIMIT 1`
- agent: `SELECT MAX(L.Date) AS LabCompletionDate, CAST(STRFTIME('%Y', P.[First Date]) AS INTEGER) - CAST(STRFTIME('%Y', P.Birthday) AS INTEGER) AS AgeAtArrival FROM Patient P JOIN Laboratory L ON L.ID = P.ID WHERE P.Diagnosis LIKE '%SJS%' AND P.Birthday = (SELECT MIN(Birthday) FROM Patient WHERE Diagnosis LIKE '%SJS%');`

### thrombosis_prediction_1252

- question: Among the patients with a normal Ig G level, how many of them have symptoms?
- expected: `SELECT COUNT(T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID INNER JOIN Examination AS T3 ON T3.ID = T2.ID WHERE T2.IGG BETWEEN 900 AND 2000 AND T3.Symptoms IS NOT NULL`
- agent: `SELECT COUNT(DISTINCT e.ID) AS patient_count FROM Laboratory l JOIN Examination e ON e.ID = l.ID WHERE l.IGG > 900 AND l.IGG < 2000 AND e.Symptoms IS NOT NULL;`

### thrombosis_prediction_1256

- question: How many patients with a abnormal C-reactive protein don't have their data recorded?
- expected: `SELECT COUNT(T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE (T2.CRP = '+' ) AND T1.Description IS NULL`
- agent: `SELECT COUNT(DISTINCT p.ID) AS patient_count FROM Patient p JOIN Laboratory l ON p.ID = l.ID WHERE l.CRP = '+' AND p.Description IS NULL;`

### toxicology_212

- question: Which element is the least numerous in non-carcinogenic molecules?
- expected: `SELECT T.element FROM (SELECT T1.element, COUNT(DISTINCT T1.molecule_id) FROM atom AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T2.label = '-' GROUP BY T1.element ORDER BY COUNT(DISTINCT T1.molecule_id) ASC LIMIT 1) t`
- agent: `SELECT a.element, COUNT(*) AS cnt FROM atom a JOIN molecule m ON a.molecule_id = m.molecule_id WHERE m.label = '-' GROUP BY a.element ORDER BY cnt ASC;`

### toxicology_282

- question: What is the ratio of Hydrogen elements in molecule ID TR006? List the ratio with its label.
- expected: `WITH SubQuery AS (SELECT DISTINCT T1.atom_id, T1.element, T1.molecule_id, T2.label FROM atom AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T2.molecule_id = 'TR006') SELECT CAST(COUNT(CASE WHEN element = 'h' THEN atom_id ELSE NULL END) AS REAL) / (CASE WHEN COUNT(atom_id) = 0 THEN NULL ELSE COUNT(atom_id) END) AS ratio, label FROM SubQuery GROUP BY label`
- agent: `SELECT m.label, SUM(CASE WHEN a.element = 'h' THEN 1 ELSE 0 END) * 1.0 / COUNT(a.element) AS ratio FROM atom a JOIN molecule m ON a.molecule_id = m.molecule_id WHERE a.molecule_id = 'TR006' GROUP BY m.label`

