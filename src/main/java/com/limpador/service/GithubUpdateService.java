package com.limpador.service;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.limpador.model.UpdateInfo;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.file.*;
import java.security.MessageDigest;
import java.time.Duration;
import java.util.regex.Pattern;
import java.util.*;
import java.util.zip.ZipEntry;
import java.util.zip.ZipInputStream;

/**
 * Serviço de verificação e aplicação de atualizações diretas do repositório GitHub.
 * Implementa validação estrita de nomes de repositório, extração atômica em diretório
 * temporário com proteção contra vulnerabilidade Zip Slip (Path Traversal) e rollback.
 */
@Service
public class GithubUpdateService {

    private static final Logger log = LoggerFactory.getLogger(GithubUpdateService.class);
    private static final ObjectMapper OBJECT_MAPPER = new ObjectMapper();
    private static final Pattern REPO_PATTERN = Pattern.compile("^[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+$");
    private static final long MAX_ARCHIVE_BYTES = 100L * 1024 * 1024;
    private static final int MAX_ARCHIVE_ENTRIES = 20_000;
    private static final long MAX_EXPANDED_BYTES = 500L * 1024 * 1024;

    private volatile String currentRepo = "CrystianSantos/Limpador-PC";
    private String currentCommit = "v1.0.0-java";

    public UpdateInfo checkForUpdates(String repoOverride) {
        String repo = sanitizeRepo(repoOverride);
        if (repo == null) {
            repo = currentRepo;
        }

        UpdateInfo info = new UpdateInfo();
        info.setRepo(repo);
        info.setCurrentCommit(currentCommit);

        String apiUrl = "https://api.github.com/repos/" + repo + "/commits/main";

        try {
            HttpClient client = HttpClient.newBuilder()
                    .connectTimeout(Duration.ofSeconds(10))
                    .build();

            HttpRequest request = HttpRequest.newBuilder()
                    .uri(URI.create(apiUrl))
                    .header("User-Agent", "Limpador-PC-Java-Updater")
                    .header("Accept", "application/vnd.github.v3+json")
                    .timeout(Duration.ofSeconds(15))
                    .GET()
                    .build();

            HttpResponse<String> response = client.send(request, HttpResponse.BodyHandlers.ofString());

            if (response.statusCode() == 200) {
                JsonNode root = OBJECT_MAPPER.readTree(response.body());
                String sha = root.path("sha").asText(null);
                String shortSha = (sha != null && sha.length() >= 7) ? sha.substring(0, 7) : sha;

                String message = root.path("commit").path("message").asText("Sem mensagem");
                if (message.contains("\n")) {
                    message = message.substring(0, message.indexOf("\n"));
                }

                info.setSuccess(true);
                info.setLatestCommit(shortSha);
                info.setCommitMessage(message);
                info.setHasUpdate(!shortSha.equalsIgnoreCase(currentCommit));
            } else {
                info.setSuccess(false);
                info.setError("GitHub retornou código HTTP " + response.statusCode());
            }

        } catch (Exception e) {
            log.warn("Falha ao consultar atualizações no GitHub: {}", e.getMessage());
            info.setSuccess(false);
            info.setError("Não foi possível conectar ao GitHub: " + e.getMessage());
        }

        return info;
    }

