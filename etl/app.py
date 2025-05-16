import os
import time
import pandas as pd
import sqlalchemy
from sqlalchemy import create_engine, text
from datetime import datetime
import logging
import hashlib
from pathlib import Path
import shutil
import tempfile

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('etl_service')

# Configuration de la base de données
DB_HOST = os.environ.get('DB_HOST', 'db')
DB_PORT = os.environ.get('DB_PORT', '5432')
DB_USER = os.environ.get('DB_USER', 'admin')
DB_PASSWORD = os.environ.get('DB_PASSWORD', 'password')
DB_NAME = os.environ.get('DB_NAME', 'entrepot')
WATCH_DIRECTORY = os.environ.get('WATCH_DIRECTORY', '/app/data')
POLLING_INTERVAL = int(os.environ.get('POLLING_INTERVAL', '1'))

# Création de la connexion à la base de données
def get_db_connection():
    connection_string = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    engine = create_engine(connection_string)
    return engine

# Vérifier si le fichier a été modifié depuis la dernière fois
def file_needs_processing(engine, filename, last_modified):
    try:
        with engine.connect() as conn:
            result = conn.execute(
                text("SELECT last_processed FROM warehouse.file_metadata WHERE filename = :filename"),
                {"filename": os.path.basename(filename)}
            ).fetchone()
            
            if result is None:
                # Fichier jamais traité auparavant
                return True
            else:
                # Vérifier si le fichier a été modifié depuis le dernier traitement
                return last_modified > result[0]
    except Exception as e:
        logger.error(f"Erreur lors de la vérification du fichier {filename}: {e}")
        return True  # En cas d'erreur, on traite le fichier par sécurité

# Mise à jour des métadonnées du fichier
def update_file_metadata(engine, filename, last_modified, status):
    try:
        with engine.connect() as conn:
            result = conn.execute(
                text("SELECT id FROM warehouse.file_metadata WHERE filename = :filename"),
                {"filename": os.path.basename(filename)}
            ).fetchone()
            
            if result is None:
                # Insertion d'une nouvelle entrée
                conn.execute(
                    text("INSERT INTO warehouse.file_metadata (filename, last_modified, last_processed, status) "
                         "VALUES (:filename, :last_modified, :last_processed, :status)"),
                    {
                        "filename": os.path.basename(filename),
                        "last_modified": last_modified,
                        "last_processed": datetime.now(),
                        "status": status
                    }
                )
            else:
                # Mise à jour de l'entrée existante
                conn.execute(
                    text("UPDATE warehouse.file_metadata SET last_modified = :last_modified, "
                         "last_processed = :last_processed, status = :status WHERE filename = :filename"),
                    {
                        "filename": os.path.basename(filename),
                        "last_modified": last_modified,
                        "last_processed": datetime.now(),
                        "status": status
                    }
                )
            conn.commit()
    except Exception as e:
        logger.error(f"Erreur lors de la mise à jour des métadonnées pour {filename}: {e}")

# Ajout d'une fonction pour gérer les fichiers verrouillés
def safe_read_excel(file_path, max_retries=3, retry_delay=2):
    """
    Tente de lire un fichier Excel avec gestion des fichiers verrouillés.
    Fait une copie temporaire si nécessaire.
    """
    retries = 0
    last_error = None
    
    while retries < max_retries:
        try:
            # Essai de lecture directe du fichier
            return pd.read_excel(file_path)
        except PermissionError as e:
            # Fichier verrouillé, on tente de faire une copie
            logger.info(f"Fichier {file_path} verrouillé, tentative de copie temporaire...")
            last_error = e
            
            try:
                # Création d'un fichier temporaire
                temp_dir = tempfile.mkdtemp()
                temp_file = os.path.join(temp_dir, os.path.basename(file_path))
                shutil.copy2(file_path, temp_file)
                
                # Lecture de la copie
                df = pd.read_excel(temp_file)
                
                # Nettoyage
                try:
                    os.remove(temp_file)
                    os.rmdir(temp_dir)
                except:
                    pass
                    
                return df
                
            except Exception as copy_error:
                logger.warning(f"Échec de la copie temporaire: {copy_error}")
                
        except Exception as e:
            # Autre erreur de lecture
            logger.warning(f"Erreur lors de la lecture du fichier {file_path}: {e}")
            last_error = e
            
        # Attendre avant de réessayer
        retries += 1
        logger.info(f"Tentative {retries}/{max_retries} pour lire {file_path}...")
        time.sleep(retry_delay)
    
    # Si on arrive ici, toutes les tentatives ont échoué
    raise last_error or Exception(f"Impossible de lire le fichier {file_path} après {max_retries} tentatives")

