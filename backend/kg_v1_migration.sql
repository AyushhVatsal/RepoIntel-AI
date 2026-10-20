BEGIN;

CREATE TABLE alembic_version (
    version_num VARCHAR(32) NOT NULL,
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);

-- Running upgrade  -> 31091724d4af

CREATE TABLE users (
    id SERIAL NOT NULL,
    username VARCHAR(100) NOT NULL,
    email VARCHAR(255) NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    is_active BOOLEAN NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    PRIMARY KEY (id)
);

CREATE UNIQUE INDEX ix_users_email ON users (email);

CREATE INDEX ix_users_id ON users (id);

CREATE TYPE repositorystatus AS ENUM ('PENDING', 'CLONING', 'SCANNING', 'PARSING', 'INDEXED', 'FAILED');

CREATE TABLE repositories (
    id SERIAL NOT NULL,
    owner_id INTEGER NOT NULL,
    name VARCHAR(255) NOT NULL,
    github_url VARCHAR(500) NOT NULL,
    description VARCHAR(1000),
    default_branch VARCHAR(100) NOT NULL,
    clone_path VARCHAR(500) NOT NULL,
    status repositorystatus NOT NULL,
    last_indexed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY(owner_id) REFERENCES users (id) ON DELETE CASCADE,
    CONSTRAINT uq_owner_repository UNIQUE (owner_id, github_url)
);

CREATE INDEX ix_repositories_id ON repositories (id);

CREATE INDEX ix_repositories_owner_id ON repositories (owner_id);

CREATE INDEX ix_repositories_status ON repositories (status);

