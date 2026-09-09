# QueryAgent Eval Report — public subset

- model: `deepseek-v4-flash`
- cases: 100
- scoring: v2 (query trajectory and completion reported separately)
- Natural-language answer correctness is not measured.

## Summary

| metric | value |
|---|---|
| first-execution pass rate | 28/100 (28%) |
| query-trajectory hit rate | 44/100 (44%) |
| completed with SQL hit | 42/100 (42%) |
| metric hit rate | n/a |
| clarify-behaviour accuracy | n/a |
| average tool calls | 3.10 |
| tokens per case (in+out) | 11,623 |
| prompt cache hit rate | 87% |
| latency per case | 13.9s |
| cost per case (upper bound) | $0.0028 |
| unmeasured (upstream unreachable) | 0 |

## Cases

| id | kind | SQL hit | completed | first try | retries | tool calls | note |
|---|---|---|---|---|---|---|---|
| california_schools_36 | public | ❌ | ✅ | ❌ | 0 | 3 | result sets differ |
| california_schools_37 | public | ❌ | ❌ | ❌ | 0 | 8 | no final answer after 8 turns |
| california_schools_39 | public | ❌ | ❌ | ❌ | 0 | 8 | no final answer after 8 turns |
| california_schools_41 | public | ❌ | ❌ | ❌ | 0 | 8 | no final answer after 8 turns |
| california_schools_45 | public | ✅ | ✅ | ❌ | 0 | 2 |  |
| california_schools_72 | public | ❌ | ✅ | ❌ | 0 | 5 | result sets differ |
| california_schools_85 | public | ❌ | ✅ | ❌ | 0 | 3 | result sets differ |
| card_games_340 | public | ❌ | ✅ | ❌ | 0 | 2 | result sets differ |
| card_games_345 | public | ✅ | ✅ | ✅ | 0 | 2 |  |
| card_games_346 | public | ❌ | ✅ | ❌ | 0 | 3 | result sets differ |
| card_games_358 | public | ❌ | ✅ | ❌ | 0 | 1 | result sets differ |
| card_games_368 | public | ✅ | ✅ | ✅ | 0 | 1 |  |
| card_games_379 | public | ✅ | ❌ | ✅ | 0 | 8 | no final answer after 8 turns |
| card_games_397 | public | ❌ | ✅ | ❌ | 0 | 3 | result sets differ |
| card_games_407 | public | ❌ | ✅ | ❌ | 0 | 4 | result sets differ |
| card_games_409 | public | ✅ | ✅ | ✅ | 0 | 1 |  |
| card_games_412 | public | ❌ | ✅ | ❌ | 0 | 4 | result sets differ |
| card_games_415 | public | ✅ | ✅ | ❌ | 0 | 3 |  |
| card_games_422 | public | ❌ | ✅ | ❌ | 0 | 1 | result sets differ |
| card_games_459 | public | ❌ | ✅ | ❌ | 0 | 2 | result sets differ |
| card_games_468 | public | ✅ | ✅ | ✅ | 0 | 1 |  |
| card_games_479 | public | ✅ | ✅ | ✅ | 0 | 1 |  |
| card_games_480 | public | ❌ | ✅ | ❌ | 0 | 7 | result sets differ |
| codebase_community_539 | public | ✅ | ✅ | ✅ | 0 | 1 |  |
| codebase_community_557 | public | ❌ | ✅ | ❌ | 0 | 1 | result sets differ |
| codebase_community_573 | public | ✅ | ✅ | ✅ | 0 | 4 |  |
| codebase_community_581 | public | ✅ | ✅ | ✅ | 0 | 1 |  |
| codebase_community_604 | public | ❌ | ✅ | ❌ | 0 | 2 | result sets differ |
| codebase_community_633 | public | ❌ | ❌ | ❌ | 0 | 8 | no final answer after 8 turns |
| codebase_community_634 | public | ❌ | ❌ | ❌ | 0 | 8 | no final answer after 8 turns |
| codebase_community_640 | public | ❌ | ✅ | ❌ | 0 | 7 | result sets differ |
| codebase_community_678 | public | ❌ | ✅ | ❌ | 0 | 1 | result sets differ |
| codebase_community_685 | public | ❌ | ✅ | ❌ | 0 | 5 | result sets differ |
| codebase_community_701 | public | ❌ | ❌ | ❌ | 1 | 8 | reference expected_sql failed (case bug?): interrupted |
| codebase_community_707 | public | ❌ | ✅ | ❌ | 0 | 2 | result sets differ |
| debit_card_specializing_1481 | public | ❌ | ❌ | ❌ | 0 | 8 | no final answer after 8 turns |
| debit_card_specializing_1484 | public | ❌ | ✅ | ❌ | 0 | 1 | result sets differ |
| european_football_2_1030 | public | ❌ | ✅ | ❌ | 0 | 1 | result sets differ |
| european_football_2_1079 | public | ❌ | ✅ | ❌ | 0 | 1 | result sets differ |
| european_football_2_1134 | public | ❌ | ✅ | ❌ | 0 | 1 | result sets differ |
| european_football_2_1135 | public | ❌ | ✅ | ❌ | 0 | 3 | result sets differ |
| financial_115 | public | ❌ | ✅ | ❌ | 0 | 4 | result sets differ |
| financial_117 | public | ✅ | ✅ | ✅ | 0 | 1 |  |
| financial_128 | public | ✅ | ❌ | ❌ | 0 | 8 | no final answer after 8 turns |
| financial_159 | public | ❌ | ✅ | ❌ | 0 | 2 | result sets differ |
| financial_168 | public | ❌ | ❌ | ❌ | 0 | 5 | multiple SQL statements are not allowed (2 found); send exactly one SELECT |
| financial_169 | public | ✅ | ✅ | ❌ | 0 | 7 |  |
| financial_189 | public | ❌ | ❌ | ❌ | 0 | 4 | multiple SQL statements are not allowed (2 found); send exactly one SELECT |
| financial_92 | public | ✅ | ✅ | ❌ | 0 | 5 |  |
| financial_93 | public | ✅ | ✅ | ❌ | 0 | 2 |  |
| financial_95 | public | ❌ | ❌ | ❌ | 0 | 8 | no final answer after 8 turns |
| formula_1_866 | public | ❌ | ✅ | ❌ | 0 | 5 | result sets differ |
| formula_1_869 | public | ✅ | ✅ | ✅ | 0 | 1 |  |
| formula_1_877 | public | ❌ | ✅ | ❌ | 0 | 2 | result sets differ |
| formula_1_897 | public | ❌ | ❌ | ❌ | 0 | 4 | multiple SQL statements are not allowed (2 found); send exactly one SELECT |
| formula_1_906 | public | ❌ | ✅ | ❌ | 0 | 5 | result sets differ |
| formula_1_909 | public | ❌ | ✅ | ❌ | 0 | 2 | result sets differ |
| formula_1_910 | public | ✅ | ✅ | ✅ | 0 | 1 |  |
| formula_1_940 | public | ✅ | ✅ | ❌ | 0 | 2 |  |
| formula_1_955 | public | ❌ | ✅ | ❌ | 0 | 2 | result sets differ |
| formula_1_960 | public | ✅ | ✅ | ✅ | 0 | 1 |  |
| formula_1_972 | public | ❌ | ✅ | ❌ | 0 | 2 | result sets differ |
| formula_1_977 | public | ✅ | ✅ | ✅ | 0 | 1 |  |
| formula_1_990 | public | ✅ | ✅ | ❌ | 0 | 4 |  |
| student_club_1317 | public | ❌ | ❌ | ❌ | 0 | 8 | no final answer after 8 turns |
| student_club_1346 | public | ✅ | ✅ | ✅ | 0 | 1 |  |
| student_club_1350 | public | ✅ | ✅ | ❌ | 0 | 3 |  |
| student_club_1352 | public | ✅ | ✅ | ✅ | 0 | 1 |  |
| student_club_1361 | public | ✅ | ✅ | ✅ | 0 | 2 |  |
| student_club_1376 | public | ✅ | ✅ | ❌ | 0 | 5 |  |
| student_club_1378 | public | ✅ | ✅ | ✅ | 0 | 1 |  |
| student_club_1399 | public | ❌ | ✅ | ❌ | 0 | 1 | result sets differ |
| student_club_1405 | public | ✅ | ✅ | ❌ | 0 | 3 |  |
| student_club_1409 | public | ✅ | ✅ | ✅ | 0 | 1 |  |
| student_club_1422 | public | ❌ | ✅ | ❌ | 0 | 3 | result sets differ |
| student_club_1426 | public | ✅ | ✅ | ✅ | 0 | 1 |  |
| superhero_717 | public | ✅ | ✅ | ✅ | 0 | 1 |  |
| superhero_719 | public | ✅ | ✅ | ✅ | 0 | 1 |  |
| superhero_728 | public | ❌ | ✅ | ❌ | 0 | 2 | result sets differ |
| superhero_730 | public | ✅ | ✅ | ✅ | 0 | 3 |  |
| superhero_733 | public | ✅ | ✅ | ✅ | 0 | 1 |  |
| superhero_751 | public | ❌ | ✅ | ❌ | 0 | 1 | result sets differ |
| superhero_758 | public | ❌ | ✅ | ❌ | 0 | 4 | result sets differ |
| superhero_765 | public | ✅ | ✅ | ✅ | 0 | 1 |  |
| superhero_806 | public | ✅ | ✅ | ✅ | 0 | 1 |  |
| thrombosis_prediction_1168 | public | ❌ | ❌ | ❌ | 0 | 8 | no final answer after 8 turns |
| thrombosis_prediction_1195 | public | ✅ | ✅ | ❌ | 0 | 5 |  |
| thrombosis_prediction_1201 | public | ❌ | ✅ | ❌ | 0 | 1 | result sets differ |
| thrombosis_prediction_1209 | public | ❌ | ✅ | ❌ | 0 | 4 | result sets differ |
| thrombosis_prediction_1252 | public | ❌ | ✅ | ❌ | 0 | 1 | result sets differ |
| thrombosis_prediction_1256 | public | ❌ | ✅ | ❌ | 0 | 1 | result sets differ |
| thrombosis_prediction_1270 | public | ✅ | ✅ | ❌ | 0 | 3 |  |
| toxicology_200 | public | ✅ | ✅ | ✅ | 0 | 1 |  |
| toxicology_206 | public | ✅ | ✅ | ✅ | 0 | 2 |  |
| toxicology_212 | public | ❌ | ✅ | ❌ | 0 | 2 | result sets differ |
| toxicology_228 | public | ✅ | ✅ | ❌ | 0 | 2 |  |
| toxicology_242 | public | ✅ | ✅ | ❌ | 0 | 6 |  |
| toxicology_268 | public | ❌ | ✅ | ❌ | 0 | 1 | result sets differ |
| toxicology_282 | public | ❌ | ✅ | ❌ | 0 | 3 | result sets differ |
| toxicology_327 | public | ✅ | ✅ | ❌ | 0 | 3 |  |

