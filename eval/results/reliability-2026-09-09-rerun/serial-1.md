# QueryAgent Eval Report — public subset

- model: `deepseek-v4-flash`
- cases: 100
- scoring: v2 (query trajectory and completion reported separately)
- Natural-language answer correctness is not measured.

## Summary

| metric | value |
|---|---|
| first-execution pass rate | 30/100 (30%) |
| query-trajectory hit rate | 43/100 (43%) |
| completed with SQL hit | 43/100 (43%) |
| metric hit rate | n/a |
| clarify-behaviour accuracy | n/a |
| average tool calls | 3.37 |
| tokens per case (in+out) | 13,068 |
| prompt cache hit rate | 85% |
| latency per case | 14.5s |
| cost per case (upper bound) | $0.0031 |
| unmeasured (upstream unreachable) | 0 |

## Cases

| id | kind | SQL hit | completed | first try | retries | tool calls | note |
|---|---|---|---|---|---|---|---|
| california_schools_36 | public | ❌ | ✅ | ❌ | 0 | 4 | result sets differ |
| california_schools_37 | public | ❌ | ❌ | ❌ | 0 | 8 | no final answer after 8 turns |
| california_schools_39 | public | ❌ | ❌ | ❌ | 0 | 8 | no final answer after 8 turns |
| california_schools_41 | public | ❌ | ❌ | ❌ | 0 | 8 | no final answer after 8 turns |
| california_schools_45 | public | ✅ | ✅ | ❌ | 0 | 3 |  |
| california_schools_72 | public | ❌ | ✅ | ❌ | 0 | 6 | result sets differ |
| california_schools_85 | public | ❌ | ✅ | ❌ | 0 | 3 | result sets differ |
| card_games_340 | public | ❌ | ✅ | ❌ | 0 | 3 | result sets differ |
| card_games_345 | public | ✅ | ✅ | ✅ | 0 | 1 |  |
| card_games_346 | public | ❌ | ✅ | ❌ | 0 | 4 | result sets differ |
| card_games_358 | public | ❌ | ✅ | ❌ | 0 | 1 | result sets differ |
| card_games_368 | public | ✅ | ✅ | ✅ | 0 | 1 |  |
| card_games_379 | public | ✅ | ✅ | ✅ | 0 | 4 |  |
| card_games_397 | public | ❌ | ✅ | ❌ | 0 | 5 | result sets differ |
| card_games_407 | public | ❌ | ❌ | ❌ | 0 | 8 | no final answer after 8 turns |
| card_games_409 | public | ✅ | ✅ | ✅ | 0 | 1 |  |
| card_games_412 | public | ❌ | ❌ | ❌ | 0 | 8 | no final answer after 8 turns |
| card_games_415 | public | ✅ | ✅ | ❌ | 0 | 7 |  |
| card_games_422 | public | ❌ | ✅ | ❌ | 0 | 1 | result sets differ |
| card_games_459 | public | ❌ | ✅ | ❌ | 0 | 1 | result sets differ |
| card_games_468 | public | ✅ | ✅ | ✅ | 0 | 1 |  |
| card_games_479 | public | ✅ | ✅ | ✅ | 0 | 1 |  |
| card_games_480 | public | ❌ | ✅ | ❌ | 0 | 4 | result sets differ |
| codebase_community_539 | public | ✅ | ✅ | ✅ | 0 | 1 |  |
| codebase_community_557 | public | ✅ | ✅ | ✅ | 0 | 1 |  |
| codebase_community_573 | public | ✅ | ✅ | ✅ | 0 | 1 |  |
| codebase_community_581 | public | ✅ | ✅ | ✅ | 0 | 1 |  |
| codebase_community_604 | public | ❌ | ✅ | ❌ | 0 | 3 | result sets differ |
| codebase_community_633 | public | ❌ | ❌ | ❌ | 0 | 8 | no final answer after 8 turns |
| codebase_community_634 | public | ❌ | ✅ | ❌ | 1 | 7 | result sets differ |
| codebase_community_640 | public | ❌ | ✅ | ❌ | 0 | 6 | result sets differ |
| codebase_community_678 | public | ❌ | ✅ | ❌ | 0 | 2 | result sets differ |
| codebase_community_685 | public | ❌ | ✅ | ❌ | 1 | 7 | result sets differ |
| codebase_community_701 | public | ❌ | ❌ | ❌ | 0 | 4 | reference expected_sql failed (case bug?): interrupted |
| codebase_community_707 | public | ✅ | ✅ | ✅ | 0 | 3 |  |
| debit_card_specializing_1481 | public | ❌ | ❌ | ❌ | 1 | 8 | no final answer after 8 turns |
| debit_card_specializing_1484 | public | ✅ | ✅ | ❌ | 0 | 2 |  |
| european_football_2_1030 | public | ❌ | ✅ | ❌ | 0 | 1 | result sets differ |
| european_football_2_1079 | public | ❌ | ✅ | ❌ | 0 | 1 | result sets differ |
| european_football_2_1134 | public | ✅ | ✅ | ❌ | 0 | 4 |  |
| european_football_2_1135 | public | ❌ | ❌ | ❌ | 0 | 8 | no final answer after 8 turns |
| financial_115 | public | ❌ | ❌ | ❌ | 0 | 8 | no final answer after 8 turns |
| financial_117 | public | ❌ | ✅ | ❌ | 0 | 1 | result sets differ |
| financial_128 | public | ❌ | ✅ | ❌ | 0 | 1 | result sets differ |
| financial_159 | public | ❌ | ❌ | ❌ | 0 | 8 | no final answer after 8 turns |
| financial_168 | public | ❌ | ✅ | ❌ | 0 | 6 | result sets differ |
| financial_169 | public | ❌ | ✅ | ❌ | 0 | 6 | result sets differ |
| financial_189 | public | ❌ | ✅ | ❌ | 0 | 6 | result sets differ |
| financial_92 | public | ✅ | ✅ | ❌ | 0 | 6 |  |
| financial_93 | public | ✅ | ✅ | ❌ | 0 | 2 |  |
| financial_95 | public | ❌ | ❌ | ❌ | 0 | 8 | no final answer after 8 turns |
| formula_1_866 | public | ❌ | ❌ | ❌ | 0 | 8 | no final answer after 8 turns |
| formula_1_869 | public | ❌ | ✅ | ❌ | 0 | 1 | result sets differ |
| formula_1_877 | public | ❌ | ✅ | ❌ | 0 | 2 | result sets differ |
| formula_1_897 | public | ❌ | ✅ | ❌ | 0 | 5 | result sets differ |
| formula_1_906 | public | ❌ | ✅ | ❌ | 0 | 3 | result sets differ |
| formula_1_909 | public | ✅ | ✅ | ✅ | 0 | 1 |  |
| formula_1_910 | public | ✅ | ✅ | ✅ | 0 | 1 |  |
| formula_1_940 | public | ✅ | ✅ | ❌ | 0 | 3 |  |
| formula_1_955 | public | ❌ | ✅ | ❌ | 0 | 5 | result sets differ |
| formula_1_960 | public | ✅ | ✅ | ✅ | 0 | 1 |  |
| formula_1_972 | public | ❌ | ✅ | ❌ | 0 | 1 | result sets differ |
| formula_1_977 | public | ✅ | ✅ | ✅ | 0 | 1 |  |
| formula_1_990 | public | ❌ | ✅ | ❌ | 0 | 2 | result sets differ |
| student_club_1317 | public | ❌ | ❌ | ❌ | 0 | 8 | no final answer after 8 turns |
| student_club_1346 | public | ✅ | ✅ | ✅ | 0 | 1 |  |
| student_club_1350 | public | ✅ | ✅ | ❌ | 0 | 3 |  |
| student_club_1352 | public | ✅ | ✅ | ✅ | 0 | 1 |  |
| student_club_1361 | public | ✅ | ✅ | ✅ | 0 | 2 |  |
| student_club_1376 | public | ❌ | ✅ | ❌ | 0 | 6 | result sets differ |
| student_club_1378 | public | ✅ | ✅ | ✅ | 0 | 1 |  |
| student_club_1399 | public | ❌ | ✅ | ❌ | 0 | 2 | result sets differ |
| student_club_1405 | public | ✅ | ✅ | ❌ | 0 | 3 |  |
| student_club_1409 | public | ✅ | ✅ | ✅ | 0 | 1 |  |
| student_club_1422 | public | ❌ | ✅ | ❌ | 0 | 1 | result sets differ |
| student_club_1426 | public | ✅ | ✅ | ✅ | 0 | 2 |  |
| superhero_717 | public | ✅ | ✅ | ✅ | 0 | 1 |  |
| superhero_719 | public | ✅ | ✅ | ✅ | 0 | 1 |  |
| superhero_728 | public | ❌ | ✅ | ❌ | 0 | 1 | result sets differ |
| superhero_730 | public | ❌ | ✅ | ❌ | 0 | 5 | result sets differ |
| superhero_733 | public | ✅ | ✅ | ✅ | 0 | 1 |  |
| superhero_751 | public | ❌ | ✅ | ❌ | 0 | 1 | result sets differ |
| superhero_758 | public | ❌ | ✅ | ❌ | 0 | 5 | result sets differ |
| superhero_765 | public | ✅ | ✅ | ✅ | 0 | 1 |  |
| superhero_806 | public | ✅ | ✅ | ✅ | 0 | 1 |  |
| thrombosis_prediction_1168 | public | ❌ | ❌ | ❌ | 0 | 7 | no final answer after 8 turns |
| thrombosis_prediction_1195 | public | ✅ | ✅ | ❌ | 0 | 3 |  |
| thrombosis_prediction_1201 | public | ✅ | ✅ | ✅ | 0 | 2 |  |
| thrombosis_prediction_1209 | public | ❌ | ✅ | ❌ | 0 | 4 | result sets differ |
| thrombosis_prediction_1252 | public | ❌ | ✅ | ❌ | 0 | 7 | result sets differ |
| thrombosis_prediction_1256 | public | ❌ | ✅ | ❌ | 0 | 2 | result sets differ |
| thrombosis_prediction_1270 | public | ✅ | ✅ | ✅ | 0 | 2 |  |
| toxicology_200 | public | ✅ | ✅ | ✅ | 0 | 2 |  |
| toxicology_206 | public | ✅ | ✅ | ❌ | 0 | 3 |  |
| toxicology_212 | public | ❌ | ✅ | ❌ | 0 | 2 | result sets differ |
| toxicology_228 | public | ✅ | ✅ | ❌ | 0 | 2 |  |
| toxicology_242 | public | ✅ | ✅ | ❌ | 0 | 4 |  |
| toxicology_268 | public | ❌ | ✅ | ❌ | 0 | 1 | result sets differ |
| toxicology_282 | public | ❌ | ✅ | ❌ | 0 | 1 | result sets differ |
| toxicology_327 | public | ✅ | ✅ | ✅ | 0 | 2 |  |

