CREATE TABLE IF NOT EXISTS customers (
  id VARCHAR(36) PRIMARY KEY,
  email VARCHAR(255) NOT NULL UNIQUE,
  full_name VARCHAR(255) NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS customer_tokens (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  customer_id VARCHAR(36) NOT NULL,
  token VARCHAR(64) NOT NULL UNIQUE,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (customer_id) REFERENCES customers(id)
);

INSERT INTO customers (id,email, full_name, password_hash)
VALUES ('US_001','demo.customer@example.com', 'Demo Customer', 'pbkdf2_sha256$1200000$XxplXlRR2nAgO0WDNxJX2T$0iMVzlaeo8OBNFfDa0824puPexP0xJOBouo7dfCxJwI=')
ON DUPLICATE KEY UPDATE email=email;
