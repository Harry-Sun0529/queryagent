# QueryAgent Eval Report — public subset

- model: `deepseek-v4-flash`
- cases: 100
- scoring: v2 (query trajectory and completion reported separately)
- Natural-language answer correctness is not measured.

## Summary

| metric | value |
|---|---|
| first-execution pass rate | 31/100 (31%) |
| query-trajectory hit rate | 43/100 (43%) |
| completed with SQL hit | 42/100 (42%) |
| metric hit rate | n/a |
| clarify-behaviour accuracy | n/a |
| average tool calls | 3.11 |
| tokens per case (in+out) | 11,878 |
| prompt cache hit rate | 86% |
| latency per case | 14.2s |
| cost per case (upper bound) | $0.0029 |
| unmeasured (upstream unreachable) | 0 |

## Cases

| id | kind | SQL hit | completed | first try | retries | tool calls | note |
|---|---|---|---|---|---|---|---|
| california_schools_36 | public | ❌ | ✅ | ❌ | 0 | 5 | result sets differ |
| california_schools_37 | public | ❌ | ❌ | ❌ | 0 | 8 | no final answer after 8 turns |
| california_schools_39 | public | ❌ | ✅ | ❌ | 0 | 5 | result sets differ |
| california_schools_41 | public | ❌ | ❌ | ❌ | 1 | 8 | no final answer after 8 turns |
| california_schools_45 | public | ❌ | ✅ | ❌ | 0 | 3 | result sets differ |
| california_schools_72 | public | ❌ | ✅ | ❌ | 0 | 6 | result sets differ |
| california_schools_85 | public | ❌ | ✅ | ❌ | 1 | 5 | result sets differ |
| card_games_340 | public | ❌ | ✅ | ❌ | 0 | 2 | result sets differ |
| card_games_345 | public | ❌ | ✅ | ❌ | 0 | 3 | result sets differ |
| card_games_346 | public | ❌ | ✅ | ❌ | 0 | 5 | result sets differ |
| card_games_358 | public | ❌ | ✅ | ❌ | 0 | 1 | result sets differ |
| card_games_368 | public | ✅ | ✅ | ✅ | 0 | 1 |  |
| card_games_379 | public | ✅ | ✅ | ✅ | 0 | 7 |  |
| card_games_397 | public | ❌ | ✅ | ❌ | 0 | 4 | result sets differ |
| card_games_407 | public | ❌ | ❌ | ❌ | 1 | 7 | no final answer after 8 turns |
| card_games_409 | public | ✅ | ✅ | ✅ | 0 | 2 |  |
| card_games_412 | public | ❌ | ✅ | ❌ | 0 | 4 | result sets differ |
| card_games_415 | public | ✅ | ✅ | ❌ | 0 | 4 |  |
| card_games_422 | public | ❌ | ✅ | ❌ | 0 | 1 | result sets differ |
| card_games_459 | public | ❌ | ✅ | ❌ | 0 | 1 | result sets differ |
| card_games_468 | public | ✅ | ✅ | ✅ | 0 | 1 |  |
| card_games_479 | public | ✅ | ✅ | ✅ | 0 | 1 |  |
| card_games_480 | public | ❌ | ❌ | ❌ | 0 | 8 | no final answer after 8 turns |
| codebase_community_539 | public | ❌ | ✅ | ❌ | 0 | 1 | result sets differ |
| codebase_community_557 | public | ❌ | ✅ | ❌ | 0 | 2 | result sets differ |
| codebase_community_573 | public | ✅ | ✅ | ✅ | 0 | 3 |  |
| codebase_community_581 | public | ✅ | ✅ | ✅ | 0 | 1 |  |
| codebase_community_604 | public | ❌ | ✅ | ❌ | 0 | 5 | result sets differ |
| codebase_community_633 | public | ❌ | ❌ | ❌ | 0 | 8 | no final answer after 8 turns |
| codebase_community_634 | public | ❌ | ✅ | ❌ | 0 | 5 | result sets differ |
| codebase_community_640 | public | ❌ | ❌ | ❌ | 0 | 7 | multiple SQL statements are not allowed (3 found); send exactly one SELECT |
| codebase_community_678 | public | ❌ | ✅ | ❌ | 0 | 1 | result sets differ |
| codebase_community_685 | public | ❌ | ✅ | ❌ | 0 | 6 | result sets differ |
| codebase_community_701 | public | ❌ | ❌ | ❌ | 0 | 2 | reference expected_sql failed (case bug?): interrupted |
| codebase_community_707 | public | ✅ | ✅ | ✅ | 0 | 1 |  |
| debit_card_specializing_1481 | public | ❌ | ❌ | ❌ | 0 | 8 | no final answer after 8 turns |
| debit_card_specializing_1484 | public | ✅ | ✅ | ✅ | 0 | 1 |  |
| european_football_2_1030 | public | ❌ | ✅ | ❌ | 0 | 1 | result sets differ |
| european_football_2_1079 | public | ❌ | ✅ | ❌ | 0 | 2 | result sets differ |
| european_football_2_1134 | public | ✅ | ✅ | ❌ | 0 | 2 |  |
| european_football_2_1135 | public | ❌ | ❌ | ❌ | 0 | 8 | no final answer after 8 turns |
| financial_115 | public | ❌ | ✅ | ❌ | 0 | 3 | result sets differ |
| financial_117 | public | ✅ | ✅ | ✅ | 0 | 1 |  |
| financial_128 | public | ✅ | ❌ | ❌ | 0 | 5 | multiple SQL statements are not allowed (2 found); send exactly one SELECT |
| financial_159 | public | ❌ | ✅ | ❌ | 0 | 4 | result sets differ |
| financial_168 | public | ❌ | ✅ | ❌ | 0 | 5 | result sets differ |
| financial_169 | public | ❌ | ❌ | ❌ | 0 | 3 | multiple SQL statements are not allowed (2 found); send exactly one SELECT |
| financial_189 | public | ❌ | ❌ | ❌ | 0 | 8 | no final answer after 8 turns |
| financial_92 | public | ✅ | ✅ | ❌ | 0 | 4 |  |
| financial_93 | public | ✅ | ✅ | ❌ | 0 | 3 |  |
| financial_95 | public | ❌ | ❌ | ❌ | 0 | 8 | no final answer after 8 turns |
| formula_1_866 | public | ❌ | ✅ | ❌ | 0 | 6 | result sets differ |
| formula_1_869 | public | ❌ | ✅ | ❌ | 0 | 1 | result sets differ |
| formula_1_877 | public | ❌ | ✅ | ❌ | 0 | 1 | result sets differ |
| formula_1_897 | public | ❌ | ✅ | ❌ | 0 | 3 | result sets differ |
| formula_1_906 | public | ❌ | ✅ | ❌ | 0 | 3 | result sets differ |
| formula_1_909 | public | ✅ | ✅ | ✅ | 0 | 1 |  |
| formula_1_910 | public | ✅ | ✅ | ✅ | 0 | 1 |  |
| formula_1_940 | public | ✅ | ✅ | ❌ | 0 | 2 |  |
| formula_1_955 | public | ❌ | ✅ | ❌ | 0 | 2 | result sets differ |
| formula_1_960 | public | ✅ | ✅ | ✅ | 0 | 1 |  |
| formula_1_972 | public | ❌ | ✅ | ❌ | 0 | 1 | result sets differ |
| formula_1_977 | public | ✅ | ✅ | ✅ | 0 | 1 |  |
| formula_1_990 | public | ❌ | ✅ | ❌ | 0 | 2 | result sets differ |
| student_club_1317 | public | ✅ | ✅ | ❌ | 0 | 7 |  |
| student_club_1346 | public | ✅ | ✅ | ✅ | 0 | 1 |  |
| student_club_1350 | public | ✅ | ✅ | ❌ | 0 | 3 |  |
| student_club_1352 | public | ✅ | ✅ | ✅ | 0 | 1 |  |
| student_club_1361 | public | ✅ | ✅ | ✅ | 0 | 1 |  |
| student_club_1376 | public | ❌ | ✅ | ❌ | 0 | 6 | result sets differ |
| student_club_1378 | public | ✅ | ✅ | ✅ | 0 | 1 |  |
| student_club_1399 | public | ❌ | ✅ | ❌ | 0 | 2 | result sets differ |
| student_club_1405 | public | ✅ | ✅ | ❌ | 0 | 3 |  |
| student_club_1409 | public | ✅ | ✅ | ✅ | 0 | 1 |  |
| student_club_1422 | public | ❌ | ✅ | ❌ | 0 | 1 | result sets differ |
| student_club_1426 | public | ✅ | ✅ | ✅ | 0 | 1 |  |
| superhero_717 | public | ✅ | ✅ | ✅ | 0 | 1 |  |
| superhero_719 | public | ✅ | ✅ | ✅ | 0 | 1 |  |
| superhero_728 | public | ❌ | ✅ | ❌ | 0 | 1 | result sets differ |
| superhero_730 | public | ✅ | ✅ | ✅ | 0 | 4 |  |
| superhero_733 | public | ✅ | ✅ | ✅ | 0 | 1 |  |
| superhero_751 | public | ❌ | ✅ | ❌ | 0 | 1 | result sets differ |
| superhero_758 | public | ✅ | ✅ | ❌ | 0 | 4 |  |
| superhero_765 | public | ✅ | ✅ | ✅ | 0 | 1 |  |
| superhero_806 | public | ✅ | ✅ | ✅ | 0 | 1 |  |
| thrombosis_prediction_1168 | public | ❌ | ❌ | ❌ | 0 | 8 | no final answer after 8 turns |
| thrombosis_prediction_1195 | public | ✅ | ✅ | ❌ | 0 | 3 |  |
| thrombosis_prediction_1201 | public | ❌ | ✅ | ❌ | 0 | 2 | result sets differ |
| thrombosis_prediction_1209 | public | ✅ | ✅ | ✅ | 0 | 4 |  |
| thrombosis_prediction_1252 | public | ❌ | ✅ | ❌ | 0 | 3 | result sets differ |
| thrombosis_prediction_1256 | public | ❌ | ✅ | ❌ | 0 | 3 | result sets differ |
| thrombosis_prediction_1270 | public | ✅ | ✅ | ✅ | 0 | 2 |  |
| toxicology_200 | public | ✅ | ✅ | ✅ | 0 | 1 |  |
| toxicology_206 | public | ✅ | ✅ | ✅ | 0 | 2 |  |
| toxicology_212 | public | ❌ | ✅ | ❌ | 0 | 2 | result sets differ |
| toxicology_228 | public | ✅ | ✅ | ✅ | 0 | 1 |  |
| toxicology_242 | public | ❌ | ✅ | ❌ | 0 | 3 | result sets differ |
| toxicology_268 | public | ❌ | ✅ | ❌ | 0 | 1 | result sets differ |
| toxicology_282 | public | ❌ | ✅ | ❌ | 0 | 3 | result sets differ |
| toxicology_327 | public | ✅ | ✅ | ❌ | 0 | 5 |  |