## Failing cases — SQL comparison

### california_schools_36

- question: Under whose administration is the school with the highest number of students scoring 1500 or more on the SAT? Indicate their full names.
- expected: `SELECT T2.AdmFName1, T2.AdmLName1, T2.AdmFName2, T2.AdmLName2, T2.AdmFName3, T2.AdmLName3 FROM satscores AS T1 INNER JOIN schools AS T2 ON T1.cds = T2.CDSCode ORDER BY T1.NumGE1500 DESC LIMIT 1`
- agent: `SELECT CDSCode, School, AdmFName1, AdmLName1, AdmFName2, AdmLName2, AdmFName3, AdmLName3 FROM schools WHERE CDSCode = '38684783833407';`

### california_schools_37

- question: What is the complete address of the school with the lowest excellence rate? Indicate the Street, City, Zip and State.
- expected: `SELECT T2.Street, T2.City, T2.State, T2.Zip FROM satscores AS T1 INNER JOIN schools AS T2 ON T1.cds = T2.CDSCode ORDER BY CAST(T1.NumGE1500 AS REAL) / T1.NumTstTakr ASC LIMIT 1`
- agent: `SELECT sc.CDSCode, sc.School, sc.DOCType, sc.SOCType, sc.EILName, sc.StatusType FROM schools sc WHERE sc.CDSCode IN ( SELECT s.cds FROM satscores s WHERE s.rtype = 'S' AND s.NumTstTakr > 0 AND s.NumGE1500 = 0 ) ORDER BY sc.CDSCode;`

### california_schools_39

- question: What is the average number of test takers from Fresno schools that opened between 1/1/1980 and 12/31/1980?
- expected: `SELECT AVG(T1.NumTstTakr) FROM satscores AS T1 INNER JOIN schools AS T2 ON T1.cds = T2.CDSCode WHERE strftime('%Y', T2.OpenDate) = '1980' AND T2.County = 'Fresno'`
- agent: `SELECT COUNT(*) AS matched_rows, COUNT(DISTINCT s.cds) AS matched_schools, COUNT(DISTINCT sc.CDSCode) AS sc_codes FROM satscores s JOIN schools sc ON s.cds = sc.CDSCode WHERE sc.County='Fresno' AND sc.OpenDate BETWEEN '1980-01-01' AND '1980-12-31' AND s.rtype='S';`