## Failing cases — SQL comparison

### california_schools_36

- question: Under whose administration is the school with the highest number of students scoring 1500 or more on the SAT? Indicate their full names.
- expected: `SELECT T2.AdmFName1, T2.AdmLName1, T2.AdmFName2, T2.AdmLName2, T2.AdmFName3, T2.AdmLName3 FROM satscores AS T1 INNER JOIN schools AS T2 ON T1.cds = T2.CDSCode ORDER BY T1.NumGE1500 DESC LIMIT 1`
- agent: `SELECT School, AdmFName1, AdmLName1, AdmFName2, AdmLName2, AdmFName3, AdmLName3 FROM schools WHERE CDSCode = '38684783833407'`

### california_schools_37

- question: What is the complete address of the school with the lowest excellence rate? Indicate the Street, City, Zip and State.
- expected: `SELECT T2.Street, T2.City, T2.State, T2.Zip FROM satscores AS T1 INNER JOIN schools AS T2 ON T1.cds = T2.CDSCode ORDER BY CAST(T1.NumGE1500 AS REAL) / T1.NumTstTakr ASC LIMIT 1`
- agent: `SELECT cds, COUNT(*) c FROM satscores WHERE rtype='S' GROUP BY cds HAVING COUNT(*) > 1 LIMIT 10`