## Failing cases — SQL comparison

### california_schools_36

- question: Under whose administration is the school with the highest number of students scoring 1500 or more on the SAT? Indicate their full names.
- expected: `SELECT T2.AdmFName1, T2.AdmLName1, T2.AdmFName2, T2.AdmLName2, T2.AdmFName3, T2.AdmLName3 FROM satscores AS T1 INNER JOIN schools AS T2 ON T1.cds = T2.CDSCode ORDER BY T1.NumGE1500 DESC LIMIT 1`
- agent: `SELECT sname, dname, cds, NumGE1500 FROM satscores WHERE rtype='S' AND NumGE1500 = (SELECT MAX(NumGE1500) FROM satscores WHERE rtype='S')`

### california_schools_37

- question: What is the complete address of the school with the lowest excellence rate? Indicate the Street, City, Zip and State.
- expected: `SELECT T2.Street, T2.City, T2.State, T2.Zip FROM satscores AS T1 INNER JOIN schools AS T2 ON T1.cds = T2.CDSCode ORDER BY CAST(T1.NumGE1500 AS REAL) / T1.NumTstTakr ASC LIMIT 1`
- agent: `SELECT s.cds, s.sname, s.NumTstTakr, s.NumGE1500, (s.NumGE1500 * 1.0) / s.NumTstTakr AS rate FROM satscores s WHERE s.rtype='S' AND s.NumTstTakr > 0 AND s.NumGE1500 IS NOT NULL ORDER BY rate ASC LIMIT 10`

### california_schools_39

