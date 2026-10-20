import gzip
import os
import subprocess
from pathlib import Path

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from django.test import SimpleTestCase

WURZEL = Path(__file__).resolve().parents[2]


def openssl_aes_encrypt(plaintext: bytes, passphrase: str) -> bytes:
    """Implementiert OpenSSLs 'enc -aes-256-cbc -pbkdf2 -iter 100000 -salt' in Python."""
    salt = os.urandom(8)
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=48,  # 32 Bytes Key + 16 Bytes IV
        salt=salt,
        iterations=100000,
    )
    derived = kdf.derive(passphrase.encode("utf-8"))
    key = derived[:32]
    iv = derived[32:48]

    # PKCS7 Padding
    pad_len = 16 - (len(plaintext) % 16)
    padded = plaintext + bytes([pad_len] * pad_len)

    cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
    encryptor = cipher.encryptor()
    ciphertext = encryptor.update(padded) + encryptor.finalize()

    return b"Salted__" + salt + ciphertext


def openssl_aes_decrypt(encrypted_data: bytes, passphrase: str) -> bytes:
    """Entschlüsselt OpenSSL 'enc -aes-256-cbc -pbkdf2 -iter 100000 -salt'."""
    if len(encrypted_data) < 16 or not encrypted_data.startswith(b"Salted__"):
        raise ValueError("Ungültiges OpenSSL-Header-Format.")

    salt = encrypted_data[8:16]
    ciphertext = encrypted_data[16:]

    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=48,
        salt=salt,
        iterations=100000,
    )
    derived = kdf.derive(passphrase.encode("utf-8"))
    key = derived[:32]
    iv = derived[32:48]

    cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
    decryptor = cipher.decryptor()
    padded = decryptor.update(ciphertext) + decryptor.finalize()

    pad_len = padded[-1]
    if pad_len < 1 or pad_len > 16 or padded[-pad_len:] != bytes([pad_len] * pad_len):
        raise ValueError("Padding-Fehler: Ungültiger Schlüssel.")

    return padded[:-pad_len]


