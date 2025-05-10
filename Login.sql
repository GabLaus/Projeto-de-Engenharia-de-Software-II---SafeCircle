CREATE DATABASE SafeCircle
USE SafeCircle

CREATE TABLE Usuario (
	id_user INT PRIMARY KEY IDENTITY,
	nome VARCHAR(50) NOT NULL
	email VARCHAR(50) NOT NULL,
	senha VARCHAR(50) NOT NULL,
	dat_nac DATE NOT NULL,
	telefone INT UNIQUE NOT NULL,
	cpf VARCHAR(11) UNIQUE NOT NULL,
	rg VARCHAR(9) UNIQUE NOT NULL,
	ind_front VARBINARY(MAX), -- foto da indentidade 
	ind_back VARBINARY(MAX)  -- foto do outro lado da indentidade
);
