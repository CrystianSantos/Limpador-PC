package com.limpador.model;

public class UpdateInfo {
    private boolean success;
    private boolean hasUpdate;
    private String repository;
    private String currentVersion;
    private String latestVersion;
    private String releaseName;
    private String releaseUrl;
    private String error;

    public boolean isSuccess() { return success; }
    public void setSuccess(boolean success) { this.success = success; }
    public boolean isHasUpdate() { return hasUpdate; }
    public void setHasUpdate(boolean hasUpdate) { this.hasUpdate = hasUpdate; }
    public String getRepository() { return repository; }
    public void setRepository(String repository) { this.repository = repository; }
    public String getCurrentVersion() { return currentVersion; }
    public void setCurrentVersion(String currentVersion) { this.currentVersion = currentVersion; }
    public String getLatestVersion() { return latestVersion; }
    public void setLatestVersion(String latestVersion) { this.latestVersion = latestVersion; }
    public String getReleaseName() { return releaseName; }
    public void setReleaseName(String releaseName) { this.releaseName = releaseName; }
    public String getReleaseUrl() { return releaseUrl; }
    public void setReleaseUrl(String releaseUrl) { this.releaseUrl = releaseUrl; }
    public String getError() { return error; }
    public void setError(String error) { this.error = error; }
}