class DeploymentConfigurationTests(SimpleTestCase):
    def test_prod_compose_services_and_volumes(self):
        """docker-compose.prod.yml enthält db, app, caddy und backup sowie alle nötigen Volumes."""
        compose_text = (WURZEL / "docker-compose.prod.yml").read_text(encoding="utf-8")

        # Services
        self.assertIn("db:", compose_text)
        self.assertIn("app:", compose_text)
        self.assertIn("caddy:", compose_text)
        self.assertIn("backup:", compose_text)
        self.assertIn("uptime-kuma:", compose_text)

        # Caddy TLS & Ports
        self.assertIn('"80:80"', compose_text)
        self.assertIn('"443:443"', compose_text)
        self.assertIn("caddy:2-alpine", compose_text)

        # Uptime Kuma Port & Image (PRD N2.8: von aussen nicht ohne Weiteres erreichbar)
        self.assertIn('"127.0.0.1:3001:3001"', compose_text)
        self.assertNotIn('"3001:3001"', compose_text)
        self.assertNotIn('"0.0.0.0:3001"', compose_text)
        self.assertIn("louislam/uptime-kuma", compose_text)

        # Volumes
        self.assertIn("caddy_data:", compose_text)
        self.assertIn("caddy_config:", compose_text)
        self.assertIn("static_files:", compose_text)
        self.assertIn("db_data:", compose_text)
        self.assertIn("kuma_data:", compose_text)

        # Backup Skriptbindung & Monitoring
        self.assertIn("/tools/backup.sh", compose_text)
        self.assertIn("KUMA_PUSH_URL", compose_text)

        # SEC-01: SSL Redirect und HSTS dürfen nicht hart auf 0 stehen
        self.assertIn('SECURE_SSL_REDIRECT: "${SECURE_SSL_REDIRECT:-1}"', compose_text)
        self.assertIn('SECURE_HSTS_SECONDS: "${SECURE_HSTS_SECONDS:-31536000}"', compose_text)

    def test_caddyfile_configuration(self):
        """Caddyfile leitet auf app:8000 weiter, liefert statische Dateien aus und setzt Security-Header."""
        caddyfile = (WURZEL / "Caddyfile").read_text(encoding="utf-8")

        self.assertIn("reverse_proxy app:8000", caddyfile)
        self.assertIn("/app/staticfiles", caddyfile)
        self.assertIn("Strict-Transport-Security", caddyfile)
        self.assertIn("X-Content-Type-Options", caddyfile)
        self.assertIn("X-Frame-Options", caddyfile)
        self.assertIn("encode zstd gzip", caddyfile)
        # Keine externen Hosts im Caddyfile
        self.assertNotIn("http://", caddyfile)
        self.assertNotIn("https://", caddyfile)

    def test_env_prod_example_contains_all_keys(self):
        """Die Vorlage .env.prod.example enthält alle verpflichtenden Schlüssel."""
        env_example = (WURZEL / ".env.prod.example").read_text(encoding="utf-8")

        self.assertIn("DJANGO_SECRET_KEY=", env_example)
        self.assertIn("IBAN_FERNET_KEY=", env_example)
        self.assertIn("BACKUP_ENCRYPTION_KEY=", env_example)
        self.assertIn("POSTGRES_DB=", env_example)
        self.assertIn("POSTGRES_USER=", env_example)
        self.assertIn("POSTGRES_PASSWORD=", env_example)
        self.assertIn("EMAIL_BACKEND=", env_example)
        self.assertIn("KUMA_PUSH_URL=", env_example)

    def test_deployment_doc_requirements(self):
        """docs/deployment.md nennt EU/DE Hoststandort, Caddy, Restore-Protokoll, Updatepfad und Uptime Kuma Monitoring."""
        doc = (WURZEL / "docs/deployment.md").read_text(encoding="utf-8")

        self.assertIn("DE/EU", doc)
        self.assertIn("Hetzner", doc)
        self.assertIn("Caddy", doc)
        self.assertIn("tools/backup.sh", doc)
        self.assertIn("tools/restore.sh", doc)
        self.assertIn("Restore-Test-Protokoll", doc)
        self.assertIn("schachverein_2026-10-01", doc)
        self.assertIn("git pull", doc)
        self.assertIn("Uptime Kuma", doc)
        self.assertIn("Push-Monitor", doc)
        self.assertIn("KUMA_PUSH_URL", doc)
        self.assertIn("127.0.0.1:3001", doc)

    def test_backup_script_contains_push_monitor_logic(self):
        """tools/backup.sh enthält die Push-Ping-Logik für Uptime Kuma (PRD N2.8 / T24b)."""
        backup_sh = (WURZEL / "tools/backup.sh").read_text(encoding="utf-8")
        self.assertIn("KUMA_PUSH_URL", backup_sh)
        self.assertIn("Melde erfolgreiches Backup an Uptime Kuma", backup_sh)
        # Negativfall: Fehler beim Ping darf Backup nicht abbrechen
        self.assertIn("|| echo", backup_sh)


