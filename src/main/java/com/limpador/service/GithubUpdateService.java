package com.limpador.service;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.limpador.model.UpdateInfo;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.io.InputStream;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.file.*;
import java.time.Duration;
import java.util.zip.ZipEntry;
import java.util.zip.ZipInputStream;

/**
 * Serviço de verificação e aplicação de atualizações diretas do repositório GitHub.
 * Utiliza o cliente HTTP assíncrono nativo do Java 11+ e deserialização robusta via Jackson.
 */
@Service
public class GithubUpdateService {

    private static final Logger log = LoggerFactory.getLogger(GithubUpdateService.class);
    private static final ObjectMapper OBJECT_MAPPER = new ObjectMapper();

    private String currentRepo = "CrystianSantos/Limpador-PC";
    private String currentCommit = "v1.0.0-java";

    public UpdateInfo checkForUpdates(String repoOverride) {
        String repo = (repoOverride != null && !repoOverride.isBlank()) ? repoOverride.trim() : currentRepo;
        if (repo.contains("github.com/")) {
            repo = repo.substring(repo.indexOf("github.com/") + 11).replace(".git", "");
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
        String repo = (repoOverride != null && !repoOverride.isBlank()) ? repoOverride.trim() : currentRepo;
        if (repo.contains("github.com/")) {
            repo = repo.substring(repo.indexOf("github.com/") + 11).replace(".git", "");
        }

        String zipUrl = "https://github.com/" + repo + "/archive/refs/heads/main.zip";

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

            if (response.statusCode() == 200) {
                Path destDir = Paths.get(".").toAbsolutePath().normalize();

                try (ZipInputStream zis = new ZipInputStream(response.body())) {
                    ZipEntry entry;
                    while ((entry = zis.getNextEntry()) != null) {
                        String name = entry.getName();
                        // Remove a pasta raiz do repositório gerada pelo GitHub (ex: Limpador-PC-main/)
                        int slashIndex = name.indexOf('/');
                        if (slashIndex != -1) {
                            name = name.substring(slashIndex + 1);
                        }
                        if (name.isBlank()) continue;

                        Path targetFile = destDir.resolve(name);
                        if (entry.isDirectory()) {
                            Files.createDirectories(targetFile);
                        } else {
                            if (targetFile.getParent() != null) {
                                Files.createDirectories(targetFile.getParent());
                            }
                            Files.copy(zis, targetFile, StandardCopyOption.REPLACE_EXISTING);
                        }
                        zis.closeEntry();
                    }
                }
                this.currentCommit = "main-latest";
                log.info("Atualização aplicada com sucesso a partir de {}", repo);
                return true;
            }
        } catch (Exception e) {
            log.error("Erro ao aplicar atualização: {}", e.getMessage(), e);
            return false;
        }

        return false;
    }

    public String getCurrentRepo() {
        return currentRepo;
    }

    public void setCurrentRepo(String currentRepo) {
        this.currentRepo = currentRepo;
    }
}