    public boolean applyUpdate(String repoOverride) {
        String repo = sanitizeRepo(repoOverride);
        if (repo == null) {
            repo = currentRepo;
        }

        String zipUrl = "https://github.com/" + repo + "/archive/refs/heads/main.zip";
        Path tempDir = null;

        try {
            HttpClient client = HttpClient.newBuilder()
                    .connectTimeout(Duration.ofSeconds(15))
                    .build();

            HttpRequest request = HttpRequest.newBuilder()
                    .uri(URI.create(zipUrl))
                    .header("User-Agent", "Limpador-PC-Java-Updater")
                    .timeout(Duration.ofSeconds(30))
                    .GET()
                    .build();

            HttpResponse<InputStream> response = client.send(request, HttpResponse.BodyHandlers.ofInputStream());

            if (response.statusCode() != 200) {
                response.body().close();
                log.warn("Download do ZIP falhou com código HTTP: {}", response.statusCode());
                return false;
            }

            Path targetBase = Paths.get(".").toAbsolutePath().normalize();
            // Staging no mesmo volume da instalação permite substituições atômicas por arquivo.
            tempDir = Files.createTempDirectory(targetBase, ".limpador_update_");
            Path payload = Files.createDirectory(tempDir.resolve("payload"));
            Path backup = Files.createDirectory(tempDir.resolve("backup"));
            Path archive = tempDir.resolve("update.zip");
            try (InputStream in = response.body(); OutputStream out = Files.newOutputStream(archive)) {
                byte[] buffer = new byte[8192];
                long downloaded = 0;
                int read;
                while ((read = in.read(buffer)) != -1) {
                    downloaded += read;
                    if (downloaded > MAX_ARCHIVE_BYTES) throw new IOException("ZIP excede o limite de download permitido");
                    out.write(buffer, 0, read);
                }
            }
            String archiveRoot = null;
            int entryCount = 0;
            long expandedBytes = 0;

            try (ZipInputStream zis = new ZipInputStream(Files.newInputStream(archive))) {
                ZipEntry entry;
                while ((entry = zis.getNextEntry()) != null) {
                    if (++entryCount > MAX_ARCHIVE_ENTRIES) throw new IOException("ZIP excede o limite de entradas");
                    String rawName = entry.getName().replace('\\', '/');
                    if (rawName.startsWith("/") || rawName.matches("^[A-Za-z]:.*")) throw new SecurityException("Caminho absoluto no ZIP");
                    if (rawName.endsWith("/") && rawName.substring(0, rawName.length() - 1).indexOf('/') < 0) {
                        String rootEntry = rawName.substring(0, rawName.length() - 1);
                        if (rootEntry.isBlank() || rootEntry.equals(".") || rootEntry.equals("..")) throw new SecurityException("Raiz inválida no ZIP");
                        if (archiveRoot == null) archiveRoot = rootEntry;
                        if (!archiveRoot.equals(rootEntry)) throw new SecurityException("Raiz inesperada no ZIP");
                        zis.closeEntry();
                        continue;
                    }
                    String[] parts = rawName.split("/");
                    if (parts.length < 2 || Arrays.asList(parts).contains("..") || Arrays.asList(parts).contains(".")) throw new SecurityException("Caminho inválido no ZIP");
                    if (archiveRoot == null) archiveRoot = parts[0];
                    if (!archiveRoot.equals(parts[0])) throw new SecurityException("Raiz inesperada no ZIP");
                    String relativeName = String.join("/", Arrays.copyOfRange(parts, 1, parts.length));
                    if (relativeName.isBlank()) { zis.closeEntry(); continue; }
                    Path destPath = payload.resolve(relativeName).normalize();
                    if (!destPath.startsWith(payload)) throw new SecurityException("Escape de diretório detectado no ZIP");

                    if (entry.isDirectory()) {
                        Files.createDirectories(destPath);
                    } else {
                        if (destPath.getParent() != null) {
                            Files.createDirectories(destPath.getParent());
                        }
                        try (OutputStream out = Files.newOutputStream(destPath, StandardOpenOption.CREATE_NEW)) {
                            byte[] buffer = new byte[8192];
                            int read;
                            while ((read = zis.read(buffer)) != -1) {
                                expandedBytes += read;
                                if (expandedBytes > MAX_EXPANDED_BYTES) throw new IOException("ZIP descompactado excede o limite permitido");
                                out.write(buffer, 0, read);
                            }
                        }
                    }
                    zis.closeEntry();
                }
            }

            if (entryCount == 0 || archiveRoot == null) throw new IOException("ZIP vazio ou inválido");
            // Prepare replacements and backups before changing installed files.
            List<Path> installed = new ArrayList<>();
            try (var stream = Files.walk(payload)) {
                for (Path source : (Iterable<Path>) stream.filter(Files::isRegularFile)::iterator) {
                    Path relative = payload.relativize(source);
                    Path destination = targetBase.resolve(relative).normalize();
                    validateUpdateDestination(targetBase, destination);
                    Path staged = tempDir.resolve("new").resolve(relative);
                    Path saved = backup.resolve(relative);
                    Files.createDirectories(staged.getParent());
                    Files.copy(source, staged, StandardCopyOption.REPLACE_EXISTING);
                    if (Files.exists(destination, LinkOption.NOFOLLOW_LINKS)) {
                        if (!Files.isRegularFile(destination, LinkOption.NOFOLLOW_LINKS)) throw new IOException("Destino existente não é arquivo regular: " + relative);
                        Files.createDirectories(saved.getParent());
                        Files.copy(destination, saved, StandardCopyOption.REPLACE_EXISTING, StandardCopyOption.COPY_ATTRIBUTES);
                    }
                }
            }
            try (var stream = Files.walk(payload)) {
                for (Path source : (Iterable<Path>) stream.filter(Files::isRegularFile)::iterator) {
                    Path relative = payload.relativize(source);
                    Path destination = targetBase.resolve(relative).normalize();
                    validateUpdateDestination(targetBase, destination);
                    Files.createDirectories(destination.getParent());
                    Path staged = tempDir.resolve("new").resolve(relative);
                    try { Files.move(staged, destination, StandardCopyOption.ATOMIC_MOVE, StandardCopyOption.REPLACE_EXISTING); }
                    catch (AtomicMoveNotSupportedException e) { Files.move(staged, destination, StandardCopyOption.REPLACE_EXISTING); }
                    installed.add(relative);
                }
            } catch (Exception applyFailure) {
                Collections.reverse(installed);
                for (Path relative : installed) {
                    Path destination = targetBase.resolve(relative);
                    Path saved = backup.resolve(relative);
                    if (Files.exists(saved)) Files.copy(saved, destination, StandardCopyOption.REPLACE_EXISTING, StandardCopyOption.COPY_ATTRIBUTES);
                    else Files.deleteIfExists(destination);
                }
                throw applyFailure;
            }

            this.currentCommit = "main-latest";
            log.info("Atualização verificada e aplicada com sucesso a partir de {}", repo);
            return true;

        } catch (Exception e) {
            log.error("Erro seguro durante processo de atualização: {}", e.getMessage(), e);
            return false;
        } finally {
            if (tempDir != null) {
                deleteDirectoryQuietly(tempDir);
            }
        }
    }

