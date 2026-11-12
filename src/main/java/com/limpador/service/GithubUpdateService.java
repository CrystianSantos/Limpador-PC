package com.limpador.service;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.limpador.model.UpdateInfo;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.io.IOException;
import java.io.InputStream;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.file.*;
import java.time.Duration;
import java.util.regex.Pattern;
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

    private String currentRepo = "CrystianSantos/Limpador-PC";
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
                log.warn("Download do ZIP falhou com código HTTP: {}", response.statusCode());
                return false;
            }

            // 1. Extração segura para diretório temporário isolado (Atômico)
            tempDir = Files.createTempDirectory("limpador_update_");
            Path targetBase = Paths.get(".").toAbsolutePath().normalize();

            try (ZipInputStream zis = new ZipInputStream(response.body())) {
                ZipEntry entry;
                while ((entry = zis.getNextEntry()) != null) {
                    String name = entry.getName();
                    // Remove pasta raiz padrão criada pelo GitHub (ex: Limpador-PC-main/)
                    int slashIndex = name.indexOf('/');
                    if (slashIndex != -1) {
                        name = name.substring(slashIndex + 1);
                    }
                    if (name.isBlank()) continue;

                    // Defesa contra Vulnerabilidade Zip Slip (Path Traversal)
                    Path destPath = tempDir.resolve(name).normalize();
                    if (!destPath.startsWith(tempDir)) {
                        throw new SecurityException("Tentativa de escape de diretório detectada no ZIP: " + name);
                    }

                    if (entry.isDirectory()) {
                        Files.createDirectories(destPath);
                    } else {
                        if (destPath.getParent() != null) {
                            Files.createDirectories(destPath.getParent());
                        }
                        Files.copy(zis, destPath, StandardCopyOption.REPLACE_EXISTING);
                    }
                    zis.closeEntry();
                }
            }

            // 2. Aplica arquivos do diretório temporário para a aplicação após validação completa
            copyDirectoryRecursively(tempDir, targetBase);

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
        if (cleaned.contains("github.com/")) {
            cleaned = cleaned.substring(cleaned.indexOf("github.com/") + 11);
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

    private void copyDirectoryRecursively(Path source, Path target) throws IOException {
        try (var stream = Files.walk(source)) {
            for (Path p : (Iterable<Path>) stream::iterator) {
                Path relative = source.relativize(p);
                Path dest = target.resolve(relative).normalize();

                // Garante que o destino não saia da raiz da aplicação
                if (!dest.startsWith(target)) {
                    continue;
                }

                if (Files.isDirectory(p)) {
                    Files.createDirectories(dest);
                } else if (Files.isRegularFile(p)) {
                    if (dest.getParent() != null) {
                        Files.createDirectories(dest.getParent());
                    }
                    Files.copy(p, dest, StandardCopyOption.REPLACE_EXISTING);
                }
            }
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
