package com.limpador.model;

import com.limpador.util.FormatUtils;
import java.util.ArrayList;
import java.util.List;

public class DuplicateGroup {
    private String hash;
    private long fileSize;
    private String fileSizeFormatted;
    private FileItem original;
    private List<FileItem> copies = new ArrayList<>();
    private long wastedBytes;
    private String wastedFormatted;

    public DuplicateGroup() {
    }

    public DuplicateGroup(String hash, long fileSize, FileItem original, List<FileItem> copies) {
        this.hash = hash;
        this.fileSize = fileSize;
        this.fileSizeFormatted = FormatUtils.formatSize(fileSize);
        this.original = original;
        this.copies = copies;
        this.wastedBytes = fileSize * copies.size();
        this.wastedFormatted = FormatUtils.formatSize(this.wastedBytes);
    }

    public String getHash() {
        return hash;
    }

    public void setHash(String hash) {
        this.hash = hash;
    }

    public long getFileSize() {
        return fileSize;
    }

    public void setFileSize(long fileSize) {
        this.fileSize = fileSize;
        this.fileSizeFormatted = FormatUtils.formatSize(fileSize);
        recalcWasted();
    }

    public String getFileSizeFormatted() {
        return fileSizeFormatted;
    }

    public FileItem getOriginal() {
        return original;
    }

    public void setOriginal(FileItem original) {
        this.original = original;
    }

    public List<FileItem> getCopies() {
        return copies;
    }

    public void setCopies(List<FileItem> copies) {
        this.copies = copies;
        recalcWasted();
    }

    public long getWastedBytes() {
        return wastedBytes;
    }

    public String getWastedFormatted() {
        return wastedFormatted;
    }

    private void recalcWasted() {
        this.wastedBytes = this.fileSize * (copies != null ? copies.size() : 0);
        this.wastedFormatted = FormatUtils.formatSize(this.wastedBytes);
    }
}