### california_schools_41

- question: List the names of virtual schools that are among the top 5 in their respective counties based on average reading scores.
- expected: `SELECT School FROM (SELECT T2.School,T1.AvgScrRead, RANK() OVER (PARTITION BY T2.County ORDER BY T1.AvgScrRead DESC) AS rnk FROM satscores AS T1 INNER JOIN schools AS T2 ON T1.cds = T2.CDSCode WHERE T2.Virtual = 'F' ) ranked_schools WHERE rnk <= 5`
- agent: `WITH ranked AS ( SELECT sc.School, sc.County, sc.Virtual, s.AvgScrRead, ROW_NUMBER() OVER (PARTITION BY sc.County ORDER BY s.AvgScrRead DESC) AS rn FROM satscores s JOIN schools sc ON s.cds = sc.CDSCode WHERE s.rtype='S' AND s.AvgScrRead IS NOT NULL ) SELECT School, County, AvgScrRead, Virtual, rn FROM ranked WHERE County IN ('San Joaquin','Los Angeles','Orange') AND rn <= 5 ORDER BY County, rn`

### california_schools_72

- question: How many students from the ages of 5 to 17 are enrolled at the State Special School school in Fremont for the 2014-2015 academic year?
- expected: `SELECT T1.`Enrollment (Ages 5-17)` FROM frpm AS T1 INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode WHERE T2.EdOpsCode = 'SSS' AND T2.City = 'Fremont' AND T1.`Academic Year` BETWEEN 2014 AND 2015`
- agent: `SELECT CDSCode, School, City, StatusType, OpenDate, ClosedDate FROM schools WHERE CDSCode IN ('01316090131755','01316170131763')`

### california_schools_85

- question: What is the Percent (%) Eligible Free (K-12) in the school administered by an administrator whose first name is Alusine. List the district code of the school.
- expected: `SELECT T1.`Free Meal Count (K-12)` * 100 / T1.`Enrollment (K-12)`, T1.`District Code` FROM frpm AS T1 INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode WHERE T2.AdmFName1 = 'Alusine'`
- agent: `SELECT frpm."District Code", ROUND(frpm."Free Meal Count (K-12)" / frpm."Enrollment (K-12)" * 100.0, 2) AS pct_eligible_free FROM frpm WHERE frpm."CDSCode" = '19648576108609'`

### card_games_340

- question: Which are the cards that have incredibly powerful foils.
- expected: `SELECT id FROM cards WHERE cardKingdomFoilId IS NOT NULL AND cardKingdomId IS NOT NULL`
- agent: `SELECT COUNT(DISTINCT name) AS distinct_cards FROM cards WHERE cardKingdomFoilId IS NOT NULL AND cardKingdomId IS NOT NULL;`

### card_games_346

- question: List all the card id and artist with unknown power which are legal for commander play format.
- expected: `SELECT T1.id, T1.artist FROM cards AS T1 INNER JOIN legalities AS T2 ON T1.uuid = T2.uuid WHERE T2.status = 'Legal' AND T2.format = 'commander' AND (T1.power IS NULL OR T1.power = '*')`
- agent: `SELECT CASE WHEN c.power = '*' THEN 'star' ELSE 'null' END AS power_kind, COUNT(DISTINCT c.id) AS cnt FROM cards c JOIN legalities l ON l.uuid = c.uuid WHERE l.format = 'commander' AND l.status = 'Legal' AND (c.power = '*' OR c.power IS NULL) GROUP BY power_kind;`

### card_games_358

- question: What is the border color of card "Ancestor's Chosen"?
- expected: `SELECT DISTINCT borderColor FROM cards WHERE name = 'Ancestor''s Chosen'`
- agent: `SELECT borderColor FROM cards WHERE name = 'Ancestor''s Chosen';`

### card_games_397

- question: What is the mana cost of cards with a normal layout, a 2003 frame version, with a black border color, and available in paper and mtgo?
- expected: `SELECT manaCost FROM cards WHERE availability = 'mtgo,paper' AND borderColor = 'black' AND frameVersion = 2003 AND layout = 'normal'`
- agent: `SELECT convertedManaCost AS cmc, COUNT(DISTINCT manaCost) AS distinct_mana_costs, COUNT(*) AS cards FROM cards WHERE layout = 'normal' AND frameVersion = '2003' AND borderColor = 'black' AND availability = 'mtgo,paper' AND manaCost IS NOT NULL GROUP BY convertedManaCost ORDER BY convertedManaCost;`

### card_games_407

- question: Lists all types of cards in German.
- expected: `SELECT T1.subtypes, T1.supertypes FROM cards AS T1 INNER JOIN foreign_data AS T2 ON T1.uuid = T2.uuid WHERE T2.language = 'German' AND T1.subtypes IS NOT NULL AND T1.supertypes IS NOT NULL`
- agent: `SELECT uuid, name, setCode, multiverseId, type, supertypes, subtypes FROM cards WHERE multiverseId IN (148411, 148412)`

### card_games_412

- question: What is the foreign name of the card in French of type Creature, normal layout and black border color, by artist Matthew D. Wilson?
- expected: `SELECT name FROM foreign_data WHERE uuid IN ( SELECT uuid FROM cards WHERE types = 'Creature' AND layout = 'normal' AND borderColor = 'black' AND artist = 'Matthew D. Wilson' ) AND language = 'French'`
- agent: `SELECT COUNT(*) FROM cards WHERE type = 'Creature';`

### card_games_422

- question: What is the language of the card with the multiverse number 149934?
- expected: `SELECT language FROM foreign_data WHERE multiverseid = 149934`
- agent: `SELECT language, name, multiverseid FROM foreign_data WHERE multiverseid = 149934;`

### card_games_459

- question: Which card costs more converted mana, "Serra Angel" or "Shrine Keeper"?
- expected: `SELECT name FROM cards WHERE name IN ('Serra Angel', 'Shrine Keeper') ORDER BY convertedManaCost DESC LIMIT 1`
- agent: `SELECT name, convertedManaCost FROM cards WHERE name IN ('Serra Angel', 'Shrine Keeper')`

### card_games_480

