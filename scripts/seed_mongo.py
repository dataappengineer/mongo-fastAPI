"""
Script to seed MongoDB with test data for Regione Puglia.
Run this after starting the MongoDB container to populate test collections.
"""
import os
import sys
from datetime import datetime
from pymongo import MongoClient
from pymongo.errors import PyMongoError

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def seed_database():
    """Seed the database with test collections for Regione Puglia."""
    
    # Connection settings
    mongo_host = os.getenv("MONGO_HOST", "localhost")
    mongo_port = int(os.getenv("MONGO_PORT", "27017"))
    mongo_db = os.getenv("MONGO_DB", "testdb")
    
    print(f"🔌 Connecting to MongoDB at {mongo_host}:{mongo_port}...")
    
    try:
        # Connect to MongoDB
        client = MongoClient(f"mongodb://{mongo_host}:{mongo_port}/")
        db = client[mongo_db]
        
        print(f"✅ Connected to database: {mongo_db}")
        
        # Drop existing collections if they exist
        print("🗑️  Dropping existing test collections...")
        db.cittadini.drop()
        db.servizi_pubblici.drop()
        db.pratiche_amministrative.drop()
        db.vista_cittadini_per_comune.drop()
        db.vista_servizi_per_categoria.drop()
        db.metriche_accessi.drop()
        
        # Collection 1: Cittadini (Citizens registered in Regione Puglia)
        print("📝 Creating 'cittadini' collection...")
        cittadini = [
            {
                "codice_fiscale": "RSSMRA75H15A662Z",
                "nome": "Mario",
                "cognome": "Rossi",
                "data_nascita": datetime(1975, 6, 15),
                "luogo_nascita": "Bari",
                "comune_residenza": "Bari",
                "provincia": "BA",
                "indirizzo": "Via Sparano 45",
                "cap": "70121",
                "email": "mario.rossi@pec.regione.puglia.it",
                "telefono": "+39 080 1234567",
                "stato_civile": "coniugato",
                "professione": "impiegato pubblico",
                "data_registrazione": datetime(2020, 3, 15)
            },
            {
                "codice_fiscale": "BNCLRA85M47F152H",
                "nome": "Laura",
                "cognome": "Bianchi",
                "data_nascita": datetime(1985, 8, 7),
                "luogo_nascita": "Lecce",
                "comune_residenza": "Lecce",
                "provincia": "LE",
                "indirizzo": "Piazza Sant'Oronzo 12",
                "cap": "73100",
                "email": "laura.bianchi@pec.regione.puglia.it",
                "telefono": "+39 0832 567890",
                "stato_civile": "nubile",
                "professione": "insegnante",
                "data_registrazione": datetime(2019, 9, 22)
            },
            {
                "codice_fiscale": "VRDGPP70D12E716M",
                "nome": "Giuseppe",
                "cognome": "Verdi",
                "data_nascita": datetime(1970, 4, 12),
                "luogo_nascita": "Taranto",
                "comune_residenza": "Taranto",
                "provincia": "TA",
                "indirizzo": "Corso Umberto I 78",
                "cap": "74123",
                "email": "giuseppe.verdi@pec.regione.puglia.it",
                "telefono": "+39 099 7654321",
                "stato_civile": "divorziato",
                "professione": "commerciante",
                "data_registrazione": datetime(2021, 1, 10)
            },
            {
                "codice_fiscale": "FRRNNA82B55L049D",
                "nome": "Anna",
                "cognome": "Ferraro",
                "data_nascita": datetime(1982, 2, 15),
                "luogo_nascita": "Foggia",
                "comune_residenza": "Foggia",
                "provincia": "FG",
                "indirizzo": "Viale XXIV Maggio 33",
                "cap": "71121",
                "email": "anna.ferraro@pec.regione.puglia.it",
                "telefono": "+39 0881 223344",
                "stato_civile": "coniugata",
                "professione": "medico",
                "data_registrazione": datetime(2020, 7, 5)
            },
            {
                "codice_fiscale": "CLMPLA90R18A285Y",
                "nome": "Paolo",
                "cognome": "Colombo",
                "data_nascita": datetime(1990, 10, 18),
                "luogo_nascita": "Brindisi",
                "comune_residenza": "Brindisi",
                "provincia": "BR",
                "indirizzo": "Via Appia 156",
                "cap": "72100",
                "email": "paolo.colombo@pec.regione.puglia.it",
                "telefono": None,  # Missing phone to test null handling
                "stato_civile": "celibe",
                "professione": "ingegnere",
                "data_registrazione": datetime(2022, 3, 20)
            },
            {
                "codice_fiscale": "GRCMRT88L52F842W",
                "nome": "Marta",
                "cognome": "Greco",
                "data_nascita": datetime(1988, 7, 12),
                "luogo_nascita": "Andria",
                "comune_residenza": "Barletta",
                "provincia": "BT",
                "indirizzo": "Corso Garibaldi 89",
                "cap": "76121",
                "email": "marta.greco@pec.regione.puglia.it",
                "telefono": "+39 0883 998877",
                "stato_civile": "coniugata",
                "professione": "avvocato",
                "data_registrazione": datetime(2021, 11, 8)
            }
        ]
        db.cittadini.insert_many(cittadini)
        print(f"   ✅ Inserted {len(cittadini)} cittadini")
        
        # Collection 2: Servizi Pubblici (Public Services offered by Regione Puglia)
        print("📝 Creating 'servizi_pubblici' collection...")
        servizi_pubblici = [
            {
                "codice_servizio": "SP-001",
                "nome_servizio": "Rilascio Carta d'Identità Elettronica",
                "categoria": "Anagrafe e Stato Civile",
                "descrizione": "Servizio per il rilascio della carta d'identità elettronica presso gli uffici comunali",
                "assessorato": "Affari Generali",
                "costo": 22.21,
                "tempo_medio_erogazione_giorni": 5,
                "documenti_richiesti": ["documento identità scaduto", "codice fiscale", "foto tessera"],
                "modalita_erogazione": ["sportello fisico", "prenotazione online"],
                "contatti": {
                    "telefono": "080 5406111",
                    "email": "anagrafe@regione.puglia.it",
                    "pec": "anagrafe.puglia@pec.regione.puglia.it"
                },
                "attivo": True
            },
            {
                "codice_servizio": "SP-002",
                "nome_servizio": "Certificato di Residenza",
                "categoria": "Anagrafe e Stato Civile",
                "descrizione": "Rilascio certificato di residenza in formato digitale o cartaceo",
                "assessorato": "Affari Generali",
                "costo": 0.00,
                "tempo_medio_erogazione_giorni": 1,
                "documenti_richiesti": ["documento identità valido"],
                "modalita_erogazione": ["online", "sportello fisico"],
                "contatti": {
                    "telefono": "080 5406111",
                    "email": "certificati@regione.puglia.it",
                    "pec": "certificati.puglia@pec.regione.puglia.it"
                },
                "attivo": True
            },
            {
                "codice_servizio": "SP-003",
                "nome_servizio": "Autorizzazione Paesaggistica",
                "categoria": "Urbanistica e Territorio",
                "descrizione": "Autorizzazione per interventi edilizi in zone sottoposte a vincolo paesaggistico",
                "assessorato": "Ambiente e Territorio",
                "costo": 150.00,
                "tempo_medio_erogazione_giorni": 60,
                "documenti_richiesti": ["progetto tecnico", "relazione paesaggistica", "documentazione fotografica"],
                "modalita_erogazione": ["sportello fisico", "portale SUAP"],
                "contatti": {
                    "telefono": "080 5403200",
                    "email": "paesaggio@regione.puglia.it",
                    "pec": "ambiente.puglia@pec.regione.puglia.it"
                },
                "attivo": True
            },
            {
                "codice_servizio": "SP-004",
                "nome_servizio": "Tessera Sanitaria",
                "categoria": "Sanità",
                "descrizione": "Attivazione e rinnovo tessera sanitaria regionale",
                "assessorato": "Politiche della Salute",
                "costo": 0.00,
                "tempo_medio_erogazione_giorni": 15,
                "documenti_richiesti": ["codice fiscale", "documento identità", "certificato di residenza"],
                "modalita_erogazione": ["ASL territoriale", "online"],
                "contatti": {
                    "telefono": "080 5404000",
                    "email": "sanita@regione.puglia.it",
                    "pec": "sanita.puglia@pec.regione.puglia.it"
                },
                "attivo": True
            },
            {
                "codice_servizio": "SP-005",
                "nome_servizio": "Borse di Studio Regionali",
                "categoria": "Istruzione e Formazione",
                "descrizione": "Erogazione borse di studio per studenti meritevoli residenti in Puglia",
                "assessorato": "Diritto allo Studio",
                "costo": 0.00,
                "tempo_medio_erogazione_giorni": 90,
                "documenti_richiesti": ["ISEE", "certificato di iscrizione", "autocertificazione merito"],
                "modalita_erogazione": ["portale ADISU"],
                "contatti": None,  # Null contact to test null handling
                "attivo": False
            },
            {
                "codice_servizio": "SP-006",
                "nome_servizio": "Permesso di Costruire",
                "categoria": "Urbanistica e Territorio",
                "descrizione": "Autorizzazione per nuove costruzioni e ristrutturazioni importanti",
                "assessorato": "Ambiente e Territorio",
                "costo": 500.00,
                "tempo_medio_erogazione_giorni": 120,
                "documenti_richiesti": ["progetto architettonico", "calcoli strutturali", "relazione tecnica", "titolo proprietà"],
                "modalita_erogazione": ["sportello SUE comunale", "portale SUAP"],
                "contatti": {
                    "telefono": "080 5403250",
                    "email": "edilizia@regione.puglia.it",
                    "pec": "edilizia.puglia@pec.regione.puglia.it"
                },
                "attivo": True
            }
        ]
        db.servizi_pubblici.insert_many(servizi_pubblici)
        print(f"   ✅ Inserted {len(servizi_pubblici)} servizi pubblici")
        
        # Collection 3: Pratiche Amministrative (Administrative Procedures)
        print("📝 Creating 'pratiche_amministrative' collection...")
        pratiche_amministrative = [
            {
                "numero_pratica": "PR-2024-00123",
                "codice_fiscale_richiedente": "RSSMRA75H15A662Z",
                "codice_servizio": "SP-001",
                "nome_servizio": "Rilascio Carta d'Identità Elettronica",
                "data_presentazione": datetime(2024, 1, 15, 9, 30),
                "data_completamento": datetime(2024, 1, 20, 15, 45),
                "stato": "completata",
                "ufficio_competente": "Ufficio Anagrafe - Bari",
                "operatore_assegnato": "Dott.ssa Maria Lorusso",
                "importo_pagato": 22.21,
                "metodo_pagamento": "PagoPA",
                "note": "Pratica evasa regolarmente. Documento ritirato presso lo sportello.",
                "allegati": ["ricevuta_pagamento.pdf", "documento_identita_scaduto.pdf"]
            },
            {
                "numero_pratica": "PR-2024-00234",
                "codice_fiscale_richiedente": "BNCLRA85M47F152H",
                "codice_servizio": "SP-002",
                "nome_servizio": "Certificato di Residenza",
                "data_presentazione": datetime(2024, 2, 10, 14, 20),
                "data_completamento": datetime(2024, 2, 11, 10, 15),
                "stato": "completata",
                "ufficio_competente": "Ufficio Anagrafe - Lecce",
                "operatore_assegnato": "Sig. Francesco De Luca",
                "importo_pagato": 0.00,
                "metodo_pagamento": "gratuito",
                "note": "Certificato rilasciato in formato digitale",
                "allegati": ["certificato_residenza.pdf"]
            },
            {
                "numero_pratica": "PR-2024-00345",
                "codice_fiscale_richiedente": "FRRNNA82B55L049D",
                "codice_servizio": "SP-003",
                "nome_servizio": "Autorizzazione Paesaggistica",
                "data_presentazione": datetime(2024, 3, 5, 11, 0),
                "data_completamento": None,
                "stato": "in lavorazione",
                "ufficio_competente": "Assessorato Ambiente - Regione Puglia",
                "operatore_assegnato": "Arch. Giovanni Palmieri",
                "importo_pagato": 150.00,
                "metodo_pagamento": "bonifico bancario",
                "note": "Pratica in fase di valutazione tecnica. In attesa parere soprintendenza.",
                "allegati": ["progetto_tecnico.pdf", "relazione_paesaggistica.pdf", "foto_stato_attuale.zip"]
            },
            {
                "numero_pratica": "PR-2024-00456",
                "codice_fiscale_richiedente": "VRDGPP70D12E716M",
                "codice_servizio": "SP-004",
                "nome_servizio": "Tessera Sanitaria",
                "data_presentazione": datetime(2024, 2, 20, 8, 45),
                "data_completamento": datetime(2024, 3, 8, 12, 30),
                "stato": "completata",
                "ufficio_competente": "ASL Taranto",
                "operatore_assegnato": "Dott. Michele Tarantino",
                "importo_pagato": 0.00,
                "metodo_pagamento": "gratuito",
                "note": "Tessera sanitaria spedita al domicilio del richiedente",
                "allegati": ["richiesta_tessera.pdf"]
            },
            {
                "numero_pratica": "PR-2024-00567",
                "codice_fiscale_richiedente": "GRCMRT88L52F842W",
                "codice_servizio": "SP-006",
                "nome_servizio": "Permesso di Costruire",
                "data_presentazione": datetime(2023, 11, 15, 10, 0),
                "data_completamento": None,
                "stato": "sospesa",
                "ufficio_competente": "Ufficio Tecnico Comunale - Barletta",
                "operatore_assegnato": "Ing. Sergio Manfredi",
                "importo_pagato": 500.00,
                "metodo_pagamento": "PagoPA",
                "note": "Pratica sospesa. Richiesta integrazione documentale: mancano calcoli strutturali aggiornati.",
                "allegati": ["progetto_architettonico.pdf", "planimetria.dwg"]
            },
            {
                "numero_pratica": "PR-2024-00678",
                "codice_fiscale_richiedente": "CLMPLA90R18A285Y",
                "codice_servizio": "SP-002",
                "nome_servizio": "Certificato di Residenza",
                "data_presentazione": datetime(2024, 3, 12, 16, 30),
                "data_completamento": None,
                "stato": "presentata",
                "ufficio_competente": "Ufficio Anagrafe - Brindisi",
                "operatore_assegnato": None,  # Not yet assigned
                "importo_pagato": 0.00,
                "metodo_pagamento": "gratuito",
                "note": None,
                "allegati": []
            }
        ]
        db.pratiche_amministrative.insert_many(pratiche_amministrative)
        print(f"   ✅ Inserted {len(pratiche_amministrative)} pratiche amministrative")
        
        # Create indexes for better performance
        print("🔍 Creating indexes...")
        db.cittadini.create_index("codice_fiscale", unique=True)
        db.cittadini.create_index("email", unique=True)
        db.cittadini.create_index("comune_residenza")
        db.servizi_pubblici.create_index("codice_servizio", unique=True)
        db.servizi_pubblici.create_index("categoria")
        db.pratiche_amministrative.create_index("numero_pratica", unique=True)
        db.pratiche_amministrative.create_index("codice_fiscale_richiedente")
        db.pratiche_amministrative.create_index("stato")
        print("   ✅ Indexes created")
        
        # Create views for testing
        print("📝 Creating views...")
        
        # View 1: Active citizens by city
        try:
            db.command({
                "create": "vista_cittadini_per_comune",
                "viewOn": "cittadini",
                "pipeline": [
                    {
                        "$group": {
                            "_id": "$comune_residenza",
                            "totale_cittadini": {"$sum": 1},
                            "professioni": {"$push": "$professione"}
                        }
                    },
                    {"$sort": {"totale_cittadini": -1}}
                ]
            })
            print("   ✅ Created view 'vista_cittadini_per_comune'")
        except Exception as e:
            if "already exists" not in str(e):
                print(f"   ⚠️  Warning creating view: {e}")
        
        # View 2: Services by category
        try:
            db.command({
                "create": "vista_servizi_per_categoria",
                "viewOn": "servizi_pubblici",
                "pipeline": [
                    {
                        "$group": {
                            "_id": "$categoria",
                            "numero_servizi": {"$sum": 1},
                            "costo_medio": {"$avg": "$costo"},
                            "tempo_medio_giorni": {"$avg": "$tempo_medio_erogazione_giorni"}
                        }
                    }
                ]
            })
            print("   ✅ Created view 'vista_servizi_per_categoria'")
        except Exception as e:
            if "already exists" not in str(e):
                print(f"   ⚠️  Warning creating view: {e}")
        
        # Create timeseries collection for monitoring
        print("📝 Creating timeseries collection...")
        try:
            db.create_collection(
                "metriche_accessi",
                timeseries={
                    "timeField": "timestamp",
                    "metaField": "servizio",
                    "granularity": "hours"
                }
            )
            
            # Insert sample timeseries data
            metriche_data = [
                {
                    "timestamp": datetime(2024, 12, 19, 10, 0),
                    "servizio": "SP-001",
                    "accessi": 15,
                    "tempo_medio_risposta_ms": 250
                },
                {
                    "timestamp": datetime(2024, 12, 19, 11, 0),
                    "servizio": "SP-001",
                    "accessi": 23,
                    "tempo_medio_risposta_ms": 280
                },
                {
                    "timestamp": datetime(2024, 12, 19, 12, 0),
                    "servizio": "SP-002",
                    "accessi": 45,
                    "tempo_medio_risposta_ms": 120
                }
            ]
            db.metriche_accessi.insert_many(metriche_data)
            print("   ✅ Created timeseries collection 'metriche_accessi' with sample data")
        except Exception as e:
            if "already exists" not in str(e):
                print(f"   ⚠️  Warning creating timeseries: {e}")
        
        # Summary
        print("\n" + "="*50)
        print("🎉 Database seeding completato con successo!")
        print("="*50)
        print(f"📊 Collections create:")
        print(f"   - cittadini: {db.cittadini.count_documents({})} documenti")
        print(f"   - servizi_pubblici: {db.servizi_pubblici.count_documents({})} documenti")
        print(f"   - pratiche_amministrative: {db.pratiche_amministrative.count_documents({})} documenti")
        print(f"   - metriche_accessi (timeseries): {db.metriche_accessi.count_documents({})} documenti")
        print(f"📊 Views create:")
        print(f"   - vista_cittadini_per_comune")
        print(f"   - vista_servizi_per_categoria")
        print("="*50)
        
        # Close connection
        client.close()
        
    except PyMongoError as e:
        print(f"❌ Error seeding database: {e}")
        sys.exit(1)


if __name__ == "__main__":
    seed_database()