- question: What is the average number of test takers from Fresno schools that opened between 1/1/1980 and 12/31/1980?
- expected: `SELECT AVG(T1.NumTstTakr) FROM satscores AS T1 INNER JOIN schools AS T2 ON T1.cds = T2.CDSCode WHERE strftime('%Y', T2.OpenDate) = '1980' AND T2.County = 'Fresno'`
- agent: `SELECT s.CDSCode, s.School, s.OpenDate, t.rtype, t.sname, t.cname, t.NumTstTakr FROM schools s JOIN satscores t ON t.cds = s.CDSCode WHERE s.County = 'Fresno' AND s.OpenDate BETWEEN '1980-01-01' AND '1980-12-31' ORDER BY s.CDSCode`

### california_schools_41

- question: List the names of virtual schools that are among the top 5 in their respective counties based on average reading scores.
- expected: `SELECT School FROM (SELECT T2.School,T1.AvgScrRead, RANK() OVER (PARTITION BY T2.County ORDER BY T1.AvgScrRead DESC) AS rnk FROM satscores AS T1 INNER JOIN schools AS T2 ON T1.cds = T2.CDSCode WHERE T2.Virtual = 'F' ) ranked_schools WHERE rnk <= 5`
- agent: `WITH ranked AS ( SELECT sc.School, sc.County, sc.Virtual, st.AvgScrRead, RANK() OVER (PARTITION BY sc.County ORDER BY st.AvgScrRead DESC) AS rnk FROM satscores st JOIN schools sc ON sc.CDSCode = st.cds WHERE st.rtype = 'S' AND st.AvgScrRead IS NOT NULL ) SELECT School, County, AvgScrRead, rnk FROM ranked WHERE Virtual = 'F' ORDER BY County, rnk`

### california_schools_45

- question: What is the average writing score of each of the schools managed by Ricci Ulrich? List the schools and the corresponding average writing scores.
- expected: `SELECT T2.School, T1.AvgScrWrite FROM satscores AS T1 INNER JOIN schools AS T2 ON T1.cds = T2.CDSCode WHERE T2.AdmFName1 = 'Ricci' AND T2.AdmLName1 = 'Ulrich'`
- agent: `SELECT CDSCode, School, AdmFName1, AdmLName1, AdmFName2, AdmLName2, AdmFName3, AdmLName3 FROM schools WHERE UPPER(COALESCE(AdmFName1,'') || ' ' || COALESCE(AdmLName1,'')) LIKE '%RICCI%ULRICH%' OR UPPER(COALESCE(AdmFName2,'') || ' ' || COALESCE(AdmLName2,'')) LIKE '%RICCI%ULRICH%' OR UPPER(COALESCE(AdmFName3,'') || ' ' || COALESCE(AdmLName3,'')) LIKE '%RICCI%ULRICH%';`

### california_schools_72

- question: How many students from the ages of 5 to 17 are enrolled at the State Special School school in Fremont for the 2014-2015 academic year?
- expected: `SELECT T1.`Enrollment (Ages 5-17)` FROM frpm AS T1 INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode WHERE T2.EdOpsCode = 'SSS' AND T2.City = 'Fremont' AND T1.`Academic Year` BETWEEN 2014 AND 2015`
- agent: `SELECT s.School, f."Enrollment (Ages 5-17)" AS enroll_517 FROM frpm f JOIN schools s ON s.CDSCode = f.CDSCode WHERE f."Academic Year" = '2014-2015' AND s.EdOpsCode = 'SSS' AND s.City = 'Fremont';`

### california_schools_85

- question: What is the Percent (%) Eligible Free (K-12) in the school administered by an administrator whose first name is Alusine. List the district code of the school.
- expected: `SELECT T1.`Free Meal Count (K-12)` * 100 / T1.`Enrollment (K-12)`, T1.`District Code` FROM frpm AS T1 INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode WHERE T2.AdmFName1 = 'Alusine'`
- agent: `SELECT f."District Code", (f."Free Meal Count (K-12)" / f."Enrollment (K-12)") * 100.0 AS pct_eligible_free FROM schools sc JOIN frpm f ON f.CDSCode = sc.CDSCode WHERE (sc.AdmFName1 = 'Alusine' OR sc.AdmFName2 = 'Alusine' OR sc.AdmFName3 = 'Alusine') AND f."Enrollment (K-12)" > 0;`

### card_games_340

- question: Which are the cards that have incredibly powerful foils.
- expected: `SELECT id FROM cards WHERE cardKingdomFoilId IS NOT NULL AND cardKingdomId IS NOT NULL`
- agent: `SELECT COUNT(*) AS total_rows, COUNT(DISTINCT name) AS distinct_names FROM cards WHERE cardKingdomFoilId IS NOT NULL AND cardKingdomId IS NOT NULL`

### card_games_345

- question: For artifact type of cards that do not have multiple faces on the same card, state its legalities status for vintage play format.
- expected: `SELECT DISTINCT T2.status FROM cards AS T1 INNER JOIN legalities AS T2 ON T1.uuid = T2.uuid WHERE T1.type = 'Artifact' AND T2.format = 'vintage' AND T1.side IS NULL`
- agent: `SELECT DISTINCT l.status, c.name FROM cards c JOIN legalities l ON l.uuid = c.uuid WHERE c.types = 'Artifact' AND c.side IS NULL AND l.format = 'vintage' AND l.status IN ('Banned', 'Restricted') ORDER BY l.status, c.name;`

### card_games_346

- question: List all the card id and artist with unknown power which are legal for commander play format.
- expected: `SELECT T1.id, T1.artist FROM cards AS T1 INNER JOIN legalities AS T2 ON T1.uuid = T2.uuid WHERE T2.status = 'Legal' AND T2.format = 'commander' AND (T1.power IS NULL OR T1.power = '*')`
- agent: `SELECT COUNT(DISTINCT c.id) AS distinct_ids FROM cards c JOIN legalities l ON l.uuid = c.uuid WHERE (c.power = '*' OR c.power IS NULL) AND l.format = 'commander' AND l.status = 'Legal';`

### card_games_358

- question: What is the border color of card "Ancestor's Chosen"?
- expected: `SELECT DISTINCT borderColor FROM cards WHERE name = 'Ancestor''s Chosen'`
- agent: `SELECT borderColor FROM cards WHERE name = 'Ancestor''s Chosen' LIMIT 5;`

### card_games_397

- question: What is the mana cost of cards with a normal layout, a 2003 frame version, with a black border color, and available in paper and mtgo?
- expected: `SELECT manaCost FROM cards WHERE availability = 'mtgo,paper' AND borderColor = 'black' AND frameVersion = 2003 AND layout = 'normal'`
- agent: `SELECT availability, COUNT(*) AS cnt FROM cards WHERE availability LIKE '%paper%' AND availability LIKE '%mtgo%' GROUP BY availability ORDER BY cnt DESC;`