- question: What is the Italian flavor text of the card "Ancestor's Chosen"?
- expected: `SELECT T2.flavorText FROM cards AS T1 INNER JOIN foreign_data AS T2 ON T2.uuid = T1.uuid WHERE T1.name = 'Ancestor''s Chosen' AND T2.language = 'Italian'`
- agent: `SELECT f.uuid, f.language, f.name, f.flavorText, c.setCode FROM foreign_data f JOIN cards c ON c.uuid = f.uuid WHERE f.uuid IN ('5f8287b1-5bb6-5f4c-ad17-316a40d5bb0c','b7c19924-b4bf-56fc-aa73-f586e940bd42','7a7e2e9b-93ad-5616-8e3f-ed53a06acfd4','02f098cf-93bc-5a4e-8d29-724d3b273cda') AND f.language = 'Italian'`

### codebase_community_604

- question: What is the average of the up votes and the average user age for users creating more than 10 posts?
- expected: `SELECT AVG(T1.UpVotes), AVG(T1.Age) FROM users AS T1 INNER JOIN ( SELECT OwnerUserId, COUNT(*) AS post_count FROM posts GROUP BY OwnerUserId HAVING post_count > 10) AS T2 ON T1.Id = T2.OwnerUserId`
- agent: `WITH user_post_counts AS ( SELECT OwnerUserId AS UserId FROM posts WHERE OwnerUserId IS NOT NULL GROUP BY OwnerUserId HAVING COUNT(*) > 10 ) SELECT COUNT(*) AS Total, SUM(CASE WHEN u.UpVotes IS NULL THEN 1 ELSE 0 END) AS NullUpVotes, SUM(CASE WHEN u.Age IS NULL THEN 1 ELSE 0 END) AS NullAge FROM user_post_counts upc JOIN users u ON u.Id = upc.UserId;`

### codebase_community_633

- question: Which post by slashnick has the most answers count? State the post ID.
- expected: `SELECT T2.PostId FROM users AS T1 INNER JOIN postHistory AS T2 ON T1.Id = T2.UserId INNER JOIN posts AS T3 ON T2.PostId = T3.Id WHERE T1.DisplayName = 'slashnick' ORDER BY T3.AnswerCount DESC LIMIT 1`
- agent: `SELECT Id, PostTypeId, ParentId, OwnerUserId, OwnerDisplayName, AnswerCount FROM posts WHERE OwnerDisplayName LIKE '%slashnick%' OR OwnerUserId = 16 ORDER BY AnswerCount DESC`

### codebase_community_634

- question: Among posts by Harvey Motulsky and Noah Snyder, which one has higher popularity?
- expected: `SELECT T1.DisplayName FROM users AS T1 INNER JOIN postHistory AS T2 ON T1.Id = T2.UserId INNER JOIN posts AS T3 ON T2.PostId = T3.Id WHERE T1.DisplayName = 'Harvey Motulsky' OR T1.DisplayName = 'Noah Snyder' GROUP BY T1.DisplayName ORDER BY SUM(T3.ViewCount) DESC LIMIT 1`
- agent: `SELECT u.DisplayName, COUNT(p.Id) AS num_posts, COALESCE(SUM(p.ViewCount), 0) AS TotalViewCount FROM users u LEFT JOIN posts p ON p.OwnerUserId = u.Id WHERE u.DisplayName IN ('Harvey Motulsky', 'Noah Snyder') GROUP BY u.DisplayName ORDER BY TotalViewCount DESC;`

### codebase_community_640

- question: Calculate the difference in view count from post posted by Mornington and view count from posts posted by Amos.
- expected: `SELECT SUM(IIF(T1.DisplayName = 'Mornington', T3.ViewCount, 0)) - SUM(IIF(T1.DisplayName = 'Amos', T3.ViewCount, 0)) AS diff FROM users AS T1 INNER JOIN postHistory AS T2 ON T1.Id = T2.UserId INNER JOIN posts AS T3 ON T3.Id = T2.PostId`
- agent: `SELECT COALESCE(SUM(CASE WHEN LOWER(u.DisplayName) = 'mornington' THEN p.ViewCount END),0) - COALESCE(SUM(CASE WHEN LOWER(u.DisplayName) = 'amos' THEN p.ViewCount END),0) AS view_count_difference FROM users u LEFT JOIN posts p ON p.OwnerUserId = u.Id WHERE LOWER(u.DisplayName) IN ('mornington','amos');`

### codebase_community_678

- question: Which post by Harvey Motulsky has the most views? Please give the id and title of this post.
- expected: `SELECT T2.Id, T2.Title FROM users AS T1 INNER JOIN posts AS T2 ON T1.Id = T2.OwnerUserId WHERE T1.DisplayName = 'Harvey Motulsky' ORDER BY T2.ViewCount DESC LIMIT 1`
- agent: `SELECT Id, PostTypeId, Title, ViewCount, Score, ParentId FROM posts WHERE OwnerUserId = 25 OR OwnerDisplayName = 'Harvey Motulsky' ORDER BY ViewCount DESC LIMIT 5`

### codebase_community_685

- question: Identify the total views on the post 'Computer Game Datasets'. Name the user who posted it last time.
- expected: `SELECT T2.ViewCount, T3.DisplayName FROM postHistory AS T1 INNER JOIN posts AS T2 ON T1.PostId = T2.Id INNER JOIN users AS T3 ON T2.LastEditorUserId = T3.Id WHERE T1.Text = 'Computer Game Datasets'`
- agent: `SELECT p.ViewCount AS total_views, u.DisplayName AS user_who_posted FROM postHistory ph JOIN posts p ON p.Id = ph.PostId JOIN users u ON u.Id = ph.UserId WHERE ph.Text = 'Computer Game Datasets'`

### debit_card_specializing_1481

- question: What is the difference in the annual average consumption of the customers with the least amount of consumption paid in CZK for 2013 between SME and LAM, LAM and KAM, and KAM and SME?
- expected: `SELECT CAST(SUM(IIF(T1.Segment = 'SME', T2.Consumption, 0)) AS REAL) / COUNT(T1.CustomerID) - CAST(SUM(IIF(T1.Segment = 'LAM', T2.Consumption, 0)) AS REAL) / COUNT(T1.CustomerID) , CAST(SUM(IIF(T1.Segment = 'LAM', T2.Consumption, 0)) AS REAL) / COUNT(T1.CustomerID) - CAST(SUM(IIF(T1.Segment = 'KAM', T2.Consumption, 0)) AS REAL) / COUNT(T1.CustomerID) , CAST(SUM(IIF(T1.Segment = 'KAM', T2.Consumption, 0)) AS REAL) / COUNT(T1.CustomerID) - CAST(SUM(IIF(T1.Segment = 'SME', T2.Consumption, 0)) AS REAL) / COUNT(T1.CustomerID) FROM customers AS T1 INNER JOIN yearmonth AS T2 ON T1.CustomerID = T2.CustomerID WHERE T1.Currency = 'CZK' AND T2.Consumption = ( SELECT MIN(Consumption) FROM yearmonth ) AND T2.Date BETWEEN 201301 AND 201312`
- agent: `WITH cust_annual AS ( SELECT c.CustomerID, c.Segment, SUM(ym.Consumption) AS annual FROM customers c JOIN yearmonth ym ON ym.CustomerID = c.CustomerID WHERE c.Currency = 'CZK' AND ym.Date BETWEEN '201301' AND '201312' GROUP BY c.CustomerID, c.Segment ), ranked AS ( SELECT Segment, annual, RANK() OVER (PARTITION BY Segment ORDER BY annual) AS rk FROM cust_annual ) SELECT Segment, MIN(annual) AS min_annual, COUNT(*) AS n_customers FROM ranked WHERE rk = 1 GROUP BY Segment ORDER BY Segment`