# Traitement du fichier clients.xlsx
def process_clients_file(engine, file_path):
    try:
        # Utilisation de la fonction sécurisée
        df = safe_read_excel(file_path)
        
        # Vérification des colonnes attendues
        required_columns = ['client_id', 'nom', 'prenom', 'email', 'telephone', 'adresse']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            logger.error(f"Colonnes manquantes dans {file_path}: {missing_columns}")
            return False
        
        # Préparation des données
        df['source_file'] = os.path.basename(file_path)
        df['imported_at'] = datetime.now()
        
        # Insertion dans la base de données avec gestion des doublons
        df.to_sql('clients', engine, schema='warehouse', if_exists='append', index=False, 
                  dtype={'client_id': sqlalchemy.types.VARCHAR(50)})
        
        logger.info(f"Fichier clients {file_path} traité avec succès")
        return True
        
    except Exception as e:
        logger.error(f"Erreur lors du traitement du fichier clients {file_path}: {e}")
        return False

# Traitement du fichier produits.xlsx
def process_produits_file(engine, file_path):
    try:
        # Utilisation de la fonction sécurisée
        df = safe_read_excel(file_path)
        
        # Vérification des colonnes attendues
        required_columns = ['produit_id', 'nom', 'categorie', 'prix_unitaire', 'stock_disponible', 'description']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            logger.error(f"Colonnes manquantes dans {file_path}: {missing_columns}")
            return False
        
        # Préparation des données
        df['source_file'] = os.path.basename(file_path)
        df['imported_at'] = datetime.now()
        
        # Insertion dans la base de données avec gestion des doublons
        df.to_sql('produits', engine, schema='warehouse', if_exists='append', index=False,
                  dtype={'produit_id': sqlalchemy.types.VARCHAR(50)})
        
        logger.info(f"Fichier produits {file_path} traité avec succès")
        return True
        
    except Exception as e:
        logger.error(f"Erreur lors du traitement du fichier produits {file_path}: {e}")
        return False

# Traitement du fichier ventes.xlsx
def process_ventes_file(engine, file_path):
    try:
        # Utilisation de la fonction sécurisée
        df = safe_read_excel(file_path)
        
        # Vérification des colonnes attendues
        required_columns = ['vente_id', 'client_id', 'produit_id', 'quantite', 'prix_total', 'date_vente']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            logger.error(f"Colonnes manquantes dans {file_path}: {missing_columns}")
            return False
        
        # Préparation des données
        df['source_file'] = os.path.basename(file_path)
        df['imported_at'] = datetime.now()
        
        # Insertion dans la base de données avec gestion des doublons
        df.to_sql('ventes', engine, schema='warehouse', if_exists='append', index=False,
                  dtype={
                      'vente_id': sqlalchemy.types.VARCHAR(50),
                      'client_id': sqlalchemy.types.VARCHAR(50),
                      'produit_id': sqlalchemy.types.VARCHAR(50)
                  })
        
        logger.info(f"Fichier ventes {file_path} traité avec succès")
        return True
        
    except Exception as e:
        logger.error(f"Erreur lors du traitement du fichier ventes {file_path}: {e}")
        return False

# Déterminer le type de fichier et appeler le processeur approprié
def process_file(engine, file_path):
    filename = os.path.basename(file_path).lower()
    
    if "client" in filename:
        return process_clients_file(engine, file_path)
    elif "produit" in filename:
        return process_produits_file(engine, file_path)
    elif "vente" in filename:
        return process_ventes_file(engine, file_path)
    else:
        logger.warning(f"Type de fichier non reconnu: {filename}")
        return False

# Fonction principale
def main():
    logger.info("Démarrage du service ETL")
    engine = get_db_connection()
    
    while True:
        try:
            # Vérification de la connexion à la base de données
            engine.connect().close()
            
            # Parcourir les fichiers dans le répertoire surveillé
            logger.info("Boucle principale : vérification des fichiers en cours...")

            for file in Path(WATCH_DIRECTORY).glob("*.xlsx"):
                if file.name.startswith("~$"):
                    continue  # Ignorer les fichiers temporaires Excel
                logger.info(f"Fichier trouvé : {file}")
                file_path = str(file)
                last_modified = datetime.fromtimestamp(os.path.getmtime(file_path))
                
                # Vérifier si le fichier doit être traité
                if file_needs_processing(engine, file_path, last_modified):
                    logger.info(f"Traitement du fichier: {file_path}")
                    success = process_file(engine, file_path)
                    
                    # Mise à jour des métadonnées
                    status = "success" if success else "error"
                    update_file_metadata(engine, file_path, last_modified, status)
                    
            # Attendre avant la prochaine vérification
            time.sleep(POLLING_INTERVAL)
            
        except Exception as e:
            logger.error(f"Erreur dans la boucle principale: {e}")
            time.sleep(10)  # Attendre un peu avant de réessayer en cas d'erreur 
            
            # Recréer la connexion en cas de problème
            try:
                engine = get_db_connection()
            except:
                logger.error("Impossible de se reconnecter à la base de données")

if __name__ == "__main__":
    main()