### california_schools_39

- question: What is the average number of test takers from Fresno schools that opened between 1/1/1980 and 12/31/1980?
- expected: `SELECT AVG(T1.NumTstTakr) FROM satscores AS T1 INNER JOIN schools AS T2 ON T1.cds = T2.CDSCode WHERE strftime('%Y', T2.OpenDate) = '1980' AND T2.County = 'Fresno'`
- agent: `SELECT sc.City, COUNT(*) AS n, ROUND(AVG(s.NumTstTakr),1) AS avg_takers FROM schools sc JOIN satscores s ON sc.CDSCode = s.cds AND s.rtype = 'S' WHERE sc.County = 'Fresno' AND substr(sc.OpenDate,1,4) = '1980' GROUP BY sc.City ORDER BY n DESC`

### california_schools_41

- question: List the names of virtual schools that are among the top 5 in their respective counties based on average reading scores.
- expected: `SELECT School FROM (SELECT T2.School,T1.AvgScrRead, RANK() OVER (PARTITION BY T2.County ORDER BY T1.AvgScrRead DESC) AS rnk FROM satscores AS T1 INNER JOIN schools AS T2 ON T1.cds = T2.CDSCode WHERE T2.Virtual = 'F' ) ranked_schools WHERE rnk <= 5`
- agent: `SELECT sch.CDSCode, sch.County, sch.School, s.AvgScrRead FROM schools sch JOIN satscores s ON sch.CDSCode = s.cds AND s.rtype='S' WHERE sch.Virtual='F' AND s.AvgScrRead IS NOT NULL ORDER BY sch.County, s.AvgScrRead DESC;`

### california_schools_72

- question: How many students from the ages of 5 to 17 are enrolled at the State Special School school in Fremont for the 2014-2015 academic year?
- expected: `SELECT T1.`Enrollment (Ages 5-17)` FROM frpm AS T1 INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode WHERE T2.EdOpsCode = 'SSS' AND T2.City = 'Fremont' AND T1.`Academic Year` BETWEEN 2014 AND 2015`
- agent: `SELECT s.CDSCode, s.School, f."Academic Year", f."Enrollment (Ages 5-17)" FROM frpm f JOIN schools s ON s.CDSCode = f.CDSCode WHERE s.EdOpsCode = 'SSS' AND s.City = 'Fremont' AND f."Academic Year" = '2014-2015'`

### california_schools_85

- question: What is the Percent (%) Eligible Free (K-12) in the school administered by an administrator whose first name is Alusine. List the district code of the school.
- expected: `SELECT T1.`Free Meal Count (K-12)` * 100 / T1.`Enrollment (K-12)`, T1.`District Code` FROM frpm AS T1 INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode WHERE T2.AdmFName1 = 'Alusine'`
- agent: `SELECT s.CDSCode, s.School, f."District Code", f."Enrollment (K-12)", f."Free Meal Count (K-12)", ROUND(f."Free Meal Count (K-12)" / f."Enrollment (K-12)" * 100.0, 2) AS PctEligibleFree FROM schools s JOIN frpm f ON f.CDSCode = s.CDSCode WHERE s.AdmFName1 = 'Alusine' OR s.AdmFName2 = 'Alusine' OR s.AdmFName3 = 'Alusine'`

### card_games_340

- question: Which are the cards that have incredibly powerful foils.
- expected: `SELECT id FROM cards WHERE cardKingdomFoilId IS NOT NULL AND cardKingdomId IS NOT NULL`
- agent: `SELECT COUNT(DISTINCT name) AS matching_cards FROM cards WHERE cardKingdomFoilId IS NOT NULL AND cardKingdomId IS NOT NULL;`

### card_games_346

- question: List all the card id and artist with unknown power which are legal for commander play format.
- expected: `SELECT T1.id, T1.artist FROM cards AS T1 INNER JOIN legalities AS T2 ON T1.uuid = T2.uuid WHERE T2.status = 'Legal' AND T2.format = 'commander' AND (T1.power IS NULL OR T1.power = '*')`
- agent: `SELECT COUNT(DISTINCT c.id) AS distinct_ids, COUNT(DISTINCT c.artist) AS distinct_artists FROM cards c JOIN legalities l ON l.uuid = c.uuid WHERE l.format = 'commander' AND l.status = 'Legal' AND (c.power = '*' OR c.power IS NULL);`

### card_games_358

- question: What is the border color of card "Ancestor's Chosen"?
- expected: `SELECT DISTINCT borderColor FROM cards WHERE name = 'Ancestor''s Chosen'`
- agent: `SELECT borderColor FROM cards WHERE name = 'Ancestor''s Chosen';`

### card_games_397

- question: What is the mana cost of cards with a normal layout, a 2003 frame version, with a black border color, and available in paper and mtgo?
- expected: `SELECT manaCost FROM cards WHERE availability = 'mtgo,paper' AND borderColor = 'black' AND frameVersion = 2003 AND layout = 'normal'`
- agent: `SELECT 'availability' AS attr, availability AS val, COUNT(*) AS cnt FROM cards WHERE layout='normal' AND frameVersion='2003' AND borderColor='black' GROUP BY availability ORDER BY cnt DESC;`

### card_games_407

- question: Lists all types of cards in German.
- expected: `SELECT T1.subtypes, T1.supertypes FROM cards AS T1 INNER JOIN foreign_data AS T2 ON T1.uuid = T2.uuid WHERE T2.language = 'German' AND T1.subtypes IS NOT NULL AND T1.supertypes IS NOT NULL`
- agent: `SELECT COUNT(DISTINCT f.type) AS distinct_de_types, COUNT(*) AS rows FROM foreign_data f JOIN cards c ON c.uuid = f.uuid WHERE f.language = 'German' AND c.subtypes IS NOT NULL AND c.supertypes IS NOT NULL;`