### card_games_407

- question: Lists all types of cards in German.
- expected: `SELECT T1.subtypes, T1.supertypes FROM cards AS T1 INNER JOIN foreign_data AS T2 ON T1.uuid = T2.uuid WHERE T2.language = 'German' AND T1.subtypes IS NOT NULL AND T1.supertypes IS NOT NULL`
- agent: `SELECT COUNT(*) AS rows_with_dups, SUM(cnt) AS total FROM ( SELECT uuid, COUNT(*) AS cnt FROM foreign_data WHERE language = 'German' GROUP BY uuid HAVING COUNT(*) > 1 )`

### card_games_412

- question: What is the foreign name of the card in French of type Creature, normal layout and black border color, by artist Matthew D. Wilson?
- expected: `SELECT name FROM foreign_data WHERE uuid IN ( SELECT uuid FROM cards WHERE types = 'Creature' AND layout = 'normal' AND borderColor = 'black' AND artist = 'Matthew D. Wilson' ) AND language = 'French'`
- agent: `SELECT c.name, c.types, c.type, c.setCode, f.name AS french FROM cards c JOIN foreign_data f ON c.uuid = f.uuid WHERE c.type LIKE '%Creature%' AND c.layout = 'normal' AND c.borderColor = 'black' AND c.artist = 'Matthew D. Wilson' AND f.language = 'French' LIMIT 5`

### card_games_422

- question: What is the language of the card with the multiverse number 149934?
- expected: `SELECT language FROM foreign_data WHERE multiverseid = 149934`
- agent: `SELECT name, language, multiverseid FROM foreign_data WHERE multiverseid = 149934;`

### card_games_459

- question: Which card costs more converted mana, "Serra Angel" or "Shrine Keeper"?
- expected: `SELECT name FROM cards WHERE name IN ('Serra Angel', 'Shrine Keeper') ORDER BY convertedManaCost DESC LIMIT 1`
- agent: `SELECT name, convertedManaCost, setCode FROM cards WHERE name IN ('Serra Angel', 'Shrine Keeper') GROUP BY name, convertedManaCost, setCode ORDER BY name`

### card_games_480

- question: What is the Italian flavor text of the card "Ancestor's Chosen"?
- expected: `SELECT T2.flavorText FROM cards AS T1 INNER JOIN foreign_data AS T2 ON T2.uuid = T1.uuid WHERE T1.name = 'Ancestor''s Chosen' AND T2.language = 'Italian'`
- agent: `SELECT setCode, name, flavorText FROM cards WHERE name = 'Ancestor''s Chosen'`

### codebase_community_539

- question: Who is the owner of the post "Eliciting priors from experts"?
- expected: `SELECT T2.DisplayName FROM posts AS T1 INNER JOIN users AS T2 ON T1.OwnerUserId = T2.Id WHERE T1.Title = 'Eliciting priors from experts'`
- agent: `SELECT p.Id, p.OwnerUserId, p.OwnerDisplayName, u.DisplayName AS UserDisplayName FROM posts p LEFT JOIN users u ON u.Id = p.OwnerUserId WHERE p.Title = 'Eliciting priors from experts'`

### codebase_community_557

- question: Among the posts with a score of over 5, what is the percentage of them being owned by an elder user?
- expected: `SELECT CAST(SUM(IIF(T2.Age > 65, 1, 0)) AS REAL) * 100 / COUNT(T1.Id) FROM posts AS T1 INNER JOIN users AS T2 ON T1.OwnerUserId = T2.Id WHERE T1.Score > 5`
- agent: `SELECT COUNT(*) AS total_posts, SUM(CASE WHEN u.Age > 65 THEN 1 ELSE 0 END) AS elder_owned FROM posts p LEFT JOIN users u ON p.OwnerUserId = u.Id WHERE p.Score > 5;`

### codebase_community_604

- question: What is the average of the up votes and the average user age for users creating more than 10 posts?
- expected: `SELECT AVG(T1.UpVotes), AVG(T1.Age) FROM users AS T1 INNER JOIN ( SELECT OwnerUserId, COUNT(*) AS post_count FROM posts GROUP BY OwnerUserId HAVING post_count > 10) AS T2 ON T1.Id = T2.OwnerUserId`
- agent: `WITH UserPostCounts AS ( SELECT OwnerUserId AS UserId, COUNT(*) AS PostCount FROM posts WHERE OwnerUserId IS NOT NULL GROUP BY OwnerUserId ) SELECT 1.0 * SUM(u.UpVotes) / COUNT(u.Id) AS AverageUpVotes, 1.0 * SUM(u.Age) / COUNT(u.Id) AS AverageAge FROM UserPostCounts upc JOIN users u ON u.Id = upc.UserId WHERE upc.PostCount > 10;`

### codebase_community_633

- question: Which post by slashnick has the most answers count? State the post ID.
- expected: `SELECT T2.PostId FROM users AS T1 INNER JOIN postHistory AS T2 ON T1.Id = T2.UserId INNER JOIN posts AS T3 ON T2.PostId = T3.Id WHERE T1.DisplayName = 'slashnick' ORDER BY T3.AnswerCount DESC LIMIT 1`
- agent: `SELECT Id, PostTypeId, AnswerCount, Score, Title, OwnerUserId, OwnerDisplayName FROM posts WHERE Id IN (7, 351);`

### codebase_community_634

- question: Among posts by Harvey Motulsky and Noah Snyder, which one has higher popularity?
- expected: `SELECT T1.DisplayName FROM users AS T1 INNER JOIN postHistory AS T2 ON T1.Id = T2.UserId INNER JOIN posts AS T3 ON T2.PostId = T3.Id WHERE T1.DisplayName = 'Harvey Motulsky' OR T1.DisplayName = 'Noah Snyder' GROUP BY T1.DisplayName ORDER BY SUM(T3.ViewCount) DESC LIMIT 1`
- agent: `SELECT u.DisplayName, COALESCE(SUM(p.ViewCount), 0) AS total_views, COUNT(p.Id) AS num_posts FROM users u LEFT JOIN posts p ON p.OwnerUserId = u.Id WHERE u.DisplayName IN ('Harvey Motulsky', 'Noah Snyder') GROUP BY u.DisplayName ORDER BY total_views DESC;`

