package com.limpador.service;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.limpador.model.UpdateInfo;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/** Checks published releases for the trusted Limpador-PC repository. */
@Service
public class GithubUpdateService {
    private static final Logger log = LoggerFactory.getLogger(GithubUpdateService.class);
    private static final ObjectMapper OBJECT_MAPPER = new ObjectMapper();
    private static final String REPOSITORY = "CrystianSantos/Limpador-PC";
    private static final URI LATEST_RELEASE_API = URI.create("https://api.github.com/repos/" + REPOSITORY + "/releases/latest");
    private static final String RELEASES_URL = "https://github.com/" + REPOSITORY + "/releases/latest";
    private static final Pattern VERSION_PATTERN = Pattern.compile("^[vV]?(\\d+)\\.(\\d+)\\.(\\d+)(?:-([0-9A-Za-z.-]+))?(?:\\+[0-9A-Za-z.-]+)?$");
    private static final String CURRENT_VERSION = currentPackageVersion();

    public UpdateInfo checkForUpdates() {
        UpdateInfo info = new UpdateInfo();
        info.setRepository(REPOSITORY);
        info.setCurrentVersion(CURRENT_VERSION);
        info.setReleaseUrl(RELEASES_URL);

        try {
            HttpClient client = HttpClient.newBuilder()
                    .connectTimeout(Duration.ofSeconds(10))
                    .followRedirects(HttpClient.Redirect.NEVER)
                    .build();
            HttpRequest request = HttpRequest.newBuilder()
                    .uri(LATEST_RELEASE_API)
                    .header("User-Agent", "Limpador-PC-Java")
                    .header("Accept", "application/vnd.github+json")
                    .timeout(Duration.ofSeconds(15))
                    .GET()
                    .build();

            HttpResponse<String> response = client.send(request, HttpResponse.BodyHandlers.ofString());
            if (response.statusCode() != 200) {
                info.setSuccess(false);
                info.setError(response.statusCode() == 404
                        ? "Ainda não há uma Release publicada no GitHub."
                        : "GitHub retornou código HTTP " + response.statusCode());
                return info;
            }

            JsonNode release = OBJECT_MAPPER.readTree(response.body());
            String latestVersion = release.path("tag_name").asText("").trim();
            if (latestVersion.isBlank()) {
                info.setSuccess(false);
                info.setError("A Release do GitHub não contém uma versão válida.");
                return info;
            }

            info.setSuccess(true);
            info.setLatestVersion(latestVersion);
            info.setReleaseName(release.path("name").asText(latestVersion));
            info.setHasUpdate(isNewerVersion(latestVersion, CURRENT_VERSION));
            return info;
        } catch (Exception e) {
            log.warn("Falha ao consultar Releases do GitHub: {}", e.getMessage());
            info.setSuccess(false);
            info.setError("Não foi possível consultar as Releases do GitHub.");
            return info;
        }
    }

    static String currentPackageVersion() {
        String implementationVersion = GithubUpdateService.class.getPackage().getImplementationVersion();
        return implementationVersion == null || implementationVersion.isBlank() ? "1.0.0" : implementationVersion;
    }

    public String getCurrentVersion() {
        return CURRENT_VERSION;
    }

    public static boolean isNewerVersion(String candidate, String current) {
        Matcher candidateMatcher = VERSION_PATTERN.matcher(candidate == null ? "" : candidate.trim());
        Matcher currentMatcher = VERSION_PATTERN.matcher(current == null ? "" : current.trim());
        if (!candidateMatcher.matches() || !currentMatcher.matches()) return false;

        for (int group = 1; group <= 3; group++) {
            int comparison = Integer.compare(
                    Integer.parseInt(candidateMatcher.group(group)),
                    Integer.parseInt(currentMatcher.group(group))
            );
            if (comparison != 0) return comparison > 0;
        }

        String candidatePreRelease = candidateMatcher.group(4);
        String currentPreRelease = currentMatcher.group(4);
        if (candidatePreRelease == null || currentPreRelease == null) {
            return currentPreRelease != null && candidatePreRelease == null;
        }
        return comparePreRelease(candidatePreRelease, currentPreRelease) > 0;
    }

    private static int comparePreRelease(String candidate, String current) {
        String[] candidateParts = candidate.split("\\.");
        String[] currentParts = current.split("\\.");
        int commonLength = Math.min(candidateParts.length, currentParts.length);
        for (int i = 0; i < commonLength; i++) {
            boolean candidateNumeric = candidateParts[i].matches("\\d+");
            boolean currentNumeric = currentParts[i].matches("\\d+");
            int comparison;
            if (candidateNumeric && currentNumeric) {
                comparison = new java.math.BigInteger(candidateParts[i]).compareTo(new java.math.BigInteger(currentParts[i]));
            } else if (candidateNumeric != currentNumeric) {
                comparison = candidateNumeric ? -1 : 1;
            } else {
                comparison = candidateParts[i].compareTo(currentParts[i]);
            }
            if (comparison != 0) return comparison;
        }
        return Integer.compare(candidateParts.length, currentParts.length);
    }
}