### european_football_2_1030

- question: Give the name of the league had the most matches end as draw in the 2016 season?
- expected: `SELECT t2.name FROM Match AS t1 INNER JOIN League AS t2 ON t1.league_id = t2.id WHERE t1.season = '2015/2016' AND t1.home_team_goal = t1.away_team_goal GROUP BY t2.name ORDER BY COUNT(t1.id) DESC LIMIT 1`
- agent: `SELECT l.name AS league_name, COUNT(*) AS draw_count FROM Match m JOIN League l ON m.league_id = l.id WHERE m.season = '2015/2016' AND m.home_team_goal = m.away_team_goal GROUP BY m.league_id, l.name ORDER BY draw_count DESC LIMIT 1;`

### european_football_2_1079

- question: Which player is the tallest?
- expected: `SELECT player_name FROM Player ORDER BY height DESC LIMIT 1`
- agent: `SELECT player_name, height FROM Player WHERE height = (SELECT MAX(height) FROM Player);`

### european_football_2_1135

- question: Please provide top four football players' IDs who are among the lowest potential players and prefer to use the right foot when attacking.
- expected: `SELECT id FROM Player_Attributes WHERE preferred_foot = 'right' ORDER BY potential ASC LIMIT 4`
- agent: `SELECT p.id AS player_table_id, p.player_api_id, p.player_name, t.min_pot FROM ( SELECT player_api_id, MIN(potential) AS min_pot FROM Player_Attributes WHERE preferred_foot = 'right' AND potential IS NOT NULL GROUP BY player_api_id ORDER BY min_pot ASC, player_api_id ASC LIMIT 4 ) t JOIN Player p ON p.player_api_id = t.player_api_id ORDER BY t.min_pot ASC, t.player_api_id ASC;`

### financial_115

- question: For the branch which located in the south Bohemia with biggest number of inhabitants, what is the percentage of the male clients?
- expected: `SELECT CAST(SUM(T1.gender = 'M') AS REAL) * 100 / COUNT(T1.client_id) FROM client AS T1 INNER JOIN district AS T2 ON T1.district_id = T2.district_id WHERE T2.A3 = 'south Bohemia' GROUP BY T2.A4 ORDER BY T2.A4 DESC LIMIT 1`
- agent: `SELECT COUNT(*) AS total_clients_with_account, COUNT(DISTINCT c.client_id) AS distinct_clients FROM client c JOIN disp d ON d.client_id=c.client_id JOIN account a ON a.account_id=d.account_id;`

### financial_117

- question: What is the percentage of loan amount that has been fully paid with no issue.
- expected: `SELECT (CAST(SUM(CASE WHEN status = 'A' THEN amount ELSE 0 END) AS REAL) * 100) / SUM(amount) FROM loan`
- agent: `SELECT ROUND(100.0 * SUM(CASE WHEN status = 'A' THEN amount ELSE 0 END) / SUM(amount), 2) AS pct_fully_paid FROM loan;`

### financial_128

- question: List the top nine districts, by descending order, from the highest to the lowest, the number of female account holders.
- expected: `SELECT T2.A2, COUNT(T1.client_id) FROM client AS T1 INNER JOIN district AS T2 ON T1.district_id = T2.district_id WHERE T1.gender = 'F' GROUP BY T2.district_id, T2.A2 ORDER BY COUNT(T1.client_id) DESC LIMIT 9`
- agent: `SELECT d.A2 AS district, COUNT(DISTINCT c.client_id) AS female_account_holders FROM client c JOIN disp di ON c.client_id = di.client_id JOIN account a ON di.account_id = a.account_id JOIN district d ON a.district_id = d.district_id WHERE c.gender = 'F' GROUP BY d.A2 ORDER BY female_account_holders DESC, d.A2 LIMIT 9;`

### financial_159

- question: List all the withdrawals in cash transactions that the client with the id 3356 makes.
- expected: `SELECT T4.trans_id FROM client AS T1 INNER JOIN disp AS T2 ON T1.client_id = T2.client_id INNER JOIN account AS T3 ON T2.account_id = T3.account_id INNER JOIN trans AS T4 ON T3.account_id = T4.account_id WHERE T1.client_id = 3356 AND T4.operation = 'VYBER'`
- agent: `SELECT trans_id, date, amount, balance FROM trans WHERE account_id = 2779 AND operation = 'VYBER' ORDER BY date, trans_id LIMIT 70 OFFSET 70;`

### financial_168

- question: What percentage of clients who opened their accounts in the district with an average salary of over 10000 are women?
- expected: `SELECT CAST(SUM(T2.gender = 'F') AS REAL) * 100 / COUNT(T2.client_id) FROM district AS T1 INNER JOIN client AS T2 ON T1.district_id = T2.district_id WHERE T1.A11 > 10000`
- agent: `SELECT MIN(c) AS min_owners, MAX(c) AS max_owners FROM ( SELECT account_id, COUNT(*) AS c FROM disp WHERE type='OWNER' GROUP BY account_id )`

### financial_169