### card_games_412

- question: What is the foreign name of the card in French of type Creature, normal layout and black border color, by artist Matthew D. Wilson?
- expected: `SELECT name FROM foreign_data WHERE uuid IN ( SELECT uuid FROM cards WHERE types = 'Creature' AND layout = 'normal' AND borderColor = 'black' AND artist = 'Matthew D. Wilson' ) AND language = 'French'`
- agent: `SELECT c.name AS englishName, c.type, fd.type AS frenchType, fd.name AS frenchName, c.setCode FROM foreign_data fd JOIN cards c ON c.uuid = fd.uuid WHERE fd.language = 'French' AND c.type LIKE 'Creature%' AND c.layout = 'normal' AND c.borderColor = 'black' AND c.artist = 'Matthew D. Wilson' ORDER BY fd.type, c.name`

### card_games_422

- question: What is the language of the card with the multiverse number 149934?
- expected: `SELECT language FROM foreign_data WHERE multiverseid = 149934`
- agent: `SELECT language, name, multiverseid FROM foreign_data WHERE multiverseid = 149934;`

### card_games_459

- question: Which card costs more converted mana, "Serra Angel" or "Shrine Keeper"?
- expected: `SELECT name FROM cards WHERE name IN ('Serra Angel', 'Shrine Keeper') ORDER BY convertedManaCost DESC LIMIT 1`
- agent: `SELECT name, MAX(convertedManaCost) AS convertedManaCost FROM cards WHERE name IN ('Serra Angel', 'Shrine Keeper') GROUP BY name`

### card_games_480

- question: What is the Italian flavor text of the card "Ancestor's Chosen"?
- expected: `SELECT T2.flavorText FROM cards AS T1 INNER JOIN foreign_data AS T2 ON T2.uuid = T1.uuid WHERE T1.name = 'Ancestor''s Chosen' AND T2.language = 'Italian'`
- agent: `SELECT c.setCode, c.multiverseId, fd.multiverseid, fd.language, fd.flavorText, fd.name AS localizedName FROM cards c JOIN foreign_data fd ON c.uuid = fd.uuid WHERE c.name = 'Ancestor''s Chosen' AND fd.language = 'Italian'`

### codebase_community_557

- question: Among the posts with a score of over 5, what is the percentage of them being owned by an elder user?
- expected: `SELECT CAST(SUM(IIF(T2.Age > 65, 1, 0)) AS REAL) * 100 / COUNT(T1.Id) FROM posts AS T1 INNER JOIN users AS T2 ON T1.OwnerUserId = T2.Id WHERE T1.Score > 5`
- agent: `SELECT (SUM(CASE WHEN u.Age > 65 THEN 1 ELSE 0 END) * 100.0) / COUNT(*) AS percentage FROM posts p LEFT JOIN users u ON p.OwnerUserId = u.Id WHERE p.Score > 5`

### codebase_community_604

- question: What is the average of the up votes and the average user age for users creating more than 10 posts?
- expected: `SELECT AVG(T1.UpVotes), AVG(T1.Age) FROM users AS T1 INNER JOIN ( SELECT OwnerUserId, COUNT(*) AS post_count FROM posts GROUP BY OwnerUserId HAVING post_count > 10) AS T2 ON T1.Id = T2.OwnerUserId`
- agent: `SELECT COUNT(DISTINCT u.Id) AS qualifying_users, COUNT(u.Age) AS users_with_age, SUM(u.UpVotes) AS total_upvotes, SUM(u.Age) AS total_age FROM users u JOIN ( SELECT OwnerUserId FROM posts WHERE OwnerUserId IS NOT NULL GROUP BY OwnerUserId HAVING COUNT(*) > 10 ) p ON u.Id = p.OwnerUserId;`

### codebase_community_633

- question: Which post by slashnick has the most answers count? State the post ID.
- expected: `SELECT T2.PostId FROM users AS T1 INNER JOIN postHistory AS T2 ON T1.Id = T2.UserId INNER JOIN posts AS T3 ON T2.PostId = T3.Id WHERE T1.DisplayName = 'slashnick' ORDER BY T3.AnswerCount DESC LIMIT 1`
- agent: `SELECT p.Id, p.PostTypeId, p.ParentId, p.Title, p.AnswerCount, p.OwnerUserId, u.DisplayName FROM posts p LEFT JOIN users u ON p.OwnerUserId = u.Id WHERE p.Id IN (7, 351) OR (p.OwnerUserId = 16);`

### codebase_community_634

- question: Among posts by Harvey Motulsky and Noah Snyder, which one has higher popularity?
- expected: `SELECT T1.DisplayName FROM users AS T1 INNER JOIN postHistory AS T2 ON T1.Id = T2.UserId INNER JOIN posts AS T3 ON T2.PostId = T3.Id WHERE T1.DisplayName = 'Harvey Motulsky' OR T1.DisplayName = 'Noah Snyder' GROUP BY T1.DisplayName ORDER BY SUM(T3.ViewCount) DESC LIMIT 1`
- agent: `SELECT u.DisplayName, COUNT(p.Id) AS num_posts, COUNT(CASE WHEN p.PostTypeId = 1 THEN p.Id END) AS num_questions, COALESCE(SUM(CASE WHEN p.PostTypeId = 1 THEN p.ViewCount END), 0) AS total_q_views, COALESCE(MAX(CASE WHEN p.PostTypeId = 1 THEN p.ViewCount END), 0) AS max_q_views FROM users u LEFT JOIN posts p ON p.OwnerUserId = u.Id WHERE u.DisplayName IN ('Harvey Motulsky', 'Noah Snyder') GROUP BY u.Id, u.DisplayName`

### codebase_community_640

