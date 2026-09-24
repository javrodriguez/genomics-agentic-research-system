-- PostgreSQL 16. Apply with psql -1 -v ON_ERROR_STOP=1.
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'gars_claims_owner') THEN
        CREATE ROLE gars_claims_owner NOLOGIN NOSUPERUSER NOCREATEROLE;
    END IF;
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'gars_claims_writer') THEN
        CREATE ROLE gars_claims_writer LOGIN NOSUPERUSER NOCREATEROLE;
    END IF;
    IF EXISTS (SELECT FROM pg_roles WHERE rolname = 'gars_claims_writer'
               AND (rolsuper OR rolcreaterole OR rolcreatedb OR rolreplication OR rolbypassrls OR NOT rolcanlogin))
       OR EXISTS (SELECT FROM pg_roles WHERE rolname = 'gars_claims_owner'
                  AND (rolsuper OR rolcreaterole OR rolcanlogin))
       OR has_parameter_privilege('gars_claims_writer', 'session_replication_role', 'SET')
       OR has_parameter_privilege('gars_claims_writer', 'session_replication_role', 'ALTER SYSTEM')
       OR EXISTS (SELECT FROM pg_db_role_setting s WHERE
                  s.setrole = (SELECT oid FROM pg_roles WHERE rolname = 'gars_claims_writer')
                  OR (s.setrole = 0 AND EXISTS (SELECT FROM unnest(s.setconfig) setting
                                            WHERE lower(setting) = 'session_replication_role=replica')))
       OR EXISTS (SELECT FROM pg_auth_members m JOIN pg_roles r ON r.oid = m.member
                  WHERE r.rolname = 'gars_claims_writer') THEN
        RAISE EXCEPTION 'unsafe pre-existing claims role attributes or memberships';
    END IF;
END $$;
DO $$
BEGIN
    IF to_regclass('claims.claim') IS NOT NULL THEN
        RAISE EXCEPTION 'claims schema already applied; re-apply refused';
    END IF;
END $$;

CREATE SCHEMA claims AUTHORIZATION gars_claims_owner;
SET LOCAL ROLE gars_claims_owner;

CREATE TABLE claims.run (
    id bigint PRIMARY KEY,
    question text,
    manifest_path text,
    manifest_sha256 text,
    exploratory boolean NOT NULL
);
CREATE TABLE claims.artifact (id bigint PRIMARY KEY, path text NOT NULL, sha256 text NOT NULL);
CREATE TABLE claims.source (id bigint PRIMARY KEY, reference text NOT NULL);

-- Reserved scalar-aggregate keys are forbidden at every depth, including arrays.
CREATE FUNCTION claims.no_reserved_keys(value jsonb) RETURNS boolean
LANGUAGE plpgsql IMMUTABLE STRICT SET search_path = claims, pg_temp AS $$
DECLARE k text; v jsonb;
BEGIN
    IF jsonb_typeof(value) = 'object' THEN
        FOR k, v IN SELECT * FROM jsonb_each(value) LOOP
            IF lower(k COLLATE "C") IN ('confidence', 'score') OR NOT claims.no_reserved_keys(v) THEN
                RETURN false;
            END IF;
        END LOOP;
    ELSIF jsonb_typeof(value) = 'array' THEN
        FOR v IN SELECT * FROM jsonb_array_elements(value) LOOP
            IF NOT claims.no_reserved_keys(v) THEN RETURN false; END IF;
        END LOOP;
    END IF;
    RETURN true;
END $$;
CREATE FUNCTION claims.group_valid(value jsonb, allowed text[]) RETURNS boolean
LANGUAGE sql IMMUTABLE STRICT SET search_path = claims, pg_temp AS $$
    SELECT CASE WHEN jsonb_typeof(value) = 'object' THEN value - allowed = '{}'::jsonb AND claims.no_reserved_keys(value) ELSE false END
$$;
CREATE TABLE claims.claim (
    id bigint PRIMARY KEY,
    run_id bigint NOT NULL REFERENCES claims.run(id) ON DELETE RESTRICT,
    type text NOT NULL CHECK (type IN ('OBSERVATION','INTERPRETATION','HYPOTHESIS','RECOMMENDATION')),
    text text NOT NULL,
    bio_support jsonb NOT NULL CHECK (claims.group_valid(bio_support,
        ARRAY['statistical_support','replication','orthogonal_assay','effect_size','literature'])),
    process_risk jsonb NOT NULL CHECK (claims.group_valid(process_risk,
        ARRAY['data_quality','confounding_risk','provenance_completeness','qc_disposition','limitation'])),
    reference_release text,
    workflow_version text
);
CREATE TABLE claims.evidence (
    id bigint PRIMARY KEY,
    artifact_id bigint REFERENCES claims.artifact(id) ON DELETE RESTRICT,
    source_id bigint REFERENCES claims.source(id) ON DELETE RESTRICT,
    CONSTRAINT evidence_exactly_one CHECK ((artifact_id IS NOT NULL)::integer +
                                         (source_id IS NOT NULL)::integer = 1),
    kind text NOT NULL CHECK (kind IN ('computational','statistical','literature')),
    relation text NOT NULL CHECK (relation IN ('supports','contradicts','absent'))
);
CREATE TABLE claims.claim_evidence (
    claim_id bigint NOT NULL REFERENCES claims.claim(id) ON DELETE RESTRICT,
    evidence_id bigint NOT NULL REFERENCES claims.evidence(id) ON DELETE RESTRICT,
    PRIMARY KEY (claim_id, evidence_id)
);