class EncryptedBackupRestoreTests(SimpleTestCase):
    """Prüft die Verschlüsselungs- und Wiederherstellungslogik für Backups (PRD N2.1 / ADR-009)."""

    def setUp(self):
        self.test_sql = (
            b"-- Test-SQL-Dump fuer Schachverein\n"
            b"CREATE TABLE members_member (id serial PRIMARY KEY, vorname varchar(100), nachname varchar(100));\n"
            b"INSERT INTO members_member (id, vorname, nachname) VALUES (1, 'Max', 'Mustermann');\n"
            b"INSERT INTO members_member (id, vorname, nachname) VALUES (2, 'Erika', 'Musterfrau');\n"
        )
        self.key = "ein-sehr-sicherer-geheimer-schluessel-12345"

    def test_backup_creates_encrypted_archive(self):
        """Ein Backup wird komprimiert und verschlüsselt; der Chiffretext enthält kein Plaintext-SQL."""
        compressed = gzip.compress(self.test_sql)
        encrypted = openssl_aes_encrypt(compressed, self.key)

        # Chiffretext muss mit Salted__ beginnen
        self.assertTrue(encrypted.startswith(b"Salted__"))
        # Keine SQL-Fragmente oder Klartextdaten im verschlüsselten Zustand auffindbar
        self.assertNotIn(b"CREATE TABLE", encrypted)
        self.assertNotIn(b"Mustermann", encrypted)
        self.assertNotIn(b"Musterfrau", encrypted)

    def test_restore_with_correct_key_succeeds(self):
        """Mit dem richtigen Schlüssel wird der ursprüngliche SQL-Dump bitgenau wiederhergestellt."""
        compressed = gzip.compress(self.test_sql)
        encrypted = openssl_aes_encrypt(compressed, self.key)

        decrypted_compressed = openssl_aes_decrypt(encrypted, self.key)
        recovered_sql = gzip.decompress(decrypted_compressed)

        self.assertEqual(recovered_sql, self.test_sql)

    def test_restore_with_wrong_key_fails(self):
        """Negativtest: Ein falscher Schlüssel bricht die Entschlüsselung mit einem Fehler ab."""
        compressed = gzip.compress(self.test_sql)
        encrypted = openssl_aes_encrypt(compressed, self.key)

        wrong_key = "falscher-schluessel-98765"
        with self.assertRaises((ValueError, gzip.BadGzipFile, Exception)):
            decrypted = openssl_aes_decrypt(encrypted, wrong_key)
            gzip.decompress(decrypted)

    def test_restore_with_corrupt_data_fails(self):
        """Negativtest: Beschädigte oder manipulierte Backup-Dateien werden abgewiesen."""
        compressed = gzip.compress(self.test_sql)
        encrypted = openssl_aes_encrypt(compressed, self.key)

        # Byte im Chiffretext manipulieren
        corrupt_encrypted = encrypted[:20] + bytes([encrypted[20] ^ 0xFF]) + encrypted[21:]

        with self.assertRaises((ValueError, gzip.BadGzipFile, Exception)):
            decrypted = openssl_aes_decrypt(corrupt_encrypted, self.key)
            gzip.decompress(decrypted)


    def test_restore_with_truncated_data_fails(self):
        """Negativtest: Unvollständige/abgebrochene Backup-Dateien werden abgewiesen."""
        compressed = gzip.compress(self.test_sql)
        encrypted = openssl_aes_encrypt(compressed, self.key)

        # Datei nach 15 Bytes abgeschnitten (zu kurz für OpenSSL-Header)
        truncated = encrypted[:15]

        with self.assertRaises(ValueError):
            openssl_aes_decrypt(truncated, self.key)

    def test_backup_scripts_syntax(self):
        """Die Shellskripte tools/backup.sh und tools/restore.sh existieren und enthalten die Sicherheitsprüfungen."""
        backup_sh = (WURZEL / "tools/backup.sh").read_text(encoding="utf-8")
        restore_sh = (WURZEL / "tools/restore.sh").read_text(encoding="utf-8")

        self.assertIn("BACKUP_ENCRYPTION_KEY", backup_sh)
        self.assertIn("openssl enc -aes-256-cbc", backup_sh)
        self.assertIn("BACKUP_ENCRYPTION_KEY", restore_sh)
        self.assertIn("openssl enc -d -aes-256-cbc", restore_sh)
        self.assertIn("--check-only", restore_sh)

    def test_restore_script_check_only_workflow(self):
        """tools/restore.sh mit --check-only prüft Integrität und Schlüssel erfolgreich per Shell."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            compressed = gzip.compress(self.test_sql)
            encrypted = openssl_aes_encrypt(compressed, self.key)
            backup_file = tmp_path / "schachverein_test.sql.gz.enc"
            backup_file.write_bytes(encrypted)

            # Test mit korrektem Schlüssel
            env = {**os.environ, "BACKUP_ENCRYPTION_KEY": self.key}
            proc = subprocess.run(
                ["/bin/sh", str(WURZEL / "tools/restore.sh"), str(backup_file), "--check-only"],
                env=env,
                capture_output=True,
                text=True,
            )
            self.assertEqual(proc.returncode, 0)
            self.assertIn("Integritätsprüfung erfolgreich", proc.stdout)

            # Negativtest: Falscher Schlüssel bricht mit Exit-Code 2 ab
            env_wrong = {**os.environ, "BACKUP_ENCRYPTION_KEY": "falscher-schluessel"}
            proc_wrong = subprocess.run(
                ["/bin/sh", str(WURZEL / "tools/restore.sh"), str(backup_file), "--check-only"],
                env=env_wrong,
                capture_output=True,
                text=True,
            )
            self.assertEqual(proc_wrong.returncode, 2)
            self.assertIn("Entschlüsselung oder Integritätsprüfung fehlgeschlagen", proc_wrong.stderr)

            # Negativtest: Fehlender Schlüssel bricht mit Exit-Code 1 ab
            env_empty = {k: v for k, v in os.environ.items() if k != "BACKUP_ENCRYPTION_KEY"}
            proc_empty = subprocess.run(
                ["/bin/sh", str(WURZEL / "tools/restore.sh"), str(backup_file), "--check-only"],
                env=env_empty,
                capture_output=True,
                text=True,
            )
            self.assertEqual(proc_empty.returncode, 1)
            self.assertIn("BACKUP_ENCRYPTION_KEY ist nicht gesetzt", proc_empty.stderr)