- question: Calculate the difference in view count from post posted by Mornington and view count from posts posted by Amos.
- expected: `SELECT SUM(IIF(T1.DisplayName = 'Mornington', T3.ViewCount, 0)) - SUM(IIF(T1.DisplayName = 'Amos', T3.ViewCount, 0)) AS diff FROM users AS T1 INNER JOIN postHistory AS T2 ON T1.Id = T2.UserId INNER JOIN posts AS T3 ON T3.Id = T2.PostId`
- agent: `SELECT COALESCE(SUM(CASE WHEN u.DisplayName = 'mornington' THEN p.ViewCount END), 0) - COALESCE(SUM(CASE WHEN u.DisplayName = 'Amos' THEN p.ViewCount END), 0) AS difference FROM posts p LEFT JOIN users u ON u.Id = p.OwnerUserId WHERE LOWER(u.DisplayName) IN ('mornington', 'amos');`

### codebase_community_678

- question: Which post by Harvey Motulsky has the most views? Please give the id and title of this post.
- expected: `SELECT T2.Id, T2.Title FROM users AS T1 INNER JOIN posts AS T2 ON T1.Id = T2.OwnerUserId WHERE T1.DisplayName = 'Harvey Motulsky' ORDER BY T2.ViewCount DESC LIMIT 1`
- agent: `SELECT p.Id, p.Title, p.ViewCount FROM posts p JOIN users u ON u.Id = p.OwnerUserId WHERE u.DisplayName = 'Harvey Motulsky' ORDER BY p.ViewCount DESC LIMIT 1;`

### codebase_community_685

- question: Identify the total views on the post 'Computer Game Datasets'. Name the user who posted it last time.
- expected: `SELECT T2.ViewCount, T3.DisplayName FROM postHistory AS T1 INNER JOIN posts AS T2 ON T1.PostId = T2.Id INNER JOIN users AS T3 ON T2.LastEditorUserId = T3.Id WHERE T1.Text = 'Computer Game Datasets'`
- agent: `SELECT p.ViewCount, u.DisplayName FROM postHistory ph JOIN posts p ON p.Id = ph.PostId JOIN users u ON u.Id = ph.UserId WHERE ph.Text = 'Computer Game Datasets'`

### codebase_community_707

- question: Among the posts with views ranging from 100 to 150, what is the comment with the highest score?
- expected: `SELECT Text FROM comments WHERE PostId IN ( SELECT Id FROM posts WHERE ViewCount BETWEEN 100 AND 150 ) ORDER BY Score DESC LIMIT 1`
- agent: `SELECT c.Score, COUNT(*) AS num_comments FROM comments c JOIN posts p ON p.Id = c.PostId WHERE p.ViewCount BETWEEN 100 AND 150 GROUP BY c.Score ORDER BY c.Score DESC LIMIT 5;`

### debit_card_specializing_1481

- question: What is the difference in the annual average consumption of the customers with the least amount of consumption paid in CZK for 2013 between SME and LAM, LAM and KAM, and KAM and SME?
- expected: `SELECT CAST(SUM(IIF(T1.Segment = 'SME', T2.Consumption, 0)) AS REAL) / COUNT(T1.CustomerID) - CAST(SUM(IIF(T1.Segment = 'LAM', T2.Consumption, 0)) AS REAL) / COUNT(T1.CustomerID) , CAST(SUM(IIF(T1.Segment = 'LAM', T2.Consumption, 0)) AS REAL) / COUNT(T1.CustomerID) - CAST(SUM(IIF(T1.Segment = 'KAM', T2.Consumption, 0)) AS REAL) / COUNT(T1.CustomerID) , CAST(SUM(IIF(T1.Segment = 'KAM', T2.Consumption, 0)) AS REAL) / COUNT(T1.CustomerID) - CAST(SUM(IIF(T1.Segment = 'SME', T2.Consumption, 0)) AS REAL) / COUNT(T1.CustomerID) FROM customers AS T1 INNER JOIN yearmonth AS T2 ON T1.CustomerID = T2.CustomerID WHERE T1.Currency = 'CZK' AND T2.Consumption = ( SELECT MIN(Consumption) FROM yearmonth ) AND T2.Date BETWEEN 201301 AND 201312`
- agent: `SELECT CustomerID, Date, Consumption FROM yearmonth WHERE Consumption < 0 ORDER BY Date LIMIT 30`

### debit_card_specializing_1484

- question: How many more "discount" gas stations does the Czech Republic have compared to Slovakia?
- expected: `SELECT SUM(IIF(Country = 'CZE', 1, 0)) - SUM(IIF(Country = 'SVK', 1, 0)) FROM gasstations WHERE Segment = 'Discount'`
- agent: `SELECT Country, Segment, COUNT(*) AS cnt FROM gasstations WHERE Country IN ('CZE','SVK') GROUP BY Country, Segment ORDER BY Country, Segment`

### european_football_2_1030

- question: Give the name of the league had the most matches end as draw in the 2016 season?
- expected: `SELECT t2.name FROM Match AS t1 INNER JOIN League AS t2 ON t1.league_id = t2.id WHERE t1.season = '2015/2016' AND t1.home_team_goal = t1.away_team_goal GROUP BY t2.name ORDER BY COUNT(t1.id) DESC LIMIT 1`
- agent: `SELECT l.name AS league_name, SUM(CASE WHEN m.home_team_goal = m.away_team_goal THEN 1 ELSE 0 END) AS draw_count FROM Match m JOIN League l ON m.league_id = l.id WHERE m.season = '2015/2016' GROUP BY l.id, l.name ORDER BY draw_count DESC LIMIT 5;`

### european_football_2_1079

- question: Which player is the tallest?
- expected: `SELECT player_name FROM Player ORDER BY height DESC LIMIT 1`
- agent: `SELECT player_name, height FROM Player WHERE height = (SELECT MAX(height) FROM Player);`

### european_football_2_1134

- question: What is the difference between players 6 and 23's jumping scores?
- expected: `SELECT SUM(CASE WHEN t1.id = 6 THEN t1.jumping ELSE 0 END) - SUM(CASE WHEN t1.id = 23 THEN t1.jumping ELSE 0 END) FROM Player_Attributes AS t1`
- agent: `SELECT id, player_api_id, player_fifa_api_id, jumping FROM Player_Attributes WHERE id IN (6, 23)`

### european_football_2_1135