CREATE TABLE conversations (
    id SERIAL NOT NULL,
    title VARCHAR(255) NOT NULL,
    user_id INTEGER NOT NULL,
    repository_id INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY(repository_id) REFERENCES repositories (id) ON DELETE CASCADE,
    FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE INDEX ix_conversations_id ON conversations (id);

CREATE INDEX ix_conversations_repository_id ON conversations (repository_id);

CREATE INDEX ix_conversations_user_id ON conversations (user_id);

CREATE TYPE messagerole AS ENUM ('USER', 'ASSISTANT', 'SYSTEM');

CREATE TABLE messages (
    id SERIAL NOT NULL,
    conversation_id INTEGER NOT NULL,
    role messagerole NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY(conversation_id) REFERENCES conversations (id) ON DELETE CASCADE
);

CREATE INDEX ix_messages_conversation_id ON messages (conversation_id);

CREATE INDEX ix_messages_id ON messages (id);

INSERT INTO alembic_version (version_num) VALUES ('31091724d4af') RETURNING alembic_version.version_num;

-- Running upgrade 31091724d4af -> 2b08890419d6

CREATE TYPE filecategory AS ENUM ('SOURCE', 'DOCUMENTATION', 'CONFIGURATION', 'BINARY', 'IGNORED');

CREATE TYPE languagesupporttier AS ENUM ('TIER_1', 'TIER_0', 'NONE');

CREATE TABLE repository_files (
    id SERIAL NOT NULL,
    repository_id INTEGER NOT NULL,
    path VARCHAR(1000) NOT NULL,
    relative_path VARCHAR(1000) NOT NULL,
    filename VARCHAR(255) NOT NULL,
    extension VARCHAR(20),
    language VARCHAR(50),
    category filecategory NOT NULL,
    support_tier languagesupporttier NOT NULL,
    size INTEGER NOT NULL,
    sha256_hash VARCHAR(64),
    is_binary BOOLEAN NOT NULL,
    last_modified TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY(repository_id) REFERENCES repositories (id) ON DELETE CASCADE
);

CREATE INDEX ix_repository_files_category ON repository_files (category);

CREATE INDEX ix_repository_files_language ON repository_files (language);

CREATE INDEX ix_repository_files_repository_id ON repository_files (repository_id);

CREATE UNIQUE INDEX ix_repository_files_repository_relative_path ON repository_files (repository_id, relative_path);

ALTER TABLE repositories ADD COLUMN primary_language VARCHAR(100);

ALTER TABLE repositories ADD COLUMN primary_framework VARCHAR(100);

ALTER TABLE repositories ADD COLUMN total_files INTEGER NOT NULL;

ALTER TABLE repositories ADD COLUMN supported_files INTEGER NOT NULL;

ALTER TABLE repositories ADD COLUMN skipped_files INTEGER NOT NULL;

ALTER TABLE repositories ADD COLUMN repository_size INTEGER NOT NULL;

ALTER TABLE repositories ALTER COLUMN github_url TYPE VARCHAR(1000);

ALTER TABLE repositories ALTER COLUMN clone_path TYPE VARCHAR(1000);

ALTER TABLE repositories ALTER COLUMN default_branch DROP NOT NULL;

ALTER TABLE repositories ADD UNIQUE (github_url);

ALTER TABLE repositories DROP COLUMN description;

ALTER TABLE repositories DROP COLUMN last_indexed_at;

UPDATE alembic_version SET version_num='2b08890419d6' WHERE alembic_version.version_num = '31091724d4af';

-- Running upgrade 2b08890419d6 -> 29e9809be8c8

CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE TABLE repository_symbols (
    id SERIAL NOT NULL,
    repository_id INTEGER NOT NULL,
    file_id INTEGER NOT NULL,
    symbol_type VARCHAR(50) NOT NULL,
    name VARCHAR(255) NOT NULL,
    qualified_name VARCHAR(1000) NOT NULL,
    location JSON NOT NULL,
    symbol_metadata JSON,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY(file_id) REFERENCES repository_files (id) ON DELETE CASCADE,
    FOREIGN KEY(repository_id) REFERENCES repositories (id) ON DELETE CASCADE,
    CONSTRAINT uq_file_symbol UNIQUE (file_id, symbol_type, qualified_name)
);

CREATE INDEX idx_symbols_repo_type ON repository_symbols (repository_id, symbol_type);

CREATE INDEX idx_symbols_file ON repository_symbols (file_id);

UPDATE alembic_version SET version_num='29e9809be8c8' WHERE alembic_version.version_num = '2b08890419d6';

-- Running upgrade 29e9809be8c8 -> 7c0d2f1a4b6e

ALTER TABLE repositories DROP CONSTRAINT repositories_github_url_key;

ALTER TABLE repositories ADD CONSTRAINT uq_owner_repository UNIQUE (owner_id, github_url);

UPDATE alembic_version SET version_num='7c0d2f1a4b6e' WHERE alembic_version.version_num = '29e9809be8c8';

-- Running upgrade 7c0d2f1a4b6e -> ee4657f8f0b4

CREATE TYPE chunktype AS ENUM ('MODULE', 'CLASS', 'FUNCTION', 'METHOD', 'IMPORT', 'VARIABLE', 'TEXT');

CREATE TABLE chunks (
    id SERIAL NOT NULL,
    repository_id INTEGER NOT NULL,
    file_id INTEGER NOT NULL,
    chunk_index INTEGER NOT NULL,
    chunk_type chunktype NOT NULL,
    content TEXT NOT NULL,
    start_line INTEGER NOT NULL,
    end_line INTEGER NOT NULL,
    token_count INTEGER NOT NULL,
    symbol_name VARCHAR(255),
    qualified_name VARCHAR(1000),
    parent_symbol VARCHAR(1000),
    metadata JSON NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY(file_id) REFERENCES repository_files (id) ON DELETE CASCADE,
    FOREIGN KEY(repository_id) REFERENCES repositories (id) ON DELETE CASCADE,
    CONSTRAINT uq_file_chunk_index UNIQUE (file_id, chunk_index)
);

CREATE INDEX ix_chunks_file_id ON chunks (file_id);

CREATE INDEX ix_chunks_repository_id ON chunks (repository_id);

UPDATE alembic_version SET version_num='ee4657f8f0b4' WHERE alembic_version.version_num = '7c0d2f1a4b6e';

-- Running upgrade ee4657f8f0b4 -> 7524bb189201

CREATE TABLE embeddings (
    id SERIAL NOT NULL,
    chunk_id INTEGER NOT NULL,
    model VARCHAR(255) NOT NULL,
    dimensions INTEGER NOT NULL,
    embedding VECTOR(384) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY(chunk_id) REFERENCES chunks (id) ON DELETE CASCADE,
    CONSTRAINT uq_embedding_chunk_model UNIQUE (chunk_id, model)
);

CREATE INDEX ix_embeddings_chunk_id ON embeddings (chunk_id);

UPDATE alembic_version SET version_num='7524bb189201' WHERE alembic_version.version_num = 'ee4657f8f0b4';

-- Running upgrade 7524bb189201 -> 59d528f0c29b

CREATE INDEX ix_embeddings_embedding_hnsw
        ON embeddings
        USING hnsw (embedding vector_cosine_ops);

UPDATE alembic_version SET version_num='59d528f0c29b' WHERE alembic_version.version_num = '7524bb189201';

-- Running upgrade 59d528f0c29b -> f197a73f5c78

CREATE TYPE filerole AS ENUM ('SOURCE', 'TEST', 'FIXTURE', 'CONFIG', 'DOCUMENTATION', 'UNKNOWN');

ALTER TABLE repository_files ADD COLUMN role filerole;

UPDATE repository_files SET role = 'UNKNOWN' WHERE role IS NULL;

ALTER TABLE repository_files ALTER COLUMN role SET NOT NULL;

UPDATE alembic_version SET version_num='f197a73f5c78' WHERE alembic_version.version_num = '59d528f0c29b';

-- Running upgrade f197a73f5c78 -> b7e4c9d2a610

ALTER TABLE repository_files ADD CONSTRAINT uq_repository_files_repository_id_id UNIQUE (repository_id, id);

ALTER TABLE repository_symbols ADD CONSTRAINT uq_repository_symbols_repository_file_id_id UNIQUE (repository_id, file_id, id);

ALTER TABLE chunks ADD CONSTRAINT uq_chunks_repository_file_id_id UNIQUE (repository_id, file_id, id);

CREATE TABLE graph_nodes (
    id SERIAL NOT NULL,
    repository_id INTEGER NOT NULL,
    node_type VARCHAR(30) NOT NULL,
    entity_key VARCHAR(1200) NOT NULL,
    name VARCHAR(255) NOT NULL,
    qualified_name VARCHAR(1200),
    file_id INTEGER,
    symbol_id INTEGER,
    chunk_id INTEGER,
    metadata JSON DEFAULT '{}'::json NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT fk_graph_nodes_repository_id_repositories FOREIGN KEY(repository_id) REFERENCES repositories (id) ON DELETE CASCADE,
    CONSTRAINT fk_graph_nodes_repository_file FOREIGN KEY(repository_id, file_id) REFERENCES repository_files (repository_id, id) ON DELETE CASCADE,
    CONSTRAINT fk_graph_nodes_repository_file_symbol FOREIGN KEY(repository_id, file_id, symbol_id) REFERENCES repository_symbols (repository_id, file_id, id) ON DELETE CASCADE,
    CONSTRAINT fk_graph_nodes_repository_file_chunk FOREIGN KEY(repository_id, file_id, chunk_id) REFERENCES chunks (repository_id, file_id, id) ON DELETE CASCADE,
    CONSTRAINT uq_graph_nodes_repository_id_id UNIQUE (repository_id, id),
    CONSTRAINT uq_graph_nodes_entity_identity UNIQUE (repository_id, node_type, entity_key),
    CONSTRAINT ck_graph_nodes_node_type CHECK (node_type IN ('REPOSITORY', 'FILE', 'SYMBOL', 'CHUNK')),
    CONSTRAINT ck_graph_nodes_entity_shape CHECK (
            (
                node_type = 'REPOSITORY'
                AND file_id IS NULL
                AND symbol_id IS NULL
                AND chunk_id IS NULL
            )
            OR
            (
                node_type = 'FILE'
                AND file_id IS NOT NULL
                AND symbol_id IS NULL
                AND chunk_id IS NULL
            )
            OR
            (
                node_type = 'SYMBOL'
                AND file_id IS NOT NULL
                AND symbol_id IS NOT NULL
                AND chunk_id IS NULL
            )
            OR
            (
                node_type = 'CHUNK'
                AND file_id IS NOT NULL
                AND symbol_id IS NULL
                AND chunk_id IS NOT NULL
            )
            )
);

CREATE UNIQUE INDEX uq_graph_nodes_repository_root ON graph_nodes (repository_id) WHERE node_type = 'REPOSITORY';

CREATE INDEX ix_graph_nodes_repository_type ON graph_nodes (repository_id, node_type);

CREATE TABLE graph_edges (
    id SERIAL NOT NULL,
    repository_id INTEGER NOT NULL,
    source_node_id INTEGER NOT NULL,
    target_node_id INTEGER NOT NULL,
    edge_type VARCHAR(50) NOT NULL,
    metadata JSON DEFAULT '{}'::json NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT fk_graph_edges_repository_id_repositories FOREIGN KEY(repository_id) REFERENCES repositories (id) ON DELETE CASCADE,
    CONSTRAINT fk_graph_edges_repository_source_node FOREIGN KEY(repository_id, source_node_id) REFERENCES graph_nodes (repository_id, id) ON DELETE CASCADE,
    CONSTRAINT fk_graph_edges_repository_target_node FOREIGN KEY(repository_id, target_node_id) REFERENCES graph_nodes (repository_id, id) ON DELETE CASCADE,
    CONSTRAINT uq_graph_edges_identity UNIQUE (repository_id, source_node_id, target_node_id, edge_type),
    CONSTRAINT ck_graph_edges_no_self_loop CHECK (source_node_id <> target_node_id),
    CONSTRAINT ck_graph_edges_edge_type CHECK (edge_type IN ('CONTAINS', 'DEFINES', 'IMPORTS', 'HAS_CHUNK'))
);

CREATE INDEX ix_graph_edges_repository_target ON graph_edges (repository_id, target_node_id);

UPDATE alembic_version SET version_num='b7e4c9d2a610' WHERE alembic_version.version_num = 'f197a73f5c78';

COMMIT;
