# 🛠️ Projet ETL - Intégration de Données Excel vers PostgreSQL

Ce projet implémente un pipeline **ETL** (Extract - Transform - Load) permettant d'alimenter automatiquement un entrepôt de données PostgreSQL à partir de fichiers **Excel (.xlsx)** déposés dans un répertoire surveillé. Il est conçu pour fonctionner en continu grâce à un service Python Dockerisé.

---

## 📁 Structure du Projet
Presentation1
    ├──etl
     ├── app.py   
     ├── requirements.txt
     ├──Dockerfile
    ├──init-db
     ├──init.sql # Script SQL de création des tables et du schéma
    ├── docker-compose.yml # Déploiement multi-conteneurs (PostgreSQL + ETL)
    ├── data/ # Répertoire surveillé (à créer localement)
    ├── excel
     └── clients.xlsx # Exemple de fichier source

---

## 🚀 Fonctionnalités

- 📂 Surveillance continue d’un répertoire local pour détecter les fichiers `.xlsx`
- ✅ Traitement automatique des fichiers **clients**, **produits**, et **ventes**
- 🔎 Validation des colonnes attendues
- 🧠 Évitement des doublons grâce à un système de métadonnées
- 🗃️ Insertion des données dans un schéma `warehouse` PostgreSQL
- 🧾 Historique de traitement enregistré dans une table `file_metadata`
- 📊 Prêt pour la visualisation dans Metabase

---

## 📦 Technologies utilisées

- Python 3
- Pandas
- SQLAlchemy
- PostgreSQL
- Docker / Docker Compose
- Metabase (optionnel)

---

## ⚙️ Prérequis

- Docker et Docker Compose installés
- Python (optionnel si on n’utilise que Docker)
- Fichiers Excel (`.xlsx`) à importer avec colonnes correctes

---

## 🐳 Lancement avec Docker

1. **Cloner le dépôt**
```bash
git clone https://github.com/Gbessaya-joseph/Datawarehouse1.git
cd Presentation1
```
Créer un répertoire data/ (s’il n’existe pas)
```bash
mkdir data
```
Placer vos fichiers .xlsx dans data/

Lancer les services
```bash
docker compose up --build
```

🗂️ Schéma de base de données

Le script init.sql crée les éléments suivants dans la base entrepot :

    warehouse.clients

    warehouse.produits

    warehouse.ventes

    warehouse.file_metadata

🔐 Contraintes :

    Clés étrangères entre ventes.client_id → clients.client_id

    produit_id référencé également

    Indices pour performance (client_id, produit_id, date_vente)

📝 Format attendu des fichiers .xlsx

    clients.xlsx
    client_id	nom	prenom	email	telephone	adresse
---
    produits.xlsx
    produit_id	nom	categorie	prix_unitaire	stock_disponible	description
---
    ventes.xlsx
    vente_id	client_id	produit_id	quantite	prix_total	date_vente

🕒 Le traitement inclut automatiquement les colonnes imported_at et source_file.

🔁 Fréquence de traitement

Le script vérifie les fichiers toutes les 
```
POLLING_INTERVAL secondes (défaut : 60 sec).
```
Peut être ajusté via les variables d’environnement dans docker-compose.yml :

environment:
  - POLLING_INTERVAL=30

📊 Intégration avec Metabase

Une base nommée metabase est créée pour accueillir une future visualisation avec Metabase.
Elle peut être connectée au même conteneur PostgreSQL.
🛠️ Débogage

    Voir les logs du service :

docker logs -f <nom_conteneur_etl>

    Forcer un retraitement :

        Modifier le fichier (touch clients.xlsx)

        Ou le renommer (clients_v2.xlsx)