### codebase_community_640

- question: Calculate the difference in view count from post posted by Mornington and view count from posts posted by Amos.
- expected: `SELECT SUM(IIF(T1.DisplayName = 'Mornington', T3.ViewCount, 0)) - SUM(IIF(T1.DisplayName = 'Amos', T3.ViewCount, 0)) AS diff FROM users AS T1 INNER JOIN postHistory AS T2 ON T1.Id = T2.UserId INNER JOIN posts AS T3 ON T3.Id = T2.PostId`
- agent: `SELECT 'posts' AS src, Id, OwnerUserId AS uid, OwnerDisplayName AS dn FROM posts WHERE OwnerDisplayName LIKE '%Mornington%' OR OwnerUserId = 47 UNION ALL SELECT 'comments', Id, UserId, UserDisplayName FROM comments WHERE UserDisplayName LIKE '%Mornington%' OR UserId = 47 UNION ALL SELECT 'postHistory', Id, UserId, UserDisplayName FROM postHistory WHERE UserDisplayName LIKE '%Mornington%' OR UserId = 47;`

### codebase_community_678

- question: Which post by Harvey Motulsky has the most views? Please give the id and title of this post.
- expected: `SELECT T2.Id, T2.Title FROM users AS T1 INNER JOIN posts AS T2 ON T1.Id = T2.OwnerUserId WHERE T1.DisplayName = 'Harvey Motulsky' ORDER BY T2.ViewCount DESC LIMIT 1`
- agent: `SELECT p.Id, p.Title, p.ViewCount FROM posts p JOIN users u ON p.OwnerUserId = u.Id WHERE u.DisplayName = 'Harvey Motulsky' ORDER BY p.ViewCount DESC LIMIT 5`

### codebase_community_685

- question: Identify the total views on the post 'Computer Game Datasets'. Name the user who posted it last time.
- expected: `SELECT T2.ViewCount, T3.DisplayName FROM postHistory AS T1 INNER JOIN posts AS T2 ON T1.PostId = T2.Id INNER JOIN users AS T3 ON T2.LastEditorUserId = T3.Id WHERE T1.Text = 'Computer Game Datasets'`
- agent: `WITH target AS ( SELECT ph.PostId, ph.UserId FROM postHistory ph WHERE ph.Text = 'Computer Game Datasets' ORDER BY ph.CreationDate DESC, ph.Id DESC LIMIT 1 ) SELECT p.ViewCount AS total_views, u.DisplayName AS poster_name FROM target t JOIN posts p ON p.Id = t.PostId JOIN users u ON u.Id = t.UserId`

### debit_card_specializing_1481

- question: What is the difference in the annual average consumption of the customers with the least amount of consumption paid in CZK for 2013 between SME and LAM, LAM and KAM, and KAM and SME?
- expected: `SELECT CAST(SUM(IIF(T1.Segment = 'SME', T2.Consumption, 0)) AS REAL) / COUNT(T1.CustomerID) - CAST(SUM(IIF(T1.Segment = 'LAM', T2.Consumption, 0)) AS REAL) / COUNT(T1.CustomerID) , CAST(SUM(IIF(T1.Segment = 'LAM', T2.Consumption, 0)) AS REAL) / COUNT(T1.CustomerID) - CAST(SUM(IIF(T1.Segment = 'KAM', T2.Consumption, 0)) AS REAL) / COUNT(T1.CustomerID) , CAST(SUM(IIF(T1.Segment = 'KAM', T2.Consumption, 0)) AS REAL) / COUNT(T1.CustomerID) - CAST(SUM(IIF(T1.Segment = 'SME', T2.Consumption, 0)) AS REAL) / COUNT(T1.CustomerID) FROM customers AS T1 INNER JOIN yearmonth AS T2 ON T1.CustomerID = T2.CustomerID WHERE T1.Currency = 'CZK' AND T2.Consumption = ( SELECT MIN(Consumption) FROM yearmonth ) AND T2.Date BETWEEN 201301 AND 201312`
- agent: `SELECT * FROM transactions_1k LIMIT 10`

### european_football_2_1030

- question: Give the name of the league had the most matches end as draw in the 2016 season?
- expected: `SELECT t2.name FROM Match AS t1 INNER JOIN League AS t2 ON t1.league_id = t2.id WHERE t1.season = '2015/2016' AND t1.home_team_goal = t1.away_team_goal GROUP BY t2.name ORDER BY COUNT(t1.id) DESC LIMIT 1`
- agent: `SELECT l.name AS league_name, SUM(CASE WHEN m.home_team_goal = m.away_team_goal THEN 1 ELSE 0 END) AS draw_count FROM Match m JOIN League l ON l.id = m.league_id WHERE m.season = '2015/2016' GROUP BY l.name ORDER BY draw_count DESC LIMIT 1;`

### european_football_2_1079

- question: Which player is the tallest?
- expected: `SELECT player_name FROM Player ORDER BY height DESC LIMIT 1`
- agent: `SELECT player_name, height FROM Player WHERE height = (SELECT MAX(height) FROM Player);`

### european_football_2_1135

- question: Please provide top four football players' IDs who are among the lowest potential players and prefer to use the right foot when attacking.
- expected: `SELECT id FROM Player_Attributes WHERE preferred_foot = 'right' ORDER BY potential ASC LIMIT 4`
- agent: `SELECT p.player_api_id, p.preferred_foot, p.potential, p.date, ROW_NUMBER() OVER (PARTITION BY p.player_api_id ORDER BY p.date DESC) rn FROM Player_Attributes p WHERE p.player_api_id IN (41496,166963,8893,168342) ORDER BY p.player_api_id, p.date`

### financial_115

- question: For the branch which located in the south Bohemia with biggest number of inhabitants, what is the percentage of the male clients?
- expected: `SELECT CAST(SUM(T1.gender = 'M') AS REAL) * 100 / COUNT(T1.client_id) FROM client AS T1 INNER JOIN district AS T2 ON T1.district_id = T2.district_id WHERE T2.A3 = 'south Bohemia' GROUP BY T2.A4 ORDER BY T2.A4 DESC LIMIT 1`
- agent: `SELECT COUNT(*) AS total, SUM(CASE WHEN gender='M' THEN 1 ELSE 0 END) AS males FROM client WHERE district_id=14`

### financial_159