- question: What was the growth rate of the total amount of loans across all accounts for a male client between 1996 and 1997?
- expected: `SELECT CAST((SUM(CASE WHEN STRFTIME('%Y', T1.date) = '1997' THEN T1.amount ELSE 0 END) - SUM(CASE WHEN STRFTIME('%Y', T1.date) = '1996' THEN T1.amount ELSE 0 END)) AS REAL) * 100 / SUM(CASE WHEN STRFTIME('%Y', T1.date) = '1996' THEN T1.amount ELSE 0 END) FROM loan AS T1 INNER JOIN account AS T2 ON T1.account_id = T2.account_id INNER JOIN disp AS T3 ON T3.account_id = T2.account_id INNER JOIN client AS T4 ON T4.client_id = T3.client_id WHERE T4.gender = 'M' AND T3.type = 'OWNER'`
- agent: `WITH male_accounts AS ( SELECT DISTINCT d.account_id FROM disp d JOIN client c ON c.client_id = d.client_id WHERE c.gender = 'M' ), yr_sums AS ( SELECT substr(l.date,1,4) AS yr, SUM(l.amount) AS total FROM loan l JOIN male_accounts m ON m.account_id = l.account_id WHERE substr(l.date,1,4) IN ('1996','1997') GROUP BY yr ) SELECT SUM(CASE WHEN yr='1996' THEN total END) AS y1996, SUM(CASE WHEN yr='1997' THEN total END) AS y1997, ROUND((SUM(CASE WHEN yr='1997' THEN total END) - SUM(CASE WHEN yr='1996' THEN total END)) * 100.0 / SUM(CASE WHEN yr='1996' THEN total END), 2) AS growth_pct FROM yr_sums;`

### financial_189

- question: Name the account numbers of female clients who are oldest and have lowest average salary?
- expected: `SELECT T3.account_id FROM client AS T1 INNER JOIN district AS T2 ON T1.district_id = T2.district_id INNER JOIN account AS T3 ON T2.district_id = T3.district_id INNER JOIN disp AS T4 ON T1.client_id = T4.client_id AND T4.account_id = T3.account_id WHERE T1.gender = 'F' ORDER BY T1.birth_date ASC, T2.A11 ASC LIMIT 1`
- agent: `SELECT DISTINCT a.account_id FROM client c JOIN disp dp ON dp.client_id = c.client_id JOIN account a ON a.account_id = dp.account_id WHERE c.gender = 'F' AND c.district_id IN (SELECT district_id FROM district WHERE A11 = (SELECT MIN(A11) FROM district)) AND c.birth_date = (SELECT MIN(birth_date) FROM client WHERE gender = 'F' AND district_id IN (SELECT district_id FROM district WHERE A11 = (SELECT MIN(A11) FROM district))) ORDER BY a.account_id`

### financial_95

- question: List out the account numbers of clients who are youngest and have highest average salary?
- expected: `SELECT T1.account_id FROM account AS T1 INNER JOIN disp AS T2 ON T1.account_id = T2.account_id INNER JOIN client AS T3 ON T2.client_id = T3.client_id INNER JOIN district AS T4 on T4.district_id = T1.district_id WHERE T2.client_id = ( SELECT client_id FROM client ORDER BY birth_date DESC LIMIT 1) GROUP BY T4.A11, T1.account_id`
- agent: `SELECT c.client_id, c.birth_date, c.district_id, dp.account_id, dp.type FROM client c JOIN disp dp ON c.client_id = dp.client_id WHERE c.district_id = (SELECT district_id FROM district WHERE A11 = (SELECT MAX(A11) FROM district)) AND c.birth_date = (SELECT MAX(birth_date) FROM client WHERE district_id = (SELECT district_id FROM district WHERE A11 = (SELECT MAX(A11) FROM district)));`

### formula_1_866

- question: Who was the player that got the lap time of 0:01:27 in the race No. 161? Show his introduction website.
- expected: `SELECT DISTINCT T2.forename, T2.surname, T2.url FROM lapTimes AS T1 INNER JOIN drivers AS T2 ON T2.driverId = T1.driverId WHERE T1.raceId = 161 AND T1.time LIKE '1:27%'`
- agent: `SELECT COUNT(*) AS cnt FROM lapTimes WHERE time LIKE '0:%'`

### formula_1_869

- question: For the constructor which got the highest point in the race No. 9 , what is its introduction website?
- expected: `SELECT T2.url FROM constructorResults AS T1 INNER JOIN constructors AS T2 ON T2.constructorId = T1.constructorId WHERE T1.raceId = 9 ORDER BY T1.points DESC LIMIT 1`
- agent: `SELECT c.name, c.url, cr.points FROM constructorResults cr JOIN constructors c ON c.constructorId = cr.constructorId WHERE cr.raceId = 9 ORDER BY cr.points DESC;`

### formula_1_877

- question: For all the drivers who finished the game in race No. 872, who is the youngest?
- expected: `SELECT T1.forename, T1.surname FROM drivers AS T1 INNER JOIN results AS T2 ON T2.driverId = T1.driverId WHERE T2.raceId = 872 AND T2.time IS NOT NULL ORDER BY T1.dob DESC LIMIT 1`
- agent: `SELECT d.driverId, d.forename, d.surname, d.dob, r.position, r.positionOrder FROM results r JOIN drivers d ON d.driverId = r.driverId WHERE r.raceId = 872 AND r.time IS NOT NULL ORDER BY d.dob DESC`

### formula_1_897

- question: Name the driver with the most winning. Mention his nationality and what is his maximum point scores.
- expected: `SELECT T1.forename, T1.surname, T1.nationality, MAX(T2.points) FROM drivers AS T1 INNER JOIN driverStandings AS T2 ON T2.driverId = T1.driverId WHERE T2.wins >= 1 GROUP BY T1.forename, T1.surname, T1.nationality ORDER BY COUNT(T2.wins) DESC LIMIT 1`
- agent: `WITH wins AS ( SELECT r.driverId, COUNT(*) AS total_wins FROM results r WHERE r.positionOrder = 1 GROUP BY r.driverId ) SELECT d.forename, d.surname, d.nationality, w.total_wins, (SELECT MAX(points) FROM driverStandings ds WHERE ds.driverId = w.driverId) AS max_points FROM wins w JOIN drivers d ON d.driverId = w.driverId ORDER BY w.total_wins DESC LIMIT 1;`

### formula_1_906

- question: Which was Lewis Hamilton first race? What was his points recorded for his first race event?
- expected: `SELECT T1.name, T2.points FROM races AS T1 INNER JOIN driverStandings AS T2 ON T2.raceId = T1.raceId INNER JOIN drivers AS T3 ON T3.driverId = T2.driverId WHERE T3.forename = 'Lewis' AND T3.surname = 'Hamilton' ORDER BY T1.year ASC LIMIT 1`
- agent: `SELECT r.raceId, r.year, r.round, r.name FROM races r WHERE r.year=2007 ORDER BY r.round;`

### formula_1_955

