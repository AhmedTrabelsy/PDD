-- ============================================================
-- PPD — Tableau de Bord de Performance Personnelle
-- Schéma SQL complet pour Supabase (PostgreSQL)
-- Exécuter ce fichier dans l'éditeur SQL de Supabase
-- ============================================================

-- Fonction partagée pour updated_at (créée en premier)
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;


-- ── TABLE 1 : journal_presence ────────────────────────────
CREATE TABLE IF NOT EXISTS journal_presence (
    log_id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    type_evenement TEXT NOT NULL CHECK (type_evenement IN ('ENTREE', 'SORTIE')),
    horodatage     TIMESTAMPTZ NOT NULL DEFAULT now(),
    date_jour      DATE NOT NULL DEFAULT CURRENT_DATE,
    zone_usine     TEXT,
    note           TEXT,
    created_at     TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_presence_date ON journal_presence(date_jour);


-- ── TABLE 2 : projets ─────────────────────────────────────
-- Projets auxquels des tâches peuvent être associées (optionnel).
CREATE TABLE IF NOT EXISTS projets (
    projet_id   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nom         TEXT NOT NULL,
    description TEXT,
    couleur     TEXT DEFAULT '#3b82f6',
    statut      TEXT NOT NULL DEFAULT 'EN_COURS' CHECK (statut IN (
                    'EN_COURS', 'EN_PAUSE', 'TERMINE', 'ABANDONNE'
                )),
    date_debut  DATE DEFAULT CURRENT_DATE,
    date_fin    DATE,
    created_at  TIMESTAMPTZ DEFAULT now(),
    updated_at  TIMESTAMPTZ DEFAULT now()
);

DROP TRIGGER IF EXISTS trig_projets_updated_at ON projets;
CREATE TRIGGER trig_projets_updated_at
    BEFORE UPDATE ON projets
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();


-- ── TABLE 3 : journal_taches ──────────────────────────────
CREATE TABLE IF NOT EXISTS journal_taches (
    tache_id       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cree_le        TIMESTAMPTZ NOT NULL DEFAULT now(),
    cloture_le     TIMESTAMPTZ,
    titre          TEXT NOT NULL,
    description    TEXT,
    categorie      TEXT NOT NULL CHECK (categorie IN (
                       'Développement', 'Maintenance', 'Déploiement Terrain',
                       'Analyse de Données', 'Documentation', 'Réunion'
                   )),
    zone_usine     TEXT NOT NULL,
    projet_id      UUID REFERENCES projets(projet_id) ON DELETE SET NULL,
    statut         TEXT NOT NULL DEFAULT 'EN_COURS' CHECK (statut IN (
                       'A_FAIRE', 'EN_COURS', 'BLOQUE', 'TERMINE'
                   )),
    complexite     INTEGER NOT NULL DEFAULT 3 CHECK (complexite BETWEEN 1 AND 5),
    livrable       TEXT,
    raison_blocage TEXT,
    created_at     TIMESTAMPTZ DEFAULT now(),
    updated_at     TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_taches_statut   ON journal_taches(statut);
CREATE INDEX IF NOT EXISTS idx_taches_cree_le  ON journal_taches(cree_le);
CREATE INDEX IF NOT EXISTS idx_taches_projet   ON journal_taches(projet_id);

DROP TRIGGER IF EXISTS trig_taches_updated_at ON journal_taches;
CREATE TRIGGER trig_taches_updated_at
    BEFORE UPDATE ON journal_taches
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();


-- ── TABLE 4 : notes_journalieres ─────────────────────────
CREATE TABLE IF NOT EXISTS notes_journalieres (
    date_jour        DATE PRIMARY KEY,
    resume           TEXT,
    points_bloquants TEXT,
    plan_lendemain   TEXT,
    score_engagement INTEGER CHECK (score_engagement BETWEEN 1 AND 5),
    created_at       TIMESTAMPTZ DEFAULT now(),
    updated_at       TIMESTAMPTZ DEFAULT now()
);

DROP TRIGGER IF EXISTS trig_notes_updated_at ON notes_journalieres;
CREATE TRIGGER trig_notes_updated_at
    BEFORE UPDATE ON notes_journalieres
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();


-- ── TABLE 5 : objectifs ───────────────────────────────────
CREATE TABLE IF NOT EXISTS objectifs (
    obj_id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    titre         TEXT NOT NULL,
    description   TEXT,
    date_echeance DATE NOT NULL,
    progression   INTEGER NOT NULL DEFAULT 0 CHECK (progression BETWEEN 0 AND 100),
    statut        TEXT NOT NULL DEFAULT 'EN_COURS' CHECK (statut IN (
                      'EN_COURS', 'EN_RISQUE', 'ATTEINT', 'ABANDONNE'
                  )),
    created_at    TIMESTAMPTZ DEFAULT now(),
    updated_at    TIMESTAMPTZ DEFAULT now()
);

DROP TRIGGER IF EXISTS trig_obj_updated_at ON objectifs;
CREATE TRIGGER trig_obj_updated_at
    BEFORE UPDATE ON objectifs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();


-- ── DONNÉES DE DÉMONSTRATION ──────────────────────────────
INSERT INTO projets (nom, description, couleur, statut) VALUES
    ('Monitoring IoT', 'Déploiement des capteurs et dashboard temps réel', '#3b82f6', 'EN_COURS'),
    ('Optimisation Ligne A', 'Réduire les arrêts non planifiés de 20%', '#10b981', 'EN_COURS'),
    ('Migration Serveurs', 'Migration infrastructure vers cloud hybride', '#8b5cf6', 'EN_PAUSE');

INSERT INTO journal_presence (type_evenement, horodatage, date_jour, zone_usine) VALUES
    ('ENTREE', now() - INTERVAL '2 days' + INTERVAL '7 hours 50 minutes',  CURRENT_DATE - 2, 'Ligne A'),
    ('SORTIE', now() - INTERVAL '2 days' + INTERVAL '17 hours',            CURRENT_DATE - 2, 'Ligne A'),
    ('ENTREE', now() - INTERVAL '1 day'  + INTERVAL '7 hours 55 minutes',  CURRENT_DATE - 1, 'Salle Serveurs'),
    ('SORTIE', now() - INTERVAL '1 day'  + INTERVAL '17 hours 10 minutes', CURRENT_DATE - 1, 'Salle Serveurs'),
    ('ENTREE', now() - INTERVAL '2 hours', CURRENT_DATE, 'Bureau d''Études');

INSERT INTO journal_taches (titre, categorie, zone_usine, statut, complexite, livrable, cloture_le)
VALUES
    ('Configuration du serveur de monitoring', 'Maintenance', 'Salle Serveurs', 'TERMINE', 4,
     'Serveur Prometheus configuré', now() - INTERVAL '2 days' + INTERVAL '12 hours'),
    ('Script nettoyage données capteurs', 'Développement', 'Ligne A', 'TERMINE', 3,
     'Script Python déployé', now() - INTERVAL '1 day' + INTERVAL '14 hours'),
    ('Calibration capteurs température', 'Déploiement Terrain', 'Ligne B', 'TERMINE', 2,
     '6 capteurs recalibrés', now() - INTERVAL '1 day' + INTERVAL '16 hours'),
    ('Analyse des temps de cycle Ligne A', 'Analyse de Données', 'Ligne A', 'EN_COURS', 5, NULL, NULL),
    ('Mise à jour documentation API', 'Documentation', 'Bureau d''Études', 'A_FAIRE', 1, NULL, NULL);

INSERT INTO objectifs (titre, description, date_echeance, progression, statut) VALUES
    ('Optimisation du débit Ligne A', 'Réduire les temps d''arrêt de 20% en Q3',
     CURRENT_DATE + 45, 40, 'EN_COURS'),
    ('Déploiement plateforme monitoring IoT', 'Couvrir toutes les zones avec des capteurs',
     CURRENT_DATE + 90, 65, 'EN_COURS'),
    ('Documentation technique complète', 'Documenter tous les systèmes en production',
     CURRENT_DATE + 30, 20, 'EN_RISQUE');