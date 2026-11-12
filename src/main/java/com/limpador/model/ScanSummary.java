package com.limpador.model;

import com.limpador.util.FormatUtils;
import java.util.ArrayList;
import java.util.List;

public class ScanSummary {
    private String title;
    private int totalFiles;
    private long totalSize;
    private String totalSizeFormatted;
    private String explanation;
    private boolean safeToDelete;
    private List<FileItem> items = new ArrayList<>();

    public ScanSummary() {
    }

    public ScanSummary(String title, int totalFiles, long totalSize, String explanation, boolean safeToDelete, List<FileItem> items) {
        this.title = title;
        this.totalFiles = totalFiles;
        this.totalSize = totalSize;
        this.totalSizeFormatted = FormatUtils.formatSize(totalSize);
        this.explanation = explanation;
        this.safeToDelete = safeToDelete;
        this.items = items;
    }

    public String getTitle() {
        return title;
    }

    public void setTitle(String title) {
        this.title = title;
    }

    public int getTotalFiles() {
        return totalFiles;
    }

    public void setTotalFiles(int totalFiles) {
        this.totalFiles = totalFiles;
    }

    public long getTotalSize() {
        return totalSize;
    }

    public void setTotalSize(long totalSize) {
        this.totalSize = totalSize;
        this.totalSizeFormatted = FormatUtils.formatSize(totalSize);
    }

    public String getTotalSizeFormatted() {
        return totalSizeFormatted;
    }

    public String getExplanation() {
        return explanation;
    }

    public void setExplanation(String explanation) {
        this.explanation = explanation;
    }

    public boolean isSafeToDelete() {
        return safeToDelete;
    }

    public void setSafeToDelete(boolean safeToDelete) {
        this.safeToDelete = safeToDelete;
    }

    public List<FileItem> getItems() {
        return items;
    }

    public void setItems(List<FileItem> items) {
        this.items = items;
    }
}