- question: List all the withdrawals in cash transactions that the client with the id 3356 makes.
- expected: `SELECT T4.trans_id FROM client AS T1 INNER JOIN disp AS T2 ON T1.client_id = T2.client_id INNER JOIN account AS T3 ON T2.account_id = T3.account_id INNER JOIN trans AS T4 ON T3.account_id = T4.account_id WHERE T1.client_id = 3356 AND T4.operation = 'VYBER'`
- agent: `SELECT d.account_id, COUNT(*) AS n, MIN(t.date) AS first_date, MAX(t.date) AS last_date, SUM(t.amount) AS total_amount, MIN(t.amount) AS min_amount, MAX(t.amount) AS max_amount FROM trans t JOIN disp d ON t.account_id = d.account_id WHERE d.client_id = 3356 AND t.operation = 'VYBER' GROUP BY d.account_id;`

### financial_168

- question: What percentage of clients who opened their accounts in the district with an average salary of over 10000 are women?
- expected: `SELECT CAST(SUM(T2.gender = 'F') AS REAL) * 100 / COUNT(T2.client_id) FROM district AS T1 INNER JOIN client AS T2 ON T1.district_id = T2.district_id WHERE T1.A11 > 10000`
- agent: `SELECT COUNT(*) AS n_clients, SUM(CASE WHEN c.gender='F' THEN 1 ELSE 0 END) AS n_female FROM district d JOIN account a ON a.district_id = d.district_id JOIN disp dp ON dp.account_id = a.account_id AND dp.type='OWNER' JOIN client c ON c.client_id = dp.client_id WHERE d.A11 > 10000;`

### financial_169

- question: What was the growth rate of the total amount of loans across all accounts for a male client between 1996 and 1997?
- expected: `SELECT CAST((SUM(CASE WHEN STRFTIME('%Y', T1.date) = '1997' THEN T1.amount ELSE 0 END) - SUM(CASE WHEN STRFTIME('%Y', T1.date) = '1996' THEN T1.amount ELSE 0 END)) AS REAL) * 100 / SUM(CASE WHEN STRFTIME('%Y', T1.date) = '1996' THEN T1.amount ELSE 0 END) FROM loan AS T1 INNER JOIN account AS T2 ON T1.account_id = T2.account_id INNER JOIN disp AS T3 ON T3.account_id = T2.account_id INNER JOIN client AS T4 ON T4.client_id = T3.client_id WHERE T4.gender = 'M' AND T3.type = 'OWNER'`
- agent: `SELECT type, COUNT(*) FROM disp GROUP BY type`

### financial_189

- question: Name the account numbers of female clients who are oldest and have lowest average salary?
- expected: `SELECT T3.account_id FROM client AS T1 INNER JOIN district AS T2 ON T1.district_id = T2.district_id INNER JOIN account AS T3 ON T2.district_id = T3.district_id INNER JOIN disp AS T4 ON T1.client_id = T4.client_id AND T4.account_id = T3.account_id WHERE T1.gender = 'F' ORDER BY T1.birth_date ASC, T2.A11 ASC LIMIT 1`
- agent: `-- Candidate B: female clients in lowest-salary district who are the oldest among them SELECT a.account_id, c.client_id, c.birth_date, d.A2, d.A11 FROM client c JOIN disp dsp ON dsp.client_id = c.client_id JOIN account a ON a.account_id = dsp.account_id JOIN district d ON d.district_id = c.district_id WHERE c.gender='F' AND d.A11 = (SELECT MIN(A11) FROM district) AND c.birth_date = (SELECT MIN(birth_date) FROM client WHERE gender='F' AND district_id = d.district_id)`

### financial_95

- question: List out the account numbers of clients who are youngest and have highest average salary?
- expected: `SELECT T1.account_id FROM account AS T1 INNER JOIN disp AS T2 ON T1.account_id = T2.account_id INNER JOIN client AS T3 ON T2.client_id = T3.client_id INNER JOIN district AS T4 on T4.district_id = T1.district_id WHERE T2.client_id = ( SELECT client_id FROM client ORDER BY birth_date DESC LIMIT 1) GROUP BY T4.A11, T1.account_id`
- agent: `SELECT type, COUNT(*) FROM disp GROUP BY type;`

### formula_1_866

- question: Who was the player that got the lap time of 0:01:27 in the race No. 161? Show his introduction website.
- expected: `SELECT DISTINCT T2.forename, T2.surname, T2.url FROM lapTimes AS T1 INNER JOIN drivers AS T2 ON T2.driverId = T1.driverId WHERE T1.raceId = 161 AND T1.time LIKE '1:27%'`
- agent: `SELECT lt.lap, lt.driverId, d.forename, d.surname, lt.time, lt.milliseconds FROM lapTimes lt JOIN drivers d ON lt.driverId = d.driverId WHERE lt.raceId = 161 ORDER BY lt.milliseconds ASC LIMIT 10`

### formula_1_869

- question: For the constructor which got the highest point in the race No. 9 , what is its introduction website?
- expected: `SELECT T2.url FROM constructorResults AS T1 INNER JOIN constructors AS T2 ON T2.constructorId = T1.constructorId WHERE T1.raceId = 9 ORDER BY T1.points DESC LIMIT 1`
- agent: `SELECT c.name, c.url, cr.points FROM constructorResults cr JOIN constructors c ON c.constructorId = cr.constructorId WHERE cr.raceId = 9 ORDER BY cr.points DESC;`

### formula_1_877

- question: For all the drivers who finished the game in race No. 872, who is the youngest?
- expected: `SELECT T1.forename, T1.surname FROM drivers AS T1 INNER JOIN results AS T2 ON T2.driverId = T1.driverId WHERE T2.raceId = 872 AND T2.time IS NOT NULL ORDER BY T1.dob DESC LIMIT 1`
- agent: `SELECT d.forename, d.surname, d.dob FROM results r JOIN drivers d ON d.driverId = r.driverId WHERE r.raceId = 872 AND r.time IS NOT NULL AND r.time != '' ORDER BY d.dob DESC LIMIT 1`

### formula_1_897

- question: Name the driver with the most winning. Mention his nationality and what is his maximum point scores.
- expected: `SELECT T1.forename, T1.surname, T1.nationality, MAX(T2.points) FROM drivers AS T1 INNER JOIN driverStandings AS T2 ON T2.driverId = T1.driverId WHERE T2.wins >= 1 GROUP BY T1.forename, T1.surname, T1.nationality ORDER BY COUNT(T2.wins) DESC LIMIT 1`
- agent: `SELECT r.points, ra.year, ra.name, r.positionOrder, r.positionText FROM results r JOIN races ra ON ra.raceId = r.raceId JOIN drivers d ON d.driverId = r.driverId WHERE d.surname = 'Schumacher' AND r.points >= 10 ORDER BY r.points DESC LIMIT 10;`

