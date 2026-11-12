package com.limpador.model;

import com.limpador.util.FormatUtils;

public class FileItem {
    private String path;
    private String filename;
    private String category;
    private long size;
    private String sizeFormatted;
    private String mtime;
    private boolean isDir;
    private boolean safeToDelete;

    public FileItem() {
    }

    public FileItem(String path, String filename, String category, long size, String mtime, boolean isDir, boolean safeToDelete) {
        this.path = path;
        this.filename = filename;
        this.category = category;
        this.size = size;
        this.sizeFormatted = FormatUtils.formatSize(size);
        this.mtime = mtime;
        this.isDir = isDir;
        this.safeToDelete = safeToDelete;
    }

    public String getPath() {
        return path;
    }

    public void setPath(String path) {
        this.path = path;
    }

    public String getFilename() {
        return filename;
    }

    public void setFilename(String filename) {
        this.filename = filename;
    }

    public String getCategory() {
        return category;
    }

    public void setCategory(String category) {
        this.category = category;
    }

    public long getSize() {
        return size;
    }

    public void setSize(long size) {
        this.size = size;
        this.sizeFormatted = FormatUtils.formatSize(size);
    }

    public String getSizeFormatted() {
        return sizeFormatted;
    }

    public void setSizeFormatted(String sizeFormatted) {
        this.sizeFormatted = sizeFormatted;
    }

    public String getMtime() {
        return mtime;
    }

    public void setMtime(String mtime) {
        this.mtime = mtime;
    }

    public boolean isDir() {
        return isDir;
    }

    public void setDir(boolean dir) {
        isDir = dir;
    }

    public boolean isSafeToDelete() {
        return safeToDelete;
    }

    public void setSafeToDelete(boolean safeToDelete) {
        this.safeToDelete = safeToDelete;
    }
}