- question: Please provide top four football players' IDs who are among the lowest potential players and prefer to use the right foot when attacking.
- expected: `SELECT id FROM Player_Attributes WHERE preferred_foot = 'right' ORDER BY potential ASC LIMIT 4`
- agent: `SELECT pa.player_api_id, pa.preferred_foot, pa.potential, COUNT(*) AS rows FROM Player_Attributes pa WHERE pa.potential = (SELECT MIN(potential) FROM Player_Attributes) GROUP BY pa.player_api_id, pa.preferred_foot, pa.potential ORDER BY pa.player_api_id;`

### financial_115

- question: For the branch which located in the south Bohemia with biggest number of inhabitants, what is the percentage of the male clients?
- expected: `SELECT CAST(SUM(T1.gender = 'M') AS REAL) * 100 / COUNT(T1.client_id) FROM client AS T1 INNER JOIN district AS T2 ON T1.district_id = T2.district_id WHERE T2.A3 = 'south Bohemia' GROUP BY T2.A4 ORDER BY T2.A4 DESC LIMIT 1`
- agent: `SELECT COUNT(*) AS total, SUM(CASE WHEN gender='M' THEN 1 ELSE 0 END) AS males FROM client WHERE district_id = 14`

### financial_159

- question: List all the withdrawals in cash transactions that the client with the id 3356 makes.
- expected: `SELECT T4.trans_id FROM client AS T1 INNER JOIN disp AS T2 ON T1.client_id = T2.client_id INNER JOIN account AS T3 ON T2.account_id = T3.account_id INNER JOIN trans AS T4 ON T3.account_id = T4.account_id WHERE T1.client_id = 3356 AND T4.operation = 'VYBER'`
- agent: `SELECT d.account_id, d.type AS disp_type, COUNT(*) AS n FROM client c JOIN disp d ON d.client_id = c.client_id JOIN trans t ON t.account_id = d.account_id WHERE c.client_id = 3356 AND t.operation = 'VYBER' GROUP BY d.account_id, d.type`

### financial_168

- question: What percentage of clients who opened their accounts in the district with an average salary of over 10000 are women?
- expected: `SELECT CAST(SUM(T2.gender = 'F') AS REAL) * 100 / COUNT(T2.client_id) FROM district AS T1 INNER JOIN client AS T2 ON T1.district_id = T2.district_id WHERE T1.A11 > 10000`
- agent: `SELECT type, COUNT(*) AS n FROM disp GROUP BY type;`

### financial_189

- question: Name the account numbers of female clients who are oldest and have lowest average salary?
- expected: `SELECT T3.account_id FROM client AS T1 INNER JOIN district AS T2 ON T1.district_id = T2.district_id INNER JOIN account AS T3 ON T2.district_id = T3.district_id INNER JOIN disp AS T4 ON T1.client_id = T4.client_id AND T4.account_id = T3.account_id WHERE T1.gender = 'F' ORDER BY T1.birth_date ASC, T2.A11 ASC LIMIT 1`
- agent: `SELECT client_id, gender, birth_date, district_id FROM client WHERE gender='F' AND birth_date = (SELECT MIN(birth_date) FROM client WHERE gender='F');`

### financial_95

- question: List out the account numbers of clients who are youngest and have highest average salary?
- expected: `SELECT T1.account_id FROM account AS T1 INNER JOIN disp AS T2 ON T1.account_id = T2.account_id INNER JOIN client AS T3 ON T2.client_id = T3.client_id INNER JOIN district AS T4 on T4.district_id = T1.district_id WHERE T2.client_id = ( SELECT client_id FROM client ORDER BY birth_date DESC LIMIT 1) GROUP BY T4.A11, T1.account_id`
- agent: `SELECT c.client_id, c.birth_date, d.A11 FROM client c JOIN district d ON c.district_id = d.district_id WHERE d.A11 = (SELECT MAX(A11) FROM district) AND c.birth_date = (SELECT MAX(c2.birth_date) FROM client c2 JOIN district d2 ON c2.district_id=d2.district_id WHERE d2.A11=(SELECT MAX(A11) FROM district))`

### formula_1_866

- question: Who was the player that got the lap time of 0:01:27 in the race No. 161? Show his introduction website.
- expected: `SELECT DISTINCT T2.forename, T2.surname, T2.url FROM lapTimes AS T1 INNER JOIN drivers AS T2 ON T2.driverId = T1.driverId WHERE T1.raceId = 161 AND T1.time LIKE '1:27%'`
- agent: `SELECT time, COUNT(*) FROM lapTimes WHERE raceId = 161 AND time LIKE '1:27%' GROUP BY time ORDER BY time;`

### formula_1_877

- question: For all the drivers who finished the game in race No. 872, who is the youngest?
- expected: `SELECT T1.forename, T1.surname FROM drivers AS T1 INNER JOIN results AS T2 ON T2.driverId = T1.driverId WHERE T2.raceId = 872 AND T2.time IS NOT NULL ORDER BY T1.dob DESC LIMIT 1`
- agent: `SELECT d.forename, d.surname, d.dob FROM results r JOIN drivers d ON r.driverId = d.driverId WHERE r.raceId = 872 AND r.time IS NOT NULL ORDER BY d.dob DESC;`

### formula_1_897

- question: Name the driver with the most winning. Mention his nationality and what is his maximum point scores.
- expected: `SELECT T1.forename, T1.surname, T1.nationality, MAX(T2.points) FROM drivers AS T1 INNER JOIN driverStandings AS T2 ON T2.driverId = T1.driverId WHERE T2.wins >= 1 GROUP BY T1.forename, T1.surname, T1.nationality ORDER BY COUNT(T2.wins) DESC LIMIT 1`
- agent: `SELECT r.year, r.round, r.name, ds.points, ds.wins FROM driverStandings ds JOIN races r ON r.raceId = ds.raceId WHERE ds.driverId = 30 AND ds.points >= 140 ORDER BY ds.points DESC LIMIT 10;`

### formula_1_906