### formula_1_906

- question: Which was Lewis Hamilton first race? What was his points recorded for his first race event?
- expected: `SELECT T1.name, T2.points FROM races AS T1 INNER JOIN driverStandings AS T2 ON T2.raceId = T1.raceId INNER JOIN drivers AS T3 ON T3.driverId = T2.driverId WHERE T3.forename = 'Lewis' AND T3.surname = 'Hamilton' ORDER BY T1.year ASC LIMIT 1`
- agent: `SELECT r.raceId, r.year, r.round, r.name, COUNT(re.resultId) AS num_results FROM races r LEFT JOIN results re ON re.raceId = r.raceId WHERE r.year = 2007 GROUP BY r.raceId ORDER BY r.round;`

### formula_1_955

- question: What is the average time in seconds of champion for each year, before year 1975?
- expected: `WITH time_in_seconds AS ( SELECT T2.year, T2.raceId, T1.positionOrder, CASE WHEN T1.positionOrder = 1 THEN (CAST(SUBSTR(T1.time, 1, 1) AS REAL) * 3600) + (CAST(SUBSTR(T1.time, 3, 2) AS REAL) * 60) + CAST(SUBSTR(T1.time, 6,2) AS REAL ) + CAST(SUBSTR(T1.time, 9) AS REAL)/1000 ELSE 0 END AS time_seconds FROM results AS T1 INNER JOIN races AS T2 ON T1.raceId = T2.raceId WHERE T1.time IS NOT NULL ), champion_time AS ( SELECT year, raceId, time_seconds FROM time_in_seconds WHERE positionOrder = 1 ) SELECT year, AVG(time_seconds) FROM champion_time WHERE year < 1975 GROUP BY year HAVING AVG(time_seconds) IS NOT NULL`
- agent: `WITH final_rounds AS ( SELECT year, MAX(round) AS max_round FROM races WHERE year < 1975 GROUP BY year ), champ AS ( SELECT r.year, ds.driverId FROM driverStandings ds JOIN races r ON r.raceId = ds.raceId JOIN final_rounds fr ON fr.year = r.year AND r.round = fr.max_round WHERE ds.position = 1 AND r.year < 1975 ) SELECT c.year, d.forename, d.surname, d.driverRef, COUNT(rr.time) AS times_not_null, SUM(CASE WHEN rr.time LIKE '+%' THEN 1 ELSE 0 END) AS plus_times FROM champ c JOIN drivers d ON d.driverId = c.driverId LEFT JOIN results rr ON rr.driverId = c.driverId JOIN races r2 ON r2.raceId = rr.raceId AND r2.year = c.year GROUP BY c.year ORDER BY c.year`

### formula_1_972

- question: Which drivers who were born in 1971 and has the fastest lap time on the race? Give id and code of these drivers.
- expected: `SELECT T2.driverId, T2.code FROM results AS T1 INNER JOIN drivers AS T2 on T1.driverId = T2.driverId WHERE STRFTIME('%Y', T2.dob) = '1971' AND T1.fastestLapTime IS NOT NULL`
- agent: `SELECT DISTINCT d.driverId, d.code FROM drivers d JOIN results r ON r.driverId = d.driverId WHERE CAST(strftime('%Y', d.dob) AS INTEGER) = 1971 AND r.fastestLapTime IS NOT NULL;`

### formula_1_990

- question: What is the constructor reference name of the champion in the 2009 Singapore Grand Prix? Please give its website.
- expected: `SELECT T3.constructorRef, T3.url FROM results AS T1 INNER JOIN races AS T2 on T1.raceId = T2.raceId INNER JOIN constructors AS T3 on T1.constructorId = T3.constructorId WHERE T2.name = 'Singapore Grand Prix' AND T2.year = 2009 AND T1.time LIKE '_:%:__.___'`
- agent: `SELECT d.forename, d.surname, c.constructorRef, c.name AS constructor_name, c.url, r.position, r.positionOrder, r.time FROM results r JOIN drivers d ON r.driverId = d.driverId JOIN constructors c ON r.constructorId = c.constructorId WHERE r.raceId = 14 ORDER BY r.positionOrder LIMIT 5;`

### student_club_1376

- question: Among all the closed events, which event has the highest spend-to-budget ratio?
- expected: `SELECT T2.event_name FROM budget AS T1 INNER JOIN event AS T2 ON T1.link_to_event = T2.event_id WHERE T2.status = 'Closed' ORDER BY T1.spent / T1.amount DESC LIMIT 1`
- agent: `SELECT e.event_name, b.category, b.spent, b.amount, ROUND(b.spent / b.amount, 6) AS ratio FROM event e JOIN budget b ON e.event_id = b.link_to_event WHERE e.status = 'Closed' AND b.amount > 0 ORDER BY b.spent / b.amount DESC LIMIT 5`

### student_club_1399

- question: Did Maya Mclean attend the 'Women's Soccer' event?
- expected: `SELECT CASE WHEN T3.event_name = 'Women''s Soccer' THEN 'YES' END AS result FROM member AS T1 INNER JOIN attendance AS T2 ON T1.member_id = T2.link_to_member INNER JOIN event AS T3 ON T2.link_to_event = T3.event_id WHERE T1.first_name = 'Maya' AND T1.last_name = 'Mclean'`
- agent: `SELECT link_to_member, link_to_event FROM attendance WHERE link_to_member = 'recZ4PkGERzl9ziHO' AND link_to_event = 'rec2N69DMcrqN9PJC'`

### student_club_1422

- question: State the category of events were held at MU 215.
- expected: `SELECT DISTINCT T2.category FROM event AS T1 INNER JOIN budget AS T2 ON T1.event_id = T2.link_to_event WHERE T1.location = 'MU 215'`
- agent: `SELECT DISTINCT type FROM event WHERE location = 'MU 215'`

### superhero_728

