



SELECT * FROM meals

COMMIT TRANSACTION;
BEGIN TRANSACTION;
UPDATE meals
SET log_date = '2026-05-19'
WHERE id = 94;


INSERT INTO foods (id, name, brand, source, external_id, kcal_per_100g, protein_per_100g, carbs_per_100g, fat_per_100g, fibre_per_100g, created_at)
VALUES
  (18, 'Lidl 7% fat turkey mince', 'Lidl', 'custom', NULL, 130.0, 19.6, 0.2, 5.5, 0.5, NOW()),
  (19, 'Lidl pasta', 'Lidl', 'custom', NULL, 359.0, 12.0, 72.0, 1.9, 3.0, NOW()),
  (20, 'Lidl extra virgin olive oil', 'Lidl', 'custom', NULL, 824.0, 0.0, 0.0, 91.6, 0.0, NOW()),
  (21, 'Large onion', '', 'custom', NULL, 40.0, 1.1, 9.2, 0.1, 2.5, NOW());