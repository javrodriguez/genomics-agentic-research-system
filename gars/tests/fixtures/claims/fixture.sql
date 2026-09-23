-- Synthetic fixture only; no authoritative database writes.
INSERT INTO claims.run VALUES (1, 'How do the synthetic groups differ?',
    'gars/tests/fixtures/claims/manifest.json', '25b6987c30b06e80f47d04caf0c860359d1c687ad91d4e7ab2efd635c1871008', false);
INSERT INTO claims.artifact VALUES (1, 'fixtures/counts.tsv', 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa');
INSERT INTO claims.source VALUES (1, 'Synthetic literature reference');
INSERT INTO claims.evidence VALUES
    (1, 1, NULL, 'computational', 'supports'),
    (2, NULL, 1, 'literature', 'contradicts'),
    (3, 1, NULL, 'statistical', 'absent');
SELECT claims.claim_insert(1,1,'OBSERVATION','The synthetic table contains four rows.',
    '{"statistical_support":"synthetic only"}', '{}', 'release-A','workflow-v1',ARRAY[1,3]::bigint[]);
SELECT claims.claim_insert(2,1,'INTERPRETATION','A group difference is compatible with this fixture.',
    '{}', '{"qc_disposition":"DEGRADE","limitation":"Synthetic cohort only"}',
    'release-A','workflow-v1',ARRAY[1]::bigint[]);
SELECT claims.claim_insert(3,1,'HYPOTHESIS','A regulatory association may be possible.',
    '{"literature":"contradictory synthetic source"}', '{}',
    'release-B','workflow-v1',ARRAY[2]::bigint[]);
SELECT claims.claim_insert(4,1,'RECOMMENDATION','Consider an independent assay.',
    '{}', '{"qc_disposition":"WARN"}', 'release-B','workflow-v1',ARRAY[3]::bigint[]);