- question: Which was Lewis Hamilton first race? What was his points recorded for his first race event?
- expected: `SELECT T1.name, T2.points FROM races AS T1 INNER JOIN driverStandings AS T2 ON T2.raceId = T1.raceId INNER JOIN drivers AS T3 ON T3.driverId = T2.driverId WHERE T3.forename = 'Lewis' AND T3.surname = 'Hamilton' ORDER BY T1.year ASC LIMIT 1`
- agent: `SELECT r.name AS race_name, r.year, r.round, res.points FROM results res JOIN races r ON r.raceId = res.raceId WHERE res.driverId = 1 AND r.year = (SELECT MIN(r2.year) FROM results res2 JOIN races r2 ON r2.raceId = res2.raceId WHERE res2.driverId = 1) ORDER BY r.round ASC LIMIT 1`

### formula_1_909

- question: Among all European Grand Prix races, what is the percentage of the races were hosted in Germany?
- expected: `SELECT CAST(COUNT(CASE WHEN T1.country = 'Germany' THEN T2.circuitID END) AS REAL) * 100 / COUNT(T2.circuitId) FROM circuits AS T1 INNER JOIN races AS T2 ON T2.circuitID = T1.circuitId WHERE T2.name = 'European Grand Prix'`
- agent: `SELECT ROUND(100.0 * SUM(CASE WHEN c.country = 'Germany' THEN 1 ELSE 0 END) / COUNT(*), 2) AS percentage_germany FROM races r JOIN circuits c ON r.circuitId = c.circuitId WHERE r.name = 'European Grand Prix';`

### formula_1_955

- question: What is the average time in seconds of champion for each year, before year 1975?
- expected: `WITH time_in_seconds AS ( SELECT T2.year, T2.raceId, T1.positionOrder, CASE WHEN T1.positionOrder = 1 THEN (CAST(SUBSTR(T1.time, 1, 1) AS REAL) * 3600) + (CAST(SUBSTR(T1.time, 3, 2) AS REAL) * 60) + CAST(SUBSTR(T1.time, 6,2) AS REAL ) + CAST(SUBSTR(T1.time, 9) AS REAL)/1000 ELSE 0 END AS time_seconds FROM results AS T1 INNER JOIN races AS T2 ON T1.raceId = T2.raceId WHERE T1.time IS NOT NULL ), champion_time AS ( SELECT year, raceId, time_seconds FROM time_in_seconds WHERE positionOrder = 1 ) SELECT year, AVG(time_seconds) FROM champion_time WHERE year < 1975 GROUP BY year HAVING AVG(time_seconds) IS NOT NULL`
- agent: `SELECT r.raceId, r.driverId, r.position, r.positionOrder, r.time, r.milliseconds, r.laps FROM results r JOIN races ra ON r.raceId = ra.raceId WHERE ra.year < 1975 AND r.time IS NOT NULL ORDER BY ra.year, ra.round, r.positionOrder LIMIT 30`

### formula_1_972

- question: Which drivers who were born in 1971 and has the fastest lap time on the race? Give id and code of these drivers.
- expected: `SELECT T2.driverId, T2.code FROM results AS T1 INNER JOIN drivers AS T2 on T1.driverId = T2.driverId WHERE STRFTIME('%Y', T2.dob) = '1971' AND T1.fastestLapTime IS NOT NULL`
- agent: `SELECT driverId, code, forename, surname, dob FROM drivers WHERE driverId IN (14,35,37,69);`

### student_club_1317

- question: Among the students from the Student_Club who attended the event "Women's Soccer", how many of them want a T-shirt that's in medium size?
- expected: `SELECT COUNT(T1.event_id) FROM event AS T1 INNER JOIN attendance AS T2 ON T1.event_id = T2.link_to_event INNER JOIN member AS T3 ON T2.link_to_member = T3.member_id WHERE T1.event_name = 'Women''s Soccer' AND T3.t_shirt_size = 'Medium'`
- agent: `SELECT type, name FROM sqlite_master ORDER BY type, name;`

### student_club_1399

- question: Did Maya Mclean attend the 'Women's Soccer' event?
- expected: `SELECT CASE WHEN T3.event_name = 'Women''s Soccer' THEN 'YES' END AS result FROM member AS T1 INNER JOIN attendance AS T2 ON T1.member_id = T2.link_to_member INNER JOIN event AS T3 ON T2.link_to_event = T3.event_id WHERE T1.first_name = 'Maya' AND T1.last_name = 'Mclean'`
- agent: `SELECT m.first_name, m.last_name, e.event_name, a.link_to_member, a.link_to_event FROM attendance a JOIN member m ON m.member_id = a.link_to_member JOIN event e ON e.event_id = a.link_to_event WHERE m.first_name = 'Maya' AND m.last_name = 'Mclean' AND e.event_name = 'Women''s Soccer';`

### student_club_1422

- question: State the category of events were held at MU 215.
- expected: `SELECT DISTINCT T2.category FROM event AS T1 INNER JOIN budget AS T2 ON T1.event_id = T2.link_to_event WHERE T1.location = 'MU 215'`
- agent: `SELECT DISTINCT type FROM event WHERE location = 'MU 215'`

### superhero_728

- question: Rank superheroes from Marvel Comics by their eye color popularity, starting with the most common color.
- expected: `SELECT colour.colour AS EyeColor, COUNT(superhero.id) AS Count, RANK() OVER (ORDER BY COUNT(superhero.id) DESC) AS PopularityRank FROM superhero INNER JOIN colour ON superhero.eye_colour_id = colour.id INNER JOIN publisher ON superhero.publisher_id = publisher.id WHERE publisher.publisher_name = 'Marvel Comics' GROUP BY colour.colour`
- agent: `SELECT c.colour AS eye_colour, COUNT(s.id) AS hero_count FROM superhero s JOIN publisher p ON s.publisher_id = p.id LEFT JOIN colour c ON s.eye_colour_id = c.id WHERE p.publisher_name = 'Marvel Comics' GROUP BY c.colour ORDER BY hero_count DESC, c.colour`

### superhero_751