- question: Rank superheroes from Marvel Comics by their eye color popularity, starting with the most common color.
- expected: `SELECT colour.colour AS EyeColor, COUNT(superhero.id) AS Count, RANK() OVER (ORDER BY COUNT(superhero.id) DESC) AS PopularityRank FROM superhero INNER JOIN colour ON superhero.eye_colour_id = colour.id INNER JOIN publisher ON superhero.publisher_id = publisher.id WHERE publisher.publisher_name = 'Marvel Comics' GROUP BY colour.colour`
- agent: `SELECT c.colour, COUNT(s.id) AS hero_count FROM superhero s JOIN publisher p ON s.publisher_id = p.id JOIN colour c ON s.eye_colour_id = c.id WHERE p.publisher_name = 'Marvel Comics' GROUP BY c.colour ORDER BY hero_count DESC, c.colour ASC`

### superhero_751

- question: List down at least five superpowers of male superheroes.
- expected: `SELECT T3.power_name FROM superhero AS T1 INNER JOIN hero_power AS T2 ON T1.id = T2.hero_id INNER JOIN superpower AS T3 ON T3.id = T2.power_id INNER JOIN gender AS T4 ON T4.id = T1.gender_id WHERE T4.gender = 'Male' LIMIT 5`
- agent: `SELECT DISTINCT sp.power_name FROM superhero s JOIN gender g ON s.gender_id = g.id JOIN hero_power hp ON hp.hero_id = s.id JOIN superpower sp ON hp.power_id = sp.id WHERE g.gender = 'Male' LIMIT 10;`

### thrombosis_prediction_1168

- question: The oldest SJS patient's medical laboratory work was completed on what date, and what age was the patient when they initially arrived at the hospital?
- expected: `SELECT T1.Date, STRFTIME('%Y', T2.`First Date`) - STRFTIME('%Y', T2.Birthday),T2.Birthday FROM Laboratory AS T1 INNER JOIN Patient AS T2 ON T1.ID = T2.ID WHERE T2.Diagnosis = 'SJS' AND T2.Birthday IS NOT NULL ORDER BY T2.Birthday ASC LIMIT 1`
- agent: `SELECT e.ID, e.[Examination Date], p.Birthday, p.[First Date], e.Diagnosis FROM Examination e JOIN Patient p ON e.ID = p.ID WHERE e.Diagnosis LIKE '%SJS%' ORDER BY p.Birthday ASC LIMIT 10`

### thrombosis_prediction_1201

- question: What percentage of patients who were born in 1980 and were diagnosed with RA are women?
- expected: `SELECT CAST(SUM(CASE WHEN SEX = 'F' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(ID) FROM Patient WHERE Diagnosis = 'RA' AND STRFTIME('%Y', Birthday) = '1980'`
- agent: `SELECT COUNT(*) AS total, SUM(CASE WHEN SEX = 'F' THEN 1 ELSE 0 END) AS females, ROUND(SUM(CASE WHEN SEX = 'F' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) AS pct_female FROM Patient WHERE strftime('%Y', Birthday) = '1980' AND Diagnosis = 'RA';`

### thrombosis_prediction_1252

- question: Among the patients with a normal Ig G level, how many of them have symptoms?
- expected: `SELECT COUNT(T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID INNER JOIN Examination AS T3 ON T3.ID = T2.ID WHERE T2.IGG BETWEEN 900 AND 2000 AND T3.Symptoms IS NOT NULL`
- agent: `SELECT l.ID, l.IGG, e.Symptoms FROM Laboratory l JOIN Examination e ON e.ID = l.ID WHERE l.IGG > 900 AND l.IGG < 2000 AND e.Symptoms IS NOT NULL GROUP BY l.ID;`

### thrombosis_prediction_1256

- question: How many patients with a abnormal C-reactive protein don't have their data recorded?
- expected: `SELECT COUNT(T1.ID) FROM Patient AS T1 INNER JOIN Laboratory AS T2 ON T1.ID = T2.ID WHERE (T2.CRP = '+' ) AND T1.Description IS NULL`
- agent: `SELECT COUNT(DISTINCT p.ID) AS patient_count FROM Laboratory l JOIN Patient p ON p.ID = l.ID WHERE l.CRP = '+' AND p.Description IS NULL`

### toxicology_212

- question: Which element is the least numerous in non-carcinogenic molecules?
- expected: `SELECT T.element FROM (SELECT T1.element, COUNT(DISTINCT T1.molecule_id) FROM atom AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T2.label = '-' GROUP BY T1.element ORDER BY COUNT(DISTINCT T1.molecule_id) ASC LIMIT 1) t`
- agent: `WITH counts AS ( SELECT a.element, COUNT(a.atom_id) AS cnt FROM atom a JOIN molecule m ON a.molecule_id = m.molecule_id WHERE m.label = '-' GROUP BY a.element ) SELECT element FROM counts WHERE cnt = (SELECT MIN(cnt) FROM counts)`

### toxicology_242

- question: Among all the atoms from 21 to 25, list all the molecules that are carcinogenic.
- expected: `SELECT DISTINCT T2.molecule_id FROM atom AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE SUBSTR(T1.atom_id, -2) BETWEEN '21' AND '25' AND T2.label = '+'`
- agent: `SELECT DISTINCT m.molecule_id, m.label FROM atom a JOIN molecule m ON m.molecule_id = a.molecule_id WHERE SUBSTR(a.atom_id, 7, 2) BETWEEN '21' AND '25' AND m.label = '+' ORDER BY m.molecule_id;`

### toxicology_268

- question: What are the elements for bond id TR001_10_11?
- expected: `SELECT T2.element FROM connected AS T1 INNER JOIN atom AS T2 ON T1.atom_id = T2.atom_id WHERE T1.bond_id = 'TR001_10_11'`
- agent: `SELECT a1.element AS element1, a2.element AS element2 FROM connected c JOIN atom a1 ON c.atom_id = a1.atom_id JOIN atom a2 ON c.atom_id2 = a2.atom_id WHERE c.bond_id = 'TR001_10_11'`

### toxicology_282

- question: What is the ratio of Hydrogen elements in molecule ID TR006? List the ratio with its label.
- expected: `WITH SubQuery AS (SELECT DISTINCT T1.atom_id, T1.element, T1.molecule_id, T2.label FROM atom AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id WHERE T2.molecule_id = 'TR006') SELECT CAST(COUNT(CASE WHEN element = 'h' THEN atom_id ELSE NULL END) AS REAL) / (CASE WHEN COUNT(atom_id) = 0 THEN NULL ELSE COUNT(atom_id) END) AS ratio, label FROM SubQuery GROUP BY label`
- agent: `SELECT element, COUNT(*) AS cnt FROM atom WHERE molecule_id = 'TR006' GROUP BY element;`