- question: What is the average time in seconds of champion for each year, before year 1975?
- expected: `WITH time_in_seconds AS ( SELECT T2.year, T2.raceId, T1.positionOrder, CASE WHEN T1.positionOrder = 1 THEN (CAST(SUBSTR(T1.time, 1, 1) AS REAL) * 3600) + (CAST(SUBSTR(T1.time, 3, 2) AS REAL) * 60) + CAST(SUBSTR(T1.time, 6,2) AS REAL ) + CAST(SUBSTR(T1.time, 9) AS REAL)/1000 ELSE 0 END AS time_seconds FROM results AS T1 INNER JOIN races AS T2 ON T1.raceId = T2.raceId WHERE T1.time IS NOT NULL ), champion_time AS ( SELECT year, raceId, time_seconds FROM time_in_seconds WHERE positionOrder = 1 ) SELECT year, AVG(time_seconds) FROM champion_time WHERE year < 1975 GROUP BY year HAVING AVG(time_seconds) IS NOT NULL`
- agent: `SELECT ra.year, ra.name, res.positionOrder, res.positionText, res.driverId, res.time, res.laps, st.status FROM results res JOIN races ra ON res.raceId = ra.raceId JOIN status st ON res.statusId = st.statusId WHERE ra.year = 1950 AND ra.name = 'British Grand Prix' ORDER BY res.positionOrder`

### formula_1_972

- question: Which drivers who were born in 1971 and has the fastest lap time on the race? Give id and code of these drivers.
- expected: `SELECT T2.driverId, T2.code FROM results AS T1 INNER JOIN drivers AS T2 on T1.driverId = T2.driverId WHERE STRFTIME('%Y', T2.dob) = '1971' AND T1.fastestLapTime IS NOT NULL`
- agent: `SELECT DISTINCT d.driverId, d.code FROM drivers d JOIN results r ON r.driverId = d.driverId WHERE strftime('%Y', d.dob) = '1971' AND r.fastestLapTime IS NOT NULL ORDER BY d.driverId;`

### formula_1_990

- question: What is the constructor reference name of the champion in the 2009 Singapore Grand Prix? Please give its website.
- expected: `SELECT T3.constructorRef, T3.url FROM results AS T1 INNER JOIN races AS T2 on T1.raceId = T2.raceId INNER JOIN constructors AS T3 on T1.constructorId = T3.constructorId WHERE T2.name = 'Singapore Grand Prix' AND T2.year = 2009 AND T1.time LIKE '_:%:__.___'`
- agent: `SELECT res.driverId, d.forename, d.surname, res.positionOrder, res.time, res.milliseconds, ct.constructorId, ct.constructorRef, ct.name AS constructor_name, ct.url FROM results res JOIN drivers d ON res.driverId = d.driverId JOIN constructors ct ON res.constructorId = ct.constructorId WHERE res.raceId = 14 AND res.positionOrder = 1`

### student_club_1317

- question: Among the students from the Student_Club who attended the event "Women's Soccer", how many of them want a T-shirt that's in medium size?
- expected: `SELECT COUNT(T1.event_id) FROM event AS T1 INNER JOIN attendance AS T2 ON T1.event_id = T2.link_to_event INNER JOIN member AS T3 ON T2.link_to_member = T3.member_id WHERE T1.event_name = 'Women''s Soccer' AND T3.t_shirt_size = 'Medium'`
- agent: `SELECT 'member' AS tbl, member_id AS id, first_name AS val FROM member WHERE first_name LIKE '%Student_Club%' OR last_name LIKE '%Student_Club%' OR email LIKE '%Student_Club%' OR position LIKE '%Student_Club%' UNION ALL SELECT 'event', event_id, event_name FROM event WHERE event_name LIKE '%Student_Club%' OR notes LIKE '%Student_Club%' OR location LIKE '%Student_Club%' UNION ALL SELECT 'income', income_id, source FROM income WHERE source LIKE '%Student_Club%' OR notes LIKE '%Student_Club%' UNION ALL SELECT 'expense', expense_id, expense_description FROM expense WHERE expense_description LIKE '%Student_Club%' UNION ALL SELECT 'budget', budget_id, category FROM budget WHERE category LIKE '%Student_Club%'`

### student_club_1376

- question: Among all the closed events, which event has the highest spend-to-budget ratio?
- expected: `SELECT T2.event_name FROM budget AS T1 INNER JOIN event AS T2 ON T1.link_to_event = T2.event_id WHERE T2.status = 'Closed' ORDER BY T1.spent / T1.amount DESC LIMIT 1`
- agent: `SELECT e.event_name, b.spent, b.amount, b.spent * 1.0 / b.amount AS spend_to_budget_ratio FROM budget b JOIN event e ON b.link_to_event = e.event_id WHERE e.status = 'Closed' ORDER BY spend_to_budget_ratio DESC LIMIT 1`

### student_club_1399

- question: Did Maya Mclean attend the 'Women's Soccer' event?
- expected: `SELECT CASE WHEN T3.event_name = 'Women''s Soccer' THEN 'YES' END AS result FROM member AS T1 INNER JOIN attendance AS T2 ON T1.member_id = T2.link_to_member INNER JOIN event AS T3 ON T2.link_to_event = T3.event_id WHERE T1.first_name = 'Maya' AND T1.last_name = 'Mclean'`
- agent: `SELECT link_to_member, link_to_event FROM attendance WHERE link_to_member = 'recZ4PkGERzl9ziHO' AND link_to_event = 'rec2N69DMcrqN9PJC';`

### student_club_1422

- question: State the category of events were held at MU 215.
- expected: `SELECT DISTINCT T2.category FROM event AS T1 INNER JOIN budget AS T2 ON T1.event_id = T2.link_to_event WHERE T1.location = 'MU 215'`
- agent: `SELECT type FROM event WHERE location = 'MU 215';`

### superhero_728

- question: Rank superheroes from Marvel Comics by their eye color popularity, starting with the most common color.
- expected: `SELECT colour.colour AS EyeColor, COUNT(superhero.id) AS Count, RANK() OVER (ORDER BY COUNT(superhero.id) DESC) AS PopularityRank FROM superhero INNER JOIN colour ON superhero.eye_colour_id = colour.id INNER JOIN publisher ON superhero.publisher_id = publisher.id WHERE publisher.publisher_name = 'Marvel Comics' GROUP BY colour.colour`
- agent: `SELECT c.colour, COUNT(s.id) AS hero_count FROM superhero s JOIN publisher p ON s.publisher_id = p.id JOIN colour c ON s.eye_colour_id = c.id WHERE p.publisher_name = 'Marvel Comics' GROUP BY c.colour ORDER BY hero_count DESC, c.colour;`

### superhero_730