- question: List down at least five superpowers of male superheroes.
- expected: `SELECT T3.power_name FROM superhero AS T1 INNER JOIN hero_power AS T2 ON T1.id = T2.hero_id INNER JOIN superpower AS T3 ON T3.id = T2.power_id INNER JOIN gender AS T4 ON T4.id = T1.gender_id WHERE T4.gender = 'Male' LIMIT 5`
- agent: `SELECT DISTINCT sp.power_name FROM superhero s JOIN gender g ON s.gender_id = g.id JOIN hero_power hp ON hp.hero_id = s.id JOIN superpower sp ON sp.id = hp.power_id WHERE g.gender = 'Male' ORDER BY sp.power_name;`

### superhero_758

- question: Provide the hair colour of the human superhero who is 185 cm tall.
- expected: `SELECT DISTINCT T3.colour FROM superhero AS T1 INNER JOIN race AS T2 ON T1.race_id = T2.id INNER JOIN colour AS T3 ON T1.hair_colour_id = T3.id WHERE T1.height_cm = 185 AND T2.race = 'Human'`
- agent: `SELECT s.superhero_name, c.colour FROM superhero s JOIN race r ON s.race_id = r.id JOIN colour c ON s.hair_colour_id = c.id WHERE r.race = 'Human' AND s.height_cm = 185 ORDER BY s.superhero_name;`

### thrombosis_prediction_1168

- question: The oldest SJS patient's medical laboratory work was completed on what date, and what age was the patient when they initially arrived at the hospital?
- expected: `SELECT T1.Date, STRFTIME('%Y', T2.`First Date`) - STRFTIME('%Y', T2.Birthday),T2.Birthday FROM Laboratory AS T1 INNER JOIN Patient AS T2 ON T1.ID = T2.ID WHERE T2.Diagnosis = 'SJS' AND T2.Birthday IS NOT NULL ORDER BY T2.Birthday ASC LIMIT 1`
- agent: `SELECT * FROM Examination WHERE ID = 125619`

### thrombosis_prediction_1201

- question: What percentage of patients who were born in 1980 and were diagnosed with RA are women?
- expected: `SELECT CAST(SUM(CASE WHEN SEX = 'F' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(ID) FROM Patient WHERE Diagnosis = 'RA' AND STRFTIME('%Y', Birthday) = '1980'`
- agent: `SELECT COUNT(*) AS total, SUM(CASE WHEN SEX = 'F' THEN 1 ELSE 0 END) AS female, 100.0 * SUM(CASE WHEN SEX = 'F' THEN 1 ELSE 0 END) / COUNT(*) AS pct_female FROM Patient WHERE CAST(strftime('%Y', Birthday) AS INTEGER) = 1980 AND Diagnosis = 'RA';`

### thrombosis_prediction_1209

- question: Please provide the diagnosis of patients with ALT glutamic pylvic transaminase beyond the normal range by ascending order of their date of birth.
- expected: `SELECT DISTINCT T1.Diagnosis FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE T2.GPT > 60 ORDER BY T1.Birthday ASC`
- agent: `SELECT p.Diagnosis FROM Patient p WHERE EXISTS (SELECT 1 FROM Laboratory l WHERE l.ID = p.ID AND l.GPT > 60) ORDER BY p.Birthday ASC, p.ID ASC`

### thrombosis_prediction_1252

- question: Among the patients with a normal Ig G level, how many of them have symptoms?
- expected: `SELECT COUNT(T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID INNER JOIN Examination AS T3 ON T3.ID = T2.ID WHERE T2.IGG BETWEEN 900 AND 2000 AND T3.Symptoms IS NOT NULL`
- agent: `SELECT COUNT(DISTINCT l.ID) AS patient_count FROM Laboratory l JOIN Examination e ON l.ID = e.ID WHERE l.IGG > 900 AND l.IGG < 2000 AND e.Symptoms IS NOT NULL;`

### thrombosis_prediction_1256

- question: How many patients with a abnormal C-reactive protein don't have their data recorded?
- expected: `SELECT COUNT(T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE (T2.CRP = '+' ) AND T1.Description IS NULL`
- agent: `SELECT COUNT(DISTINCT p.ID) FROM Patient p JOIN Laboratory l ON l.ID = p.ID WHERE p.Description IS NULL AND l.CRP = '+';`

### toxicology_212

- question: Which element is the least numerous in non-carcinogenic molecules?
- expected: `SELECT T.element FROM (SELECT T1.element, COUNT(DISTINCT T1.molecule_id) FROM atom AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T2.label = '-' GROUP BY T1.element ORDER BY COUNT(DISTINCT T1.molecule_id) ASC LIMIT 1) t`
- agent: `SELECT a.element, COUNT(*) AS cnt FROM atom a JOIN molecule m ON a.molecule_id = m.molecule_id WHERE m.label = '-' GROUP BY a.element ORDER BY cnt ASC LIMIT 20;`

### toxicology_268

- question: What are the elements for bond id TR001_10_11?
- expected: `SELECT T2.element FROM connected AS T1 INNER JOIN atom AS T2 ON T1.atom_id = T2.atom_id WHERE T1.bond_id = 'TR001_10_11'`
- agent: `SELECT a.atom_id, a.element FROM connected c JOIN atom a ON a.atom_id = c.atom_id OR a.atom_id = c.atom_id2 WHERE c.bond_id = 'TR001_10_11';`

### toxicology_282

- question: What is the ratio of Hydrogen elements in molecule ID TR006? List the ratio with its label.
- expected: `WITH SubQuery AS (SELECT DISTINCT T1.atom_id, T1.element, T1.molecule_id, T2.label FROM atom AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T2.molecule_id = 'TR006') SELECT CAST(COUNT(CASE WHEN element = 'h' THEN atom_id ELSE NULL END) AS REAL) / (CASE WHEN COUNT(atom_id) = 0 THEN NULL ELSE COUNT(atom_id) END) AS ratio, label FROM SubQuery GROUP BY label`
- agent: `SELECT COUNT(*) AS total_atoms, SUM(CASE WHEN element = 'h' THEN 1 ELSE 0 END) AS hydrogen_atoms FROM atom WHERE molecule_id = 'TR006';`

