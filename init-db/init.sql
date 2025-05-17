-- Création d'une base spécifique pour Metabase
CREATE DATABASE metabase;

-- Connexion à la base de données de l'entrepôt
\c entrepot;

-- Création d'un schéma pour notre entrepôt
CREATE SCHEMA IF NOT EXISTS warehouse;

-- Table pour stocker les métadonnées des fichiers
CREATE TABLE IF NOT EXISTS warehouse.file_metadata (
    id SERIAL PRIMARY KEY,
    filename VARCHAR(255) NOT NULL,
    last_modified TIMESTAMP NOT NULL,
    last_processed TIMESTAMP NOT NULL,
    status VARCHAR(50) NOT NULL
);

-- Tables pour stocker les données des fichiers Excel
-- Supposons que le fichier1.xlsx contient des données clients
CREATE TABLE IF NOT EXISTS warehouse.clients (
    id SERIAL PRIMARY KEY,
    client_id VARCHAR(50) UNIQUE NOT NULL,
    nom VARCHAR(100) NOT NULL,
    prenom VARCHAR(100) NOT NULL,
    email VARCHAR(255),
    telephone VARCHAR(20),
    adresse TEXT,
    date_creation TIMESTAMP DEFAULT NOW(),
    source_file VARCHAR(255) NOT NULL,
    imported_at TIMESTAMP DEFAULT NOW()
);

-- Supposons que le fichier2.xlsx contient des données produits
CREATE TABLE IF NOT EXISTS warehouse.produits (
    id SERIAL PRIMARY KEY,
    produit_id VARCHAR(50) UNIQUE NOT NULL,
    nom VARCHAR(255) NOT NULL,
    categorie VARCHAR(100),
    prix_unitaire DECIMAL(10, 2) NOT NULL,
    stock_disponible INTEGER NOT NULL,
    description TEXT,
    source_file VARCHAR(255) NOT NULL,
    imported_at TIMESTAMP DEFAULT NOW()
);

-- Supposons que le fichier3.xlsx contient des données ventes
CREATE TABLE IF NOT EXISTS warehouse.ventes (
    id SERIAL PRIMARY KEY,
    vente_id VARCHAR(50) UNIQUE NOT NULL,
    client_id VARCHAR(50) NOT NULL,
    produit_id VARCHAR(50) NOT NULL,
    quantite INTEGER NOT NULL,
    prix_total DECIMAL(10, 2) NOT NULL,
    date_vente TIMESTAMP NOT NULL,
    source_file VARCHAR(255) NOT NULL,
    imported_at TIMESTAMP DEFAULT NOW(),
    FOREIGN KEY (client_id) REFERENCES warehouse.clients(client_id),
    FOREIGN KEY (produit_id) REFERENCES warehouse.produits(produit_id)
);

-- Index pour améliorer les performances
CREATE INDEX idx_clients_client_id ON warehouse.clients(client_id);
CREATE INDEX idx_produits_produit_id ON warehouse.produits(produit_id);
CREATE INDEX idx_ventes_client_id ON warehouse.ventes(client_id);
CREATE INDEX idx_ventes_produit_id ON warehouse.ventes(produit_id);
CREATE INDEX idx_ventes_date ON warehouse.ventes(date_vente);