CREATE TABLE Sheet (
      idSheet INTEGER PRIMARY KEY,
      nome    VARCHAR(20) NOT NULL UNIQUE
              CHECK (nome IN ('readiness','implementation'))
  );

  CREATE TABLE Criterio (
      idCriterio   INTEGER PRIMARY KEY,
      nomeCriterio VARCHAR(80) NOT NULL,
      definizione  TEXT NOT NULL,
      sheet_id     INTEGER NOT NULL REFERENCES Sheet(idSheet)
  );

  CREATE TABLE Framework (
      idFramework   INTEGER PRIMARY KEY,
      nomeFramework VARCHAR(150) NOT NULL,
      pdf_path      VARCHAR(255),
      sheet_id      INTEGER NOT NULL REFERENCES Sheet(idSheet),
      UNIQUE (nomeFramework, sheet_id)
  );

  CREATE TABLE Voto (
      framework_id INTEGER NOT NULL REFERENCES Framework(idFramework),
      criterio_id  INTEGER NOT NULL REFERENCES Criterio(idCriterio),
      voto         REAL NOT NULL CHECK (voto IN (0, 2.5, 5, 7.5, 10)),
      PRIMARY KEY (framework_id, criterio_id)
  );

  CREATE TABLE Assessment (
      idAssessment           INTEGER PRIMARY KEY,
      sheet_id               INTEGER NOT NULL REFERENCES Sheet(idSheet),
      framework_vincitore_id INTEGER REFERENCES Framework(idFramework),
      contesto_azienda       TEXT,
      ts                     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
  );

  CREATE TABLE peso_assessment (
      assessment_id INTEGER NOT NULL REFERENCES Assessment(idAssessment),
      criterio_id   INTEGER NOT NULL REFERENCES Criterio(idCriterio),
      livello       VARCHAR(25) NOT NULL CHECK (livello IN
                    ('Fondamentale','Importante','Abbastanza importante',
                     'Poco importante','Non importante')),
      peso          REAL NOT NULL CHECK (peso IN (0, 2.5, 5, 7.5, 10)),
      motivazione   TEXT,
      trascrizione  TEXT,
      ambiguo       INTEGER NOT NULL DEFAULT 0 CHECK (ambiguo IN (0, 1)),
      PRIMARY KEY (assessment_id, criterio_id)
  );

  CREATE TABLE Diagnostica (
      idDiagnostica   INTEGER PRIMARY KEY,
      assessment_id   INTEGER NOT NULL REFERENCES Assessment(idAssessment),
      criterio_id     INTEGER REFERENCES Criterio(idCriterio),
      domanda         TEXT NOT NULL,
      risposta_utente TEXT NOT NULL,
      valutazione_llm TEXT
  );