- question: List the superheroes from Marvel Comics who have the super power of 'Super Strength'.
- expected: `SELECT superhero_name FROM superhero AS T1 WHERE EXISTS (SELECT 1 FROM hero_power AS T2 INNER JOIN superpower AS T3 ON T2.power_id = T3.id WHERE T3.power_name = 'Super Strength' AND T1.id = T2.hero_id)AND EXISTS (SELECT 1 FROM publisher AS T4 WHERE T4.publisher_name = 'Marvel Comics' AND T1.publisher_id = T4.id)`
- agent: `SELECT s.superhero_name, COUNT(*) AS cnt FROM superhero s JOIN publisher p ON s.publisher_id = p.id JOIN hero_power hp ON s.id = hp.hero_id JOIN superpower sp ON hp.power_id = sp.id WHERE p.publisher_name = 'Marvel Comics' AND sp.power_name = 'Super Strength' GROUP BY s.superhero_name HAVING COUNT(*) > 1;`

### superhero_751

- question: List down at least five superpowers of male superheroes.
- expected: `SELECT T3.power_name FROM superhero AS T1 INNER JOIN hero_power AS T2 ON T1.id = T2.hero_id INNER JOIN superpower AS T3 ON T3.id = T2.power_id INNER JOIN gender AS T4 ON T4.id = T1.gender_id WHERE T4.gender = 'Male' LIMIT 5`
- agent: `SELECT DISTINCT sp.power_name FROM superhero s JOIN gender g ON s.gender_id = g.id JOIN hero_power hp ON hp.hero_id = s.id JOIN superpower sp ON sp.id = hp.power_id WHERE g.gender = 'Male' ORDER BY sp.power_name LIMIT 10`

### superhero_758

- question: Provide the hair colour of the human superhero who is 185 cm tall.
- expected: `SELECT DISTINCT T3.colour FROM superhero AS T1 INNER JOIN race AS T2 ON T1.race_id = T2.id INNER JOIN colour AS T3 ON T1.hair_colour_id = T3.id WHERE T1.height_cm = 185 AND T2.race = 'Human'`
- agent: `SELECT s.superhero_name, r.race, c.colour AS hair_colour, a.alignment, p.publisher_name FROM superhero s JOIN race r ON s.race_id = r.id LEFT JOIN colour c ON s.hair_colour_id = c.id LEFT JOIN alignment a ON s.alignment_id = a.id LEFT JOIN publisher p ON s.publisher_id = p.id WHERE s.height_cm = 185 AND r.race = 'Human' ORDER BY s.superhero_name`

### thrombosis_prediction_1168

- question: The oldest SJS patient's medical laboratory work was completed on what date, and what age was the patient when they initially arrived at the hospital?
- expected: `SELECT T1.Date, STRFTIME('%Y', T2.`First Date`) - STRFTIME('%Y', T2.Birthday),T2.Birthday FROM Laboratory AS T1 INNER JOIN Patient AS T2 ON T1.ID = T2.ID WHERE T2.Diagnosis = 'SJS' AND T2.Birthday IS NOT NULL ORDER BY T2.Birthday ASC LIMIT 1`
- agent: `SELECT COUNT(*) AS n_exam FROM Examination`

### thrombosis_prediction_1209

- question: Please provide the diagnosis of patients with ALT glutamic pylvic transaminase beyond the normal range by ascending order of their date of birth.
- expected: `SELECT DISTINCT T1.Diagnosis FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.GPT > 60 ORDER BY T1.Birthday ASC`
- agent: `SELECT COUNT(*) FROM Patient`

### thrombosis_prediction_1252

- question: Among the patients with a normal Ig G level, how many of them have symptoms?
- expected: `SELECT COUNT(T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID INNER JOIN Examination AS T3 ON T3.ID = T2.ID WHERE T2.IGG BETWEEN 900 AND 2000 AND T3.Symptoms IS NOT NULL`
- agent: `SELECT COUNT(DISTINCT e.ID) AS patient_count FROM Examination e JOIN Laboratory l ON l.ID = e.ID WHERE l.IGG > 900 AND l.IGG < 2000 AND e.Symptoms IS NOT NULL;`

### thrombosis_prediction_1256

- question: How many patients with a abnormal C-reactive protein don't have their data recorded?
- expected: `SELECT COUNT(T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE (T2.CRP = '+' ) AND T1.Description IS NULL`
- agent: `SELECT COUNT(DISTINCT p.ID) AS cnt FROM Patient p JOIN Laboratory l ON l.ID = p.ID WHERE l.CRP = '+' AND p.Description IS NULL`

### toxicology_212

- question: Which element is the least numerous in non-carcinogenic molecules?
- expected: `SELECT T.element FROM (SELECT T1.element, COUNT(DISTINCT T1.molecule_id) FROM atom AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T2.label = '-' GROUP BY T1.element ORDER BY COUNT(DISTINCT T1.molecule_id) ASC LIMIT 1) t`
- agent: `WITH element_counts AS ( SELECT a.element, COUNT(*) AS cnt FROM atom a JOIN molecule m ON a.molecule_id = m.molecule_id WHERE m.label = '-' AND a.element IS NOT NULL GROUP BY a.element ) SELECT element FROM element_counts WHERE cnt = (SELECT MIN(cnt) FROM element_counts);`

### toxicology_268

- question: What are the elements for bond id TR001_10_11?
- expected: `SELECT T2.element FROM connected AS T1 INNER JOIN atom AS T2 ON T1.atom_id = T2.atom_id WHERE T1.bond_id = 'TR001_10_11'`
- agent: `SELECT a1.element AS element1, a2.element AS element2 FROM connected c JOIN atom a1 ON c.atom_id = a1.atom_id JOIN atom a2 ON c.atom_id2 = a2.atom_id WHERE c.bond_id = 'TR001_10_11';`

### toxicology_282

- question: What is the ratio of Hydrogen elements in molecule ID TR006? List the ratio with its label.
- expected: `WITH SubQuery AS (SELECT DISTINCT T1.atom_id, T1.element, T1.molecule_id, T2.label FROM atom AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T2.molecule_id = 'TR006') SELECT CAST(COUNT(CASE WHEN element = 'h' THEN atom_id ELSE NULL END) AS REAL) / (CASE WHEN COUNT(atom_id) = 0 THEN NULL ELSE COUNT(atom_id) END) AS ratio, label FROM SubQuery GROUP BY label`
- agent: `SELECT m.label, SUM(CASE WHEN a.element = 'h' THEN 1 ELSE 0 END) * 1.0 / COUNT(a.element) AS ratio FROM atom a JOIN molecule m ON m.molecule_id = a.molecule_id WHERE a.molecule_id = 'TR006' GROUP BY m.molecule_id, m.label`