    private String sanitizeRepo(String raw) {
        if (raw == null || raw.isBlank()) {
            return null;
        }
        String cleaned = raw.trim();
        if (cleaned.startsWith("https://github.com/")) {
            cleaned = cleaned.substring("https://github.com/".length());
        } else if (cleaned.contains("://") || cleaned.startsWith("//")) {
            return null;
        }
        if (cleaned.endsWith(".git")) {
            cleaned = cleaned.substring(0, cleaned.length() - 4);
        }
        if (REPO_PATTERN.matcher(cleaned).matches()) {
            return cleaned;
        }
        log.warn("Nome de repositório rejeitado por conter caracteres inválidos: {}", raw);
        return null;
    }

    private void validateUpdateDestination(Path targetBase, Path destination) throws IOException {
        if (!destination.startsWith(targetBase) || destination.equals(targetBase)) {
            throw new SecurityException("Destino de atualização fora da instalação");
        }
        Path relative = targetBase.relativize(destination);
        if (relative.getNameCount() > 0 && relative.getName(0).toString().equalsIgnoreCase(".git")) {
            throw new SecurityException("Atualização não pode alterar os metadados do Git");
        }
        Path cursor = targetBase;
        for (int i = 0; i < relative.getNameCount(); i++) {
            cursor = cursor.resolve(relative.getName(i));
            if (Files.isSymbolicLink(cursor)) throw new SecurityException("Destino de atualização contém link simbólico");
        }
    }

    private void deleteDirectoryQuietly(Path dir) {
        try {
            if (!Files.exists(dir)) return;
            try (var stream = Files.walk(dir)) {
                List<Path> paths = new java.util.ArrayList<>();
                for (Path p : (Iterable<Path>) stream::iterator) {
                    paths.add(p);
                }
                paths.sort(java.util.Comparator.reverseOrder());
                for (Path p : paths) {
                    Files.deleteIfExists(p);
                }
            }
        } catch (Exception ignored) {
        }
    }

    public String getCurrentRepo() {
        return currentRepo;
    }

    public boolean setCurrentRepo(String newRepo) {
        String sanitized = sanitizeRepo(newRepo);
        if (sanitized != null) {
            this.currentRepo = sanitized;
            return true;
        }
        return false;
    }
}