CREATE FUNCTION claims.require_evidence(cid bigint) RETURNS void
LANGUAGE plpgsql SECURITY DEFINER SET search_path = claims, pg_temp AS $$
BEGIN
    -- A real row version change also prevents write skew under REPEATABLE READ.
    UPDATE claims.claim SET id = id WHERE id = cid;
    IF FOUND AND NOT EXISTS (SELECT FROM claims.claim_evidence WHERE claim_id = cid) THEN
        RAISE EXCEPTION 'claim % requires at least one evidence link', cid USING ERRCODE = '23514';
    END IF;
END $$;
CREATE FUNCTION claims.evidence_cardinality() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path = claims, pg_temp AS $$
BEGIN
    IF TG_TABLE_NAME = 'claim' THEN
        PERFORM claims.require_evidence(NEW.id);
    ELSE
        PERFORM claims.require_evidence(OLD.claim_id);
        IF TG_OP = 'UPDATE' THEN
            PERFORM claims.require_evidence(NEW.claim_id);
        END IF;
    END IF;
    RETURN NULL;
END $$;
CREATE CONSTRAINT TRIGGER claim_has_evidence
AFTER INSERT ON claims.claim DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION claims.evidence_cardinality();
CREATE CONSTRAINT TRIGGER claim_keeps_evidence
AFTER DELETE OR UPDATE OF claim_id, evidence_id ON claims.claim_evidence
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION claims.evidence_cardinality();

CREATE FUNCTION claims.claim_insert(cid bigint, rid bigint, ctype text, body text,
    bio jsonb, risk jsonb, release text, workflow text, evidence_ids bigint[])
RETURNS bigint LANGUAGE plpgsql SECURITY DEFINER SET search_path = claims, pg_temp AS $$
BEGIN
    IF EXISTS (SELECT FROM claims.run WHERE id = rid AND exploratory) THEN
        RAISE EXCEPTION 'exploratory run cannot produce a claim' USING ERRCODE = '23514';
    END IF;
    IF COALESCE(cardinality(evidence_ids), 0) < 1 THEN
        RAISE EXCEPTION 'claim % requires at least one evidence link', cid USING ERRCODE = '23514';
    END IF;
    INSERT INTO claims.claim VALUES (cid, rid, ctype, body, bio, risk, release, workflow);
    INSERT INTO claims.claim_evidence SELECT cid, unnest(evidence_ids);
    RETURN cid;
END $$;

-- The writer can register only exploratory runs. Eligibility belongs to the owner.
CREATE FUNCTION claims.run_register(rid bigint, question text, manifest_path text,
    manifest_sha256 text)
RETURNS bigint LANGUAGE plpgsql SECURITY DEFINER SET search_path = claims, pg_temp AS $$
BEGIN
    INSERT INTO claims.run VALUES (rid, question, manifest_path, manifest_sha256, true);
    RETURN rid;
END $$;

CREATE FUNCTION claims.run_register_eligible(rid bigint, question text, manifest_path text,
    manifest_sha256 text)
RETURNS bigint LANGUAGE plpgsql SECURITY DEFINER SET search_path = claims, pg_temp AS $$
BEGIN
    INSERT INTO claims.run VALUES (rid, question, manifest_path, manifest_sha256, false);
    RETURN rid;
END $$;

CREATE FUNCTION claims.claims_export(rid bigint) RETURNS jsonb
LANGUAGE sql STABLE SET search_path = claims, pg_temp AS $$
    SELECT jsonb_build_object('run', to_jsonb(r), 'claims', COALESCE((
        SELECT jsonb_agg(to_jsonb(c) || jsonb_build_object('evidence', COALESCE((
            SELECT jsonb_agg(to_jsonb(e) || jsonb_build_object(
                'artifact', (SELECT to_jsonb(a) FROM claims.artifact a WHERE a.id = e.artifact_id),
                'source', (SELECT to_jsonb(s) FROM claims.source s WHERE s.id = e.source_id)) ORDER BY e.id)
            FROM claims.claim_evidence ce JOIN claims.evidence e ON e.id = ce.evidence_id
            WHERE ce.claim_id = c.id), '[]'::jsonb), 'links', (
            SELECT jsonb_agg(to_jsonb(ce) ORDER BY ce.evidence_id)
            FROM claims.claim_evidence ce WHERE ce.claim_id = c.id)) ORDER BY c.id)
        FROM claims.claim c WHERE c.run_id = r.id), '[]'::jsonb))
    FROM claims.run r WHERE r.id = rid
$$;

-- Reset administrator-supplied default ACLs before granting the writer's surface.
REVOKE ALL ON SCHEMA claims FROM PUBLIC, gars_claims_writer;
REVOKE ALL ON ALL TABLES IN SCHEMA claims FROM PUBLIC, gars_claims_writer;
REVOKE ALL ON ALL FUNCTIONS IN SCHEMA claims FROM PUBLIC, gars_claims_writer;
GRANT USAGE ON SCHEMA claims TO gars_claims_writer;
GRANT SELECT ON ALL TABLES IN SCHEMA claims TO gars_claims_writer;
GRANT INSERT ON claims.artifact, claims.source, claims.evidence TO gars_claims_writer;
-- Evidence links are immutable to the writer, including after claim_insert.
REVOKE UPDATE, DELETE ON claims.claim_evidence FROM gars_claims_writer;
GRANT EXECUTE ON FUNCTION claims.claim_insert(bigint,bigint,text,text,jsonb,jsonb,text,text,bigint[]),
    claims.claims_export(bigint), claims.run_register(bigint,text,text,text) TO gars_claims_writer;
RESET ROLE;